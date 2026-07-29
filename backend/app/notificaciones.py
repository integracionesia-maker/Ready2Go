"""Orquestacion de avisos por correo: a quien, con que, y sin duplicar.

Tres reglas que vienen de §7 del plan y de §10.15/§10.16/§10.20:

1. **Los destinatarios se resuelven por rol desde la base**, nunca de una
   constante. La maqueta tenia `melisa.avendano@grupo-ortiz.com` escrito en el
   JavaScript; si Melisa cambia de puesto, aqui se revoca el aditivo y ya.
2. **`UNIQUE(loan_id, tipo, destinatario)` es la idempotencia.** Reintentar no
   duplica el aviso. La fila se crea antes de intentar el envio: si el proceso
   muere a medias, queda registro de que se intento.
3. **Un SMTP caido no tumba el registro del prestamo.** El envio va en
   `BackgroundTasks`, con su propia sesion, y `mailer.enviar` nunca levanta.

El recordatorio de vencimiento merece parrafo aparte: el plan lo quiere
**diario**, pero con un `tipo` constante el UNIQUE lo mandaria **una sola vez en
la vida del prestamo** y todos los dias siguientes chocarian en silencio,
interpretados como idempotencia correcta. Por eso el tipo lleva sufijo de dia
civil de CDMX (`vencimiento:2026-07-30`): el UNIQUE pasa a significar "un aviso
por prestamo, por destinatario, por dia", que es exactamente lo que pide §7, y
sigue bloqueando la doble corrida del mismo dia.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import crud_rbac, mailer, plantillas_correo as pl, tz
from .database import SessionLocal
from .models import User
from .models_equipos import (
    DecisionDevolucion,
    EstadoNotificacion,
    Equipment,
    Loan,
    LoanItem,
    NotificationLog,
    ResponsivaDoc,
)

log = logging.getLogger("ready2go.notificaciones")

__all__ = [
    "MAX_INTENTOS",
    "tipo_vencimiento",
    "aprobadores",
    "datos_de_prestamo",
    "encolar",
    "procesar_pendiente",
    "reintentar_fallidos",
]

MAX_INTENTOS = 3


def tipo_vencimiento(fecha=None) -> str:
    """`vencimiento:YYYY-MM-DD` con el dia civil de CDMX.

    El dia sale de `tz.hoy()`, jamas de UTC: despues de las 18:00 CDMX el UTC ya
    es el dia siguiente y produciria dos filas y dos correos para el mismo dia.
    """
    return f"{pl.TIPO_VENCIMIENTO}:{(fecha or tz.hoy()).isoformat()}"


# ── Destinatarios ───────────────────────────────────────────────────────────


def aprobadores(db: Session) -> list[User]:
    """Quien puede autorizar entregas, resuelto desde la base.

    `incluir_superadmin=False`: el superadmin tiene todos los permisos por
    bypass, pero mandarle cada aviso de prestamo lo convierte en ruido.

    Una lista vacia es ruidosa a proposito. En `RBAC_MODO=legacy` los paquetes
    aditivos no aplican y `equipos_aprobacion` solo lo concede
    `APROBADOR_EQUIPO`: la lista queda vacia y **ningun aviso sale**, sin error y
    sin que nadie lo note. Escribir un correo de respaldo en el codigo seria
    volver al hardcode que §10.20 prohibe; lo unico correcto es que se vea.
    """
    from . import rbac

    encontrados = crud_rbac.usuarios_con_permiso(
        db, "equipos_aprobacion", "autorizar_entrega", incluir_superadmin=False
    )
    if not encontrados:
        log.warning(
            "0 usuarios con equipos_aprobacion:autorizar_entrega (RBAC_MODO=%s). "
            "Ningun aviso de autorizacion va a salir.",
            rbac.modo_rbac(),
        )
    return encontrados


# ── Datos para las plantillas ───────────────────────────────────────────────


def datos_de_prestamo(db: Session, prestamo: Loan) -> dict:
    equipos = [
        nombre
        for (nombre,) in db.query(Equipment.nombre)
        .join(LoanItem, LoanItem.equipment_id == Equipment.id)
        .filter(LoanItem.loan_id == prestamo.id)
        .order_by(LoanItem.id)
        .all()
    ]
    incidencias = [
        f"{item.equipo.nombre if item.equipo else item.equipment_id}: "
        f"{item.decision} — {item.nota_decision or 'sin nota'}"
        for item in prestamo.items
        if item.decision and item.decision != DecisionDevolucion.OK.value
    ]
    dias = 0
    if prestamo.fecha_regreso_esperada:
        dias = tz.dias_de_atraso(prestamo.fecha_regreso_esperada)

    return {
        "folio": prestamo.folio or f"(borrador {prestamo.id})",
        "responsable": prestamo.responsable_nombre,
        "area": prestamo.area,
        "empresa": prestamo.empresa,
        "motivo": prestamo.motivo,
        "fecha_entrega": tz.iso_fecha(prestamo.fecha_entrega),
        "fecha_regreso_esperada": tz.iso_fecha(prestamo.fecha_regreso_esperada),
        "fecha_regreso_real": tz.iso_fecha(prestamo.fecha_regreso_real),
        "equipos": equipos,
        "incidencias": incidencias,
        "dias_atraso": dias,
        "url_publica": mailer.config().url_publica,
    }


def _adjunto_responsiva(db: Session, prestamo: Loan) -> list[tuple[str, bytes, str]]:
    """La ultima version de la carta, si existe en disco.

    Que falte el archivo no cancela el correo: el aviso sigue siendo util y el
    PDF se puede descargar desde la aplicacion.
    """
    documento = (
        db.query(ResponsivaDoc)
        .filter(ResponsivaDoc.loan_id == prestamo.id)
        .order_by(ResponsivaDoc.version.desc())
        .first()
    )
    if documento is None:
        return []
    ruta = Path(documento.file_path)
    if not ruta.exists():
        log.warning("Responsiva %s sin archivo en disco: %s", prestamo.folio, ruta)
        return []
    return [(f"{prestamo.folio}_v{documento.version}.pdf", ruta.read_bytes(), "application/pdf")]


# ── Encolado ────────────────────────────────────────────────────────────────


def _fila(db: Session, prestamo: Loan, tipo: str, destinatario: str, asunto: str) -> NotificationLog | None:
    """Crea la fila del registro, o devuelve la que ya existe.

    Se apoya en el UNIQUE, no en un SELECT previo: entre consultar e insertar
    cabe otra corrida del mismo aviso.
    """
    punto = db.begin_nested()
    try:
        registro = NotificationLog(
            loan_id=prestamo.id,
            canal="email",
            destinatario=destinatario,
            asunto=asunto[:255],
            tipo=tipo,
            estado=EstadoNotificacion.PENDIENTE.value,
            intentos=0,
            created_at=tz.ahora_utc_naive(),
        )
        db.add(registro)
        db.flush()
        punto.commit()
        return registro
    except IntegrityError:
        punto.rollback()

    existente = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.loan_id == prestamo.id,
            NotificationLog.tipo == tipo,
            NotificationLog.destinatario == destinatario,
        )
        .first()
    )
    if existente is None:
        return None
    if existente.estado == EstadoNotificacion.ENVIADO.value:
        # Ya salio. Reintentar no duplica el aviso a la aprobadora.
        return None
    return existente


def encolar(
    db: Session,
    tipo: str,
    prestamo: Loan,
    background_tasks=None,
    *,
    destinatarios: list[str] | None = None,
    con_responsiva: bool = False,
) -> list[NotificationLog]:
    """Registra los avisos y programa su envio.

    Devuelve las filas creadas o reutilizadas. Las que ya estaban enviadas no
    aparecen: no hay nada que hacer con ellas.

    Sin `background_tasks` no se envia nada, solo se registra — asi lo usa el
    script de recordatorios, que procesa en su propio proceso.
    """
    datos = datos_de_prestamo(db, prestamo)
    asunto, cuerpo = pl.construir(tipo, datos)

    if destinatarios is None:
        destinatarios = [u.email for u in aprobadores(db) if u.email]

    adjuntos = _adjunto_responsiva(db, prestamo) if con_responsiva else []

    filas: list[NotificationLog] = []
    for destinatario in dict.fromkeys(d for d in destinatarios if d):
        fila = _fila(db, prestamo, tipo, destinatario, asunto)
        if fila is None:
            continue
        filas.append(fila)

    db.commit()

    if background_tasks is not None:
        for fila in filas:
            # Se pasa el id, no el objeto: la sesion del request estara cerrada
            # cuando la tarea corra.
            background_tasks.add_task(procesar_pendiente, fila.id, cuerpo, adjuntos)

    return filas


# ── Envio ───────────────────────────────────────────────────────────────────


def procesar_pendiente(
    notification_id: int, cuerpo: str, adjuntos: list[tuple[str, bytes, str]] | None = None
) -> bool:
    """Intenta el envio de una fila. Abre su propia sesion.

    Corre despues de la respuesta HTTP, cuando la sesion del request ya se cerro.
    No levanta nunca: un fallo aqui deja la fila en `fallido` con su motivo, y el
    prestamo sigue registrado.
    """
    db = SessionLocal()
    try:
        fila = db.get(NotificationLog, notification_id)
        if fila is None or fila.estado == EstadoNotificacion.ENVIADO.value:
            return False

        resultado = mailer.enviar(fila.destinatario, fila.asunto or "", cuerpo, adjuntos)

        if resultado.omitido:
            # Apagado o sin configurar: no cuenta como intento fallido. La fila
            # queda pendiente para cuando haya cuenta SMTP.
            fila.error = resultado.motivo
            db.commit()
            return False

        fila.intentos = (fila.intentos or 0) + 1
        if resultado.enviado:
            fila.estado = EstadoNotificacion.ENVIADO.value
            fila.sent_at = tz.ahora_utc_naive()
            fila.error = None
        else:
            fila.estado = EstadoNotificacion.FALLIDO.value
            fila.error = (resultado.motivo or "")[:1000]
            log.warning(
                "Correo fallido a %s (tipo %s, intento %s): %s",
                fila.destinatario,
                fila.tipo,
                fila.intentos,
                fila.error,
            )
        db.commit()
        return resultado.enviado
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("Error procesando la notificacion %s", notification_id)
        return False
    finally:
        db.close()


def reintentar_fallidos(db: Session, limite: int = 50) -> int:
    """Reintenta lo que quedo pendiente o fallido sin agotar sus intentos.

    Reusa **la misma fila**: crear una nueva perderia la cuenta de intentos y
    haria imposible saber cuantas veces se intento.
    """
    filas = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.estado.in_(
                [EstadoNotificacion.PENDIENTE.value, EstadoNotificacion.FALLIDO.value]
            )
        )
        .filter(NotificationLog.intentos < MAX_INTENTOS)
        .order_by(NotificationLog.id)
        .limit(limite)
        .all()
    )

    enviados = 0
    for fila in filas:
        prestamo = db.get(Loan, fila.loan_id) if fila.loan_id else None
        if prestamo is None:
            continue
        _, cuerpo = pl.construir(fila.tipo, datos_de_prestamo(db, prestamo))
        adjuntos = (
            _adjunto_responsiva(db, prestamo)
            if fila.tipo
            in (pl.TIPO_CONFIRMADO_APROBADOR, pl.TIPO_CONFIRMADO_RESPONSABLE)
            else []
        )
        if procesar_pendiente(fila.id, cuerpo, adjuntos):
            enviados += 1
    return enviados
