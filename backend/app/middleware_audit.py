"""Middleware de auditoria automatica: registra cada request de MUTACION
(autenticada o no) en `audit_log`, a nivel HTTP generico (metodo, ruta,
status, duracion). Los GET (dashboard, listados, polling) no se auditan aqui
-- son la mayoria del trafico y no cambian nada; auditarlos solo suma
volumen de escritura de fondo sin aportar rastro util.

Convive a proposito con las ~35 llamadas manuales a `crud.log_audit(...)` que
ya existen en los routers (login, altas/bajas de usuario, concesion de
roles, aprobaciones de prestamo, etc.): esas siguen escribiendo sus propias
filas con `action`/`target_type` curados a mano. Este middleware NO las
reemplaza ni las deduplica -- cubre el resto de la superficie (la mayoria de
los endpoints de Presupuestos/Equipos hoy no llaman a log_audit en absoluto)
con un rastro generico de "quien pidio que ruta y que le respondio el
servidor", que antes no existia para nada fuera de esos ~35 puntos.

Nunca debe tumbar una request real: todo el cuerpo corre en try/except y el
fallo se imprime a consola, no se propaga.
"""

from __future__ import annotations

import time

from starlette.background import BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from . import security
from .database import SessionLocal

RUTAS_EXCLUIDAS = ("/api/audit-logs", "/api/health")
# No se captura el cuerpo de login: contendria la contraseña en texto plano.
RUTAS_SIN_CUERPO = ("/api/auth/login",)
MAX_RESUMEN_BODY = 500


def _actor_id_desde_cookie(request: Request) -> int | None:
    token = request.cookies.get(security.ACCESS_COOKIE_NAME)
    if not token:
        return None
    payload = security.decode_access_token(token)
    if not payload:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None


async def _resumen_body(request: Request) -> str | None:
    """Solo para JSON: leer un body multipart/form (tickets, gastos generales,
    fotos de equipos) es mas riesgoso de interferir con el parseo real del
    endpoint, y aporta poco (son archivos, no texto). Se deja fuera a
    proposito -- no es una omision accidental."""
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None
    try:
        crudo = await request.body()
    except Exception:
        return None
    if not crudo:
        return None
    texto = crudo.decode("utf-8", errors="replace")
    if len(texto) > MAX_RESUMEN_BODY:
        texto = texto[:MAX_RESUMEN_BODY] + "…"
    return texto


def _escribir_auditoria(**kwargs) -> None:
    """Corre en el threadpool de Starlette (via BackgroundTasks), nunca en el
    event loop: es I/O de DB sincrono y bajo trafico concurrente bloquearlo
    en el loop congela la app entera para todos, no solo para este request."""
    try:
        db = SessionLocal()
        try:
            from . import crud

            crud.log_audit(db, **kwargs)
        finally:
            db.close()
    except Exception as exc:  # nunca debe tumbar la request real
        print(f"[middleware_audit] fallo al registrar auditoria: {exc}")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(RUTAS_EXCLUIDAS) or request.method == "GET":
            return await call_next(request)

        inicio = time.monotonic()
        actor_user_id = _actor_id_desde_cookie(request)
        body_resumen = None if path in RUTAS_SIN_CUERPO else await _resumen_body(request)

        response = await call_next(request)

        try:
            duracion_ms = int((time.monotonic() - inicio) * 1000)
            kwargs = dict(
                action=f"{request.method} {path}",
                actor_user_id=actor_user_id,
                http_method=request.method,
                endpoint_path=path,
                request_params=str(request.query_params) or None,
                request_body_summary=body_resumen,
                response_status=response.status_code,
                user_agent=request.headers.get("user-agent"),
                duration_ms=duracion_ms,
                ip_address=request.client.host if request.client else None,
            )

            # El endpoint puede ya traer sus propias BackgroundTasks (ej. envio
            # de correo en loans/approvals) -- se encadena, nunca se pisa.
            if not isinstance(response.background, BackgroundTasks):
                tareas = BackgroundTasks()
                if response.background is not None:
                    tareas.add_task(response.background)
                response.background = tareas
            response.background.add_task(_escribir_auditoria, **kwargs)
        except Exception as exc:  # nunca debe tumbar la request real
            print(f"[middleware_audit] fallo al registrar auditoria: {exc}")

        return response
