"""Las cinco plantillas de correo de §7 del plan.

Texto plano, en español, tono sobrio, **cero emojis**. Funciones puras: reciben
un diccionario y devuelven `(asunto, cuerpo)`. No tocan la base ni el mailer, asi
que se prueban sin sesion y sin servidor de correo.

Los textos son propuesta del servidor: el plan define disparador, destinatarios y
que datos lleva cada correo, no la redaccion. Son mensajes de cara a personas de
Grupo Ortiz, asi que conviene que marketing los apruebe antes del piloto.
"""

from __future__ import annotations

__all__ = [
    "TIPO_CONFIRMADO_APROBADOR",
    "TIPO_CONFIRMADO_RESPONSABLE",
    "TIPO_DEVOLUCION_APROBADOR",
    "TIPO_DEVOLUCION_CONFIRMADA",
    "TIPO_VENCIMIENTO",
    "TIPO_FIRMA_COMPLETADA",
    "PIE",
    "RUTA_APROBACIONES",
    "RUTA_PRESTAMO",
    "construir",
    "PLANTILLAS",
]

# Valores de `notification_log.tipo`. Forman parte de la clave de idempotencia
# UNIQUE(loan_id, tipo, destinatario): cambiarlos reenvia todo.
TIPO_CONFIRMADO_APROBADOR = "confirmado_aprobador"
TIPO_CONFIRMADO_RESPONSABLE = "confirmado_responsable"
TIPO_DEVOLUCION_APROBADOR = "devolucion_aprobador"
TIPO_DEVOLUCION_CONFIRMADA = "devolucion_confirmada"
# El de vencimiento lleva sufijo de dia (`vencimiento:2026-07-30`) porque el
# recordatorio es DIARIO y el UNIQUE lo bloquearia para siempre despues del
# primer envio. Ver `notificaciones.tipo_vencimiento()`.
TIPO_VENCIMIENTO = "vencimiento"
# Se dispara cuando se sube la firma que faltaba al confirmar (prestamo ya en
# `prestado`, ver `crud_loans.completar_firma_faltante`). Sin sufijo de dia:
# pasa una sola vez en la vida del prestamo, exactamente como confirmado_*.
TIPO_FIRMA_COMPLETADA = "firma_completada"

PIE = (
    "\n\n--\n"
    "Mensaje automatico de GOCreate — Control de Equipos.\n"
    "No respondas a esta dirección."
)

# Rutas de la interfaz. El contrato solo define rutas de /api/*, asi que estas
# son propuesta y hay que confirmarlas con quien construye el frontend: si no
# coinciden, los correos apuntan a paginas que dan 404.
RUTA_APROBACIONES = "/equipos/aprobaciones"
RUTA_PRESTAMO = "/equipos/prestamo/{folio}"


def _lista(equipos: list[str]) -> str:
    return "\n".join(f"  - {nombre}" for nombre in equipos) if equipos else "  (sin equipos)"


def _enlace(base: str, ruta: str) -> str:
    return f"{base.rstrip('/')}{ruta}"


def _aviso_firma_pendiente(d: dict) -> str:
    """Parrafo extra si falta alguna firma (ver §1b de `loan_state.py`) —
    `confirmar` nunca pide ninguna, asi que al confirmarse lo normal es que
    falten las dos. Vacio si ya estan completas."""
    quien = d.get("firma_pendiente")
    if not quien:
        return ""
    return (
        f"\nOJO: firma(s) pendiente(s) — {quien}. La carta responsiva adjunta "
        f"lo muestra en blanco; se actualiza sola en cuanto se complete.\n"
    )


def confirmado_aprobador(d: dict) -> tuple[str, str]:
    asunto = f"[GOCreate] Prestamo {d['folio']} listo para autorizar"
    cuerpo = (
        f"Se registro un prestamo de equipo que necesita tu autorizacion.\n\n"
        f"Folio: {d['folio']}\n"
        f"Responsable: {d['responsable']}\n"
        f"Area: {d.get('area') or '—'}\n"
        f"Empresa: {d.get('empresa') or '—'}\n"
        f"Motivo: {d.get('motivo') or '—'}\n"
        f"Fecha de entrega: {d.get('fecha_entrega') or '—'}\n"
        f"Fecha de regreso esperada: {d.get('fecha_regreso_esperada') or '—'}\n\n"
        f"Equipos:\n{_lista(d.get('equipos') or [])}\n\n"
        f"La carta responsiva va adjunta.\n"
        f"{_aviso_firma_pendiente(d)}"
        f"Para autorizar la entrega: {_enlace(d['url_publica'], RUTA_APROBACIONES)}"
        f"{PIE}"
    )
    return asunto, cuerpo


def confirmado_responsable(d: dict) -> tuple[str, str]:
    asunto = f"[GOCreate] Tu carta responsiva {d['folio']}"
    cuerpo = (
        f"Hola {d['responsable']}:\n\n"
        f"Adjuntamos tu copia de la carta responsiva del equipo que recibiste.\n\n"
        f"Folio: {d['folio']}\n"
        f"Fecha de entrega: {d.get('fecha_entrega') or '—'}\n"
        f"Fecha de regreso esperada: {d.get('fecha_regreso_esperada') or '—'}\n\n"
        f"Equipos a tu resguardo:\n{_lista(d.get('equipos') or [])}\n"
        f"{_aviso_firma_pendiente(d)}\n"
        f"Consulta el prestamo en: "
        f"{_enlace(d['url_publica'], RUTA_PRESTAMO.format(folio=d['folio']))}"
        f"{PIE}"
    )
    return asunto, cuerpo


def firma_completada(d: dict) -> tuple[str, str]:
    asunto = f"[GOCreate] Firma completada — carta responsiva {d['folio']} actualizada"
    cuerpo = (
        f"Se completo la firma que faltaba en el prestamo {d['folio']}.\n\n"
        f"Responsable: {d['responsable']}\n"
        f"Equipos:\n{_lista(d.get('equipos') or [])}\n\n"
        f"La carta responsiva actualizada, ya con las dos firmas, va adjunta.\n"
        f"Consulta el prestamo en: "
        f"{_enlace(d['url_publica'], RUTA_PRESTAMO.format(folio=d['folio']))}"
        f"{PIE}"
    )
    return asunto, cuerpo


def devolucion_aprobador(d: dict) -> tuple[str, str]:
    asunto = f"[GOCreate] Devolucion registrada del prestamo {d['folio']}"
    cuerpo = (
        f"Se registro la devolucion de un prestamo y falta confirmarla.\n\n"
        f"Folio: {d['folio']}\n"
        f"Responsable: {d['responsable']}\n"
        f"Fecha de regreso: {d.get('fecha_regreso_real') or '—'}\n\n"
        f"Equipos devueltos:\n{_lista(d.get('equipos') or [])}\n\n"
        f"Revisa las fotos de devolucion y confirma el estado en: "
        f"{_enlace(d['url_publica'], RUTA_APROBACIONES)}"
        f"{PIE}"
    )
    return asunto, cuerpo


def devolucion_confirmada(d: dict) -> tuple[str, str]:
    hay_incidencias = bool(d.get("incidencias"))
    estado = "con incidencias" if hay_incidencias else "en buen estado"
    asunto = f"[GOCreate] Devolucion confirmada — {d['folio']} ({estado})"

    detalle = ""
    if hay_incidencias:
        detalle = "\nIncidencias reportadas:\n" + "\n".join(
            f"  - {linea}" for linea in d["incidencias"]
        ) + "\n"

    cuerpo = (
        f"Hola {d['responsable']}:\n\n"
        f"Se confirmo la devolucion del prestamo {d['folio']}.\n"
        f"Resultado: {'se reportaron incidencias' if hay_incidencias else 'todo en buen estado'}.\n"
        f"{detalle}\n"
        f"Consulta el detalle en: "
        f"{_enlace(d['url_publica'], RUTA_PRESTAMO.format(folio=d['folio']))}"
        f"{PIE}"
    )
    return asunto, cuerpo


def vencimiento(d: dict) -> tuple[str, str]:
    dias = d.get("dias_atraso", 0)
    plural = "s" if dias != 1 else ""
    asunto = f"[GOCreate] Equipo con {dias} dia{plural} de atraso — {d['folio']}"
    cuerpo = (
        f"El prestamo {d['folio']} paso su fecha de regreso.\n\n"
        f"Responsable: {d['responsable']}\n"
        f"Fecha de regreso esperada: {d.get('fecha_regreso_esperada') or '—'}\n"
        f"Dias de atraso: {dias}\n\n"
        f"Equipos pendientes de devolver:\n{_lista(d.get('equipos') or [])}\n\n"
        f"Registra la devolucion en: "
        f"{_enlace(d['url_publica'], RUTA_PRESTAMO.format(folio=d['folio']))}"
        f"{PIE}"
    )
    return asunto, cuerpo


PLANTILLAS = {
    TIPO_CONFIRMADO_APROBADOR: confirmado_aprobador,
    TIPO_CONFIRMADO_RESPONSABLE: confirmado_responsable,
    TIPO_DEVOLUCION_APROBADOR: devolucion_aprobador,
    TIPO_DEVOLUCION_CONFIRMADA: devolucion_confirmada,
    TIPO_VENCIMIENTO: vencimiento,
    TIPO_FIRMA_COMPLETADA: firma_completada,
}


def construir(tipo: str, datos: dict) -> tuple[str, str]:
    """`(asunto, cuerpo)` de una plantilla. El tipo de vencimiento puede venir
    con su sufijo de dia (`vencimiento:2026-07-30`)."""
    base = tipo.split(":", 1)[0]
    plantilla = PLANTILLAS.get(base)
    if plantilla is None:
        raise KeyError(f"No hay plantilla de correo para el tipo '{tipo}'.")
    return plantilla(datos)
