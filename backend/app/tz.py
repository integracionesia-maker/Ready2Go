"""Zona horaria unica del modulo de Equipos: America/Mexico_City.

Por que existe este archivo en vez de usar `datetime.now()` a secas: la maqueta
calculaba el atraso comparando cadenas de `toISOString()`, que es UTC. Entre las
18:00 y la medianoche de CDMX eso marca un prestamo como atrasado **un dia
antes** (§10.13 del plan). El calculo de atraso vive en el servidor y en esta
zona, y el cliente nunca lo recalcula (contrato §0).

Convencion de almacenamiento del proyecto: las columnas `DateTime` guardan UTC
**sin** tzinfo (SQLite descarta el offset). El resto del codigo ya asume eso
—`refresh_tokens.expires_at` se compara contra
`datetime.now(timezone.utc).replace(tzinfo=None)`—. Aqui se respeta: se guarda
UTC naive y se convierte a CDMX solo al serializar.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Mexico_City")

__all__ = [
    "ZONA",
    "ahora",
    "ahora_utc_naive",
    "hoy",
    "a_cdmx",
    "iso_cdmx",
    "iso_fecha",
    "dias_de_atraso",
    "esta_atrasado",
]


def ahora() -> datetime:
    """Instante actual, consciente de zona, en CDMX."""
    return datetime.now(ZONA)


def ahora_utc_naive() -> datetime:
    """Lo que se escribe en una columna `DateTime`: UTC sin tzinfo."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hoy() -> date:
    """Fecha de hoy en CDMX. **Nunca** `date.today()` del servidor ni UTC: es
    justo la diferencia que hace que un prestamo se marque atrasado antes de
    tiempo."""
    return ahora().date()


def a_cdmx(valor: datetime | None) -> datetime | None:
    """UTC naive (como esta en la base) -> aware en CDMX.

    Si el valor ya trae tzinfo se respeta y solo se convierte: asi la funcion
    sirve igual para lo que viene de la base y para lo que se acaba de crear.
    """
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(ZONA)


def iso_cdmx(valor: datetime | None) -> str | None:
    """ISO-8601 con offset, como pide el contrato: `2026-07-27T17:45:00-06:00`.

    Se recorta a segundos: los microsegundos no aportan nada al usuario y
    romperian cualquier comparacion literal contra un fixture congelado.
    """
    convertido = a_cdmx(valor)
    return convertido.replace(microsecond=0).isoformat() if convertido else None


def iso_fecha(valor: date | None) -> str | None:
    """`YYYY-MM-DD`. Las columnas DATE ya estan en fecha civil de CDMX."""
    return valor.isoformat() if valor else None


def dias_de_atraso(fecha_regreso_esperada: date | None, referencia: date | None = None) -> int:
    """Dias completos de atraso. 0 si no hay fecha o si aun no vence.

    Vence **al terminar** el dia esperado: entregar el mismo dia no es atraso.
    """
    if fecha_regreso_esperada is None:
        return 0
    referencia = referencia or hoy()
    diferencia = (referencia - fecha_regreso_esperada).days
    return diferencia if diferencia > 0 else 0


def esta_atrasado(fecha_regreso_esperada: date | None, referencia: date | None = None) -> bool:
    return dias_de_atraso(fecha_regreso_esperada, referencia) > 0
