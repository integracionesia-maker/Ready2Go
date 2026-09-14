"""Las plantillas de correo de Control de Equipos.

Texto plano, en español, tono sobrio, **cero emojis**. Funciones puras: reciben
un diccionario y devuelven `(asunto, cuerpo)`. No tocan la base ni el mailer, asi
que se prueban sin sesion y sin servidor de correo.

Unico disparador en todo el modulo: la creacion del prestamo (`confirmar` en
`routers/loans.py`, el momento en que se asigna folio y se genera la
responsiva). El plan original (§7) pedia tambien avisos de firma, devolucion y
vencimiento; se retiraron a proposito (decision posterior al plan) — no
avisar en esos otros eventos.

Los textos son propuesta del servidor: no la redaccion final. Son mensajes de
cara a personas de Grupo Ortiz, asi que conviene que marketing los apruebe
antes del piloto.
"""

from __future__ import annotations

__all__ = [
    "TIPO_CONFIRMADO_APROBADOR",
    "TIPO_CONFIRMADO_RESPONSABLE",
    "TIPO_CONFIRMADO_TITULAR_FIRMA",
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
# Distinto de TIPO_CONFIRMADO_APROBADOR: ese va a quien tiene
# `equipos_aprobacion:autorizar_entrega` (APROBADOR_EQUIPO); este va a quien
# tiene HOY el paquete singleton TITULAR_FIRMA_EQUIPO — hoy la misma persona
# (Melisa), pero son paquetes desacoplados a proposito (ver
# `docs/equipos/firma-pendiente-al-confirmar.md` §Titular), asi que el titular
# puede cambiar sin que cambie quien aprueba, y viceversa. Se manda una sola
# vez en la vida del prestamo: se dispara en el mismo punto que
# TIPO_CONFIRMADO_APROBADOR (`confirmar`, el unico momento en que se asigna
# folio y se genera la responsiva) y la idempotencia de `notification_log`
# (UNIQUE loan_id+tipo+destinatario) hace el resto.
TIPO_CONFIRMADO_TITULAR_FIRMA = "confirmado_titular_firma"

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


def confirmado_titular_firma(d: dict) -> tuple[str, str]:
    asunto = f"[GOCreate] Prestamo {d['folio']} espera tu firma"
    cuerpo = (
        f"Se registro un prestamo de equipo que necesita tu firma como titular.\n\n"
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
        f"Para firmar: "
        f"{_enlace(d['url_publica'], RUTA_PRESTAMO.format(folio=d['folio']))}"
        f"{PIE}"
    )
    return asunto, cuerpo


PLANTILLAS = {
    TIPO_CONFIRMADO_APROBADOR: confirmado_aprobador,
    TIPO_CONFIRMADO_RESPONSABLE: confirmado_responsable,
    TIPO_CONFIRMADO_TITULAR_FIRMA: confirmado_titular_firma,
}


def construir(tipo: str, datos: dict) -> tuple[str, str]:
    """`(asunto, cuerpo)` de una plantilla."""
    plantilla = PLANTILLAS.get(tipo)
    if plantilla is None:
        raise KeyError(f"No hay plantilla de correo para el tipo '{tipo}'.")
    return plantilla(datos)
