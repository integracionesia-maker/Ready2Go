"""Middleware de auditoria automatica: registra cada request a /api/* en
`audit_log` via cola en memoria (nunca directo a la DB desde el event loop).

La escritura real la hace una unica tarea de fondo (`audit_queue._consumidor`)
que junta eventos en lotes y los flushea por threadpool — un solo escritor a
la vez, sin competir por el pool de conexiones ni por el lock de SQLite.

Convive a proposito con las ~35 llamadas manuales a `crud.log_audit(...)` que
ya existen en los routers (login, altas/bajas de usuario, concesion de
roles, aprobaciones de prestamo, etc.): esas siguen escribiendo sus propias
filas con `action`/`target_type` curados a mano. Este middleware NO las
reemplaza ni las deduplica -- cubre el resto de la superficie con un rastro
generico de "quien pidio que ruta y que le respondio el servidor".

Nunca debe tumbar una request real: todo el cuerpo corre en try/except y el
fallo se imprime a consola, no se propaga.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from . import security
from . import audit_queue

RUTAS_EXCLUIDAS = ("/api/audit-logs", "/api/health")
# No se captura el cuerpo de estas rutas: contienen credenciales en texto plano.
# La redacción por campo (_redactar_campos) es la segunda línea de defensa para
# cualquier otra ruta que algún día reciba un campo sensible.
RUTAS_SIN_CUERPO = (
    "/api/auth/login",
    "/api/auth/change-password",
    "/api/auth/refresh",
)
MAX_RESUMEN_BODY = 500

# Campos sensibles redactados del resumen JSON ANTES de persistir: sin esto, un
# cambio de contraseña o un alta de usuario dejaría la credencial en claro en
# audit_log para siempre (hallazgo de la auditoría de seguridad 2026-08-18).
_CAMPOS_SENSIBLES = (
    "password",
    "current_password",
    "new_password",
    "confirm_password",
    "refresh_token",
    "token",
    "secret",
    "authorization",
    "api_key",
)
_PATRON_SENSIBLE = re.compile(
    r'("(?:' + "|".join(_CAMPOS_SENSIBLES) + r')"\s*:\s*")[^"]*(")',
    re.IGNORECASE,
)


def _redactar_campos(texto: str) -> str:
    """Sustituye el valor de cualquier campo sensible por `***`."""
    return _PATRON_SENSIBLE.sub(r"\1***\2", texto)


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
    return _redactar_campos(texto)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allowlist positivo: solo se auditan requests a /api/*.
        # Esto excluye automaticamente assets estaticos (/assets/*) y el
        # catch-all del SPA que sirve index.html para cualquier otra ruta.
        if not path.startswith("/api/") or path.startswith(RUTAS_EXCLUIDAS):
            return await call_next(request)

        inicio = time.monotonic()
        actor_user_id = _actor_id_desde_cookie(request)
        # Comparar sin trailing slash: un POST a /api/auth/login/ (con barra
        # final) no matchea la ruta exacta y Starlette lo redirige 307, pero el
        # body con la contraseña ya habría sido capturado y persistido.
        path_normalizado = path.rstrip("/") if path != "/" else path
        body_resumen = None if path_normalizado in RUTAS_SIN_CUERPO else await _resumen_body(request)

        response = await call_next(request)

        try:
            duracion_ms = int((time.monotonic() - inicio) * 1000)
            # El instante del evento se captura AQUI (momento del enqueue),
            # no en el flush — si se usara el momento del flush, todas las
            # filas de un mismo lote tendrian timestamps casi identicos.
            evento = dict(
                ocurrido_en=datetime.now(timezone.utc),
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
            audit_queue.enqueue(evento)
        except Exception as exc:  # nunca debe tumbar la request real
            print(f"[middleware_audit] fallo al encolar auditoria: {exc}")

        return response
