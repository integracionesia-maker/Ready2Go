"""Diagnostico de notificaciones.

**Advertencia de contrato:** el contrato v1 **no define ningun endpoint de
notificaciones**, y `permisos_catalogo.json` (congelado) no tiene un modulo para
ellas. Estas rutas existen porque `docs/ASIGNACION_EQUIPOS.md` las pide de forma
explicita en la tarea S6, y la asignacion manda sobre el plan. Son de solo
diagnostico: no cambian ningun payload existente y ningun cliente construido
contra el contrato las llama.

Se protegen con `usuarios:gestionar` — el unico par del catalogo que encaja, y
que hoy solo tiene el `superadmin`. Cuando el contrato v2 defina su propio modulo
de notificaciones, esto se cambia por el par correcto.

`GET /config` **jamas** devuelve `SMTP_PASSWORD`. Solo si esta configurada.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import mailer, models, notificaciones, tz
from ..database import get_db
from ..errores import NoEncontrado
from ..models_equipos import NotificationLog
from ..rbac import require_perm

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificacionResponse(BaseModel):
    id: int
    loan_id: Optional[int] = None
    canal: str
    destinatario: str
    asunto: Optional[str] = None
    tipo: str
    estado: str
    intentos: int
    error: Optional[str] = None
    created_at: Optional[str] = None
    sent_at: Optional[str] = None


class NotificacionesListResponse(BaseModel):
    items: List[NotificacionResponse]
    total: int


class ConfigResponse(BaseModel):
    notif_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_starttls: bool
    smtp_from: str
    app_public_url: str
    # Booleano, no el valor: una contraseña no se expone ni al superadmin.
    smtp_user_configurado: bool
    smtp_password_configurada: bool
    aprobadores_resueltos: int


def _a_response(fila: NotificationLog) -> NotificacionResponse:
    return NotificacionResponse(
        id=fila.id,
        loan_id=fila.loan_id,
        canal=fila.canal,
        destinatario=fila.destinatario,
        asunto=fila.asunto,
        tipo=fila.tipo,
        estado=fila.estado,
        intentos=fila.intentos,
        error=fila.error,
        created_at=tz.iso_cdmx(fila.created_at),
        sent_at=tz.iso_cdmx(fila.sent_at),
    )


@router.get("/", response_model=NotificacionesListResponse)
def listar_notificaciones(
    loan_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    consulta = db.query(NotificationLog)
    if loan_id is not None:
        consulta = consulta.filter(NotificationLog.loan_id == loan_id)
    if tipo:
        consulta = consulta.filter(NotificationLog.tipo.like(f"{tipo}%"))
    if estado:
        consulta = consulta.filter(NotificationLog.estado == estado)

    total = consulta.count()
    filas = consulta.order_by(NotificationLog.id.desc()).offset(offset).limit(limit).all()
    return NotificacionesListResponse(items=[_a_response(f) for f in filas], total=total)


@router.get("/config", response_model=ConfigResponse)
def configuracion(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    """Para responder "por que no llegan los correos" sin entrar al servidor.

    `aprobadores_resueltos` es el dato que mas cuesta descubrir: si sale 0, los
    avisos de autorizacion no se mandan a nadie y no hay error en ningun lado
    (pasa con `RBAC_MODO=legacy`, que apaga los paquetes aditivos).
    """
    cfg = mailer.config()
    return ConfigResponse(
        notif_enabled=cfg.habilitado,
        smtp_host=cfg.host,
        smtp_port=cfg.port,
        smtp_starttls=cfg.starttls,
        smtp_from=cfg.remitente,
        app_public_url=cfg.url_publica,
        smtp_user_configurado=bool(cfg.user),
        smtp_password_configurada=bool(cfg.password),
        aprobadores_resueltos=len(notificaciones.aprobadores(db)),
    )


@router.post("/{notification_id:int}/reintentar", response_model=NotificacionResponse)
def reintentar(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    """Reintenta un envio **reusando la misma fila**.

    Crear una fila nueva perderia la cuenta de intentos y haria imposible saber
    cuantas veces se intento — que es justo lo que el registro existe para
    contestar.
    """
    fila = db.get(NotificationLog, notification_id)
    if fila is None:
        raise NoEncontrado("Notificacion no encontrada.")

    from ..models_equipos import Loan
    from .. import plantillas_correo as pl

    prestamo = db.get(Loan, fila.loan_id) if fila.loan_id else None
    if prestamo is None:
        raise NoEncontrado("El prestamo de esa notificacion ya no existe.")

    _, cuerpo = pl.construir(fila.tipo, notificaciones.datos_de_prestamo(db, prestamo))
    adjuntos = (
        notificaciones._adjunto_responsiva(db, prestamo)
        if fila.tipo in (pl.TIPO_CONFIRMADO_APROBADOR, pl.TIPO_CONFIRMADO_RESPONSABLE)
        else []
    )
    notificaciones.procesar_pendiente(fila.id, cuerpo, adjuntos)

    db.refresh(fila)
    return _a_response(fila)
