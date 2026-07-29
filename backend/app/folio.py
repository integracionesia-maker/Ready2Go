"""Asignacion de folio: `CE-0001`, transaccional, con reintentos.

En la maqueta el contador vivia en el estado del navegador: dos pestañas
producian el mismo folio y nadie se enteraba hasta que dos cartas responsivas
distintas decian `CE-0007` (§10.5 del plan).

Aqui hay tres capas, y las tres hacen falta:

1. `folio_counter` incrementado con un `UPDATE` (atomico en SQLite dentro de la
   transaccion; no es un read-modify-write en Python).
2. `loan.folio UNIQUE` en la base: el arbitro final. Si dos transacciones
   concurrentes se las arreglan para leer el mismo valor, una se estrella aqui.
3. Tres reintentos: la que se estrella vuelve a pedir numero. Tambien resuelve el
   caso de un contador que se quedo atras de los folios ya existentes (por
   ejemplo despues de restaurar un respaldo o de sembrar datos de demostracion).

El folio se asigna **al confirmar**, no al crear el borrador: quemar numeros en
borradores abandonados deja huecos que despues alguien intenta explicar.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models_equipos import FolioCounter, Loan

__all__ = [
    "SCOPE_EQUIPOS",
    "REINTENTOS",
    "FolioNoDisponible",
    "formatear",
    "asignar_folio",
    "asegurar_contador",
    "sincronizar_contador",
]

SCOPE_EQUIPOS = "CE"
REINTENTOS = 3
ANCHO = 4


class FolioNoDisponible(RuntimeError):
    """No se pudo asignar folio tras los reintentos. Que salga como error y no
    como folio duplicado: un folio repetido en dos cartas firmadas es peor que
    un prestamo que no se confirmo."""


def formatear(valor: int, scope: str = SCOPE_EQUIPOS) -> str:
    return f"{scope}-{valor:0{ANCHO}d}"


def asegurar_contador(db: Session, scope: str = SCOPE_EQUIPOS) -> None:
    if db.get(FolioCounter, scope) is None:
        db.add(FolioCounter(scope=scope, last_value=0))
        db.flush()


def _siguiente_valor(db: Session, scope: str) -> int:
    """Incrementa y devuelve. El `UPDATE ... = last_value + 1` lo resuelve la
    base; leer en Python, sumar y escribir seria la carrera que queremos evitar."""
    db.execute(
        text("UPDATE folio_counter SET last_value = last_value + 1 WHERE scope = :scope"),
        {"scope": scope},
    )
    return db.execute(
        text("SELECT last_value FROM folio_counter WHERE scope = :scope"),
        {"scope": scope},
    ).scalar_one()


def asignar_folio(db: Session, loan: Loan, scope: str = SCOPE_EQUIPOS) -> str:
    """Asigna folio al prestamo y lo devuelve. Idempotente: si ya tiene, no lo
    cambia — un folio ya impreso en una carta firmada no se toca."""
    if loan.folio:
        return loan.folio

    ultimo_error: Exception | None = None
    for _ in range(REINTENTOS):
        # El incremento va FUERA del SAVEPOINT a proposito. Adentro, el rollback
        # del choque tambien deshacia el `UPDATE` del contador y el reintento
        # volvia a pedir exactamente el mismo numero: tres intentos identicos
        # que fallaban igual. Fuera, cada reintento avanza de verdad.
        asegurar_contador(db, scope)
        candidato = formatear(_siguiente_valor(db, scope), scope)

        punto = db.begin_nested()  # SAVEPOINT: un choque no tira la transaccion entera
        try:
            loan.folio = candidato
            db.flush()  # aqui pega el UNIQUE si el folio ya existia
            punto.commit()
            return candidato
        except IntegrityError as exc:
            punto.rollback()
            loan.folio = None
            ultimo_error = exc

    raise FolioNoDisponible(
        f"No se pudo asignar folio '{scope}' tras {REINTENTOS} intentos."
    ) from ultimo_error


def sincronizar_contador(db: Session, scope: str = SCOPE_EQUIPOS) -> int:
    """Deja el contador por encima del folio mas alto que ya existe.

    Se usa despues de sembrar datos con folios fijos. Sin esto, el primer
    prestamo real gastaria sus tres reintentos subiendo el contador uno por uno.
    """
    asegurar_contador(db, scope)
    prefijo = f"{scope}-"
    maximo = 0
    for (folio,) in db.query(Loan.folio).filter(Loan.folio.like(f"{prefijo}%")).all():
        try:
            maximo = max(maximo, int(folio[len(prefijo):]))
        except (TypeError, ValueError):
            continue

    contador = db.get(FolioCounter, scope)
    if contador.last_value < maximo:
        contador.last_value = maximo
        db.flush()
    return contador.last_value
