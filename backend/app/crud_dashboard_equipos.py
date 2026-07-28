"""Consultas del dashboard de Equipos.

**Este modulo no importa `crud_loans`.** Es una regla del reparto y tiene razon
tecnica: el dashboard necesita agregados, no objetos armados. Reusar el CRUD de
prestamos traeria payloads completos para contarlos, y ademas ataria la pantalla
de inicio a los cambios de forma del detalle de prestamo.

Definiciones que el contrato no fija y aqui se eligen (documentadas en
`docs/avances/servidor.md`):

- `prestados`: prestamos en estado `prestado`. No incluye `pendiente_confirmacion`
  —el equipo ya volvio fisicamente— porque esa cifra tiene su propio contador.
- `atrasados`: prestamos en `prestado` cuya fecha de regreso ya paso. Un
  prestamo en `pendiente_confirmacion` no cuenta: el equipo ya esta de vuelta,
  lo que falta es el visto bueno.
- `disponibles`: equipos activos, no borrados y sin renglon abierto. Misma
  formula que el listado, no una copia.
- `por_estado`: **siempre las 6 llaves**, con 0 donde no hay nada. Devolver solo
  las que tienen datos hace que una grafica cambie de forma sola.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import disponibilidad, tz
from .models_equipos import (
    Equipment,
    EstadoOperativo,
    EstadoPrestamo,
    Loan,
    LoanItem,
)

__all__ = ["resumen"]

ORDEN_ESTADOS = [
    EstadoPrestamo.BORRADOR.value,
    EstadoPrestamo.PRESTADO.value,
    EstadoPrestamo.PENDIENTE_CONFIRMACION.value,
    EstadoPrestamo.COMPLETADO.value,
    EstadoPrestamo.INCOMPLETO.value,
    EstadoPrestamo.CANCELADO.value,
]


def _por_estado(db: Session) -> dict[str, int]:
    crudo = dict(
        db.query(Loan.estado, func.count(Loan.id))
        .filter(Loan.is_deleted.is_(False))
        .group_by(Loan.estado)
        .all()
    )
    return {estado: int(crudo.get(estado, 0)) for estado in ORDEN_ESTADOS}


def _disponibles(db: Session) -> int:
    ocupados = disponibilidad.subconsulta_equipos_ocupados()
    return (
        db.query(func.count(Equipment.id))
        .filter(Equipment.is_deleted.is_(False))
        .filter(Equipment.estado_operativo == EstadoOperativo.ACTIVO.value)
        .filter(~Equipment.id.in_(ocupados))
        .scalar()
        or 0
    )


def _equipos_por_prestamo(db: Session, loan_ids: list[int]) -> dict[int, list[str]]:
    """Nombres de equipo por prestamo, en una consulta. La lista de "requiere
    atencion" los pinta, y pedirlos uno por uno seria N+1 en la pantalla de
    inicio, que es la que mas se abre."""
    if not loan_ids:
        return {}
    salida: dict[int, list[str]] = {}
    filas = (
        db.query(LoanItem.loan_id, Equipment.nombre)
        .join(Equipment, Equipment.id == LoanItem.equipment_id)
        .filter(LoanItem.loan_id.in_(loan_ids))
        .order_by(LoanItem.id)
        .all()
    )
    for loan_id, nombre in filas:
        salida.setdefault(loan_id, []).append(nombre)
    return salida


def _requiere_atencion(db: Session, referencia: date) -> list[dict]:
    """Un renglon por prestamo, con el motivo mas grave.

    Prioridad: atraso > devolucion por confirmar > entrega sin autorizar. Un
    prestamo atrasado *y* sin autorizar sale una sola vez, como atrasado: una
    lista con el mismo folio tres veces no ayuda a nadie.
    """
    candidatos = (
        db.query(Loan)
        .filter(Loan.is_deleted.is_(False))
        .filter(
            Loan.estado.in_(
                [
                    EstadoPrestamo.PRESTADO.value,
                    EstadoPrestamo.PENDIENTE_CONFIRMACION.value,
                    EstadoPrestamo.INCOMPLETO.value,
                ]
            )
        )
        .order_by(Loan.id)
        .all()
    )

    filas: list[dict] = []
    for prestamo in candidatos:
        dias = (
            tz.dias_de_atraso(prestamo.fecha_regreso_esperada, referencia)
            if prestamo.estado == EstadoPrestamo.PRESTADO.value
            else 0
        )
        if dias > 0:
            motivo = f"atrasado {dias} dia" + ("s" if dias != 1 else "")
        elif prestamo.estado == EstadoPrestamo.PENDIENTE_CONFIRMACION.value:
            motivo = "devolucion por confirmar"
        elif prestamo.estado == EstadoPrestamo.INCOMPLETO.value:
            motivo = "incidencia abierta"
        elif not prestamo.entrega_autorizada:
            motivo = "entrega sin autorizar"
        else:
            continue

        filas.append(
            {
                "loan_id": prestamo.id,
                "folio": prestamo.folio,
                "motivo": motivo,
                "responsable": prestamo.responsable_nombre,
                "equipos": [],
            }
        )

    equipos = _equipos_por_prestamo(db, [fila["loan_id"] for fila in filas])
    for fila in filas:
        fila["equipos"] = equipos.get(fila["loan_id"], [])
    return filas


def resumen(db: Session, referencia: date | None = None) -> dict:
    referencia = referencia or tz.hoy()
    por_estado = _por_estado(db)

    atrasados = (
        db.query(func.count(Loan.id))
        .filter(Loan.is_deleted.is_(False))
        .filter(Loan.estado == EstadoPrestamo.PRESTADO.value)
        .filter(Loan.fecha_regreso_esperada.isnot(None))
        .filter(Loan.fecha_regreso_esperada < referencia)
        .scalar()
        or 0
    )

    return {
        "prestados": por_estado[EstadoPrestamo.PRESTADO.value],
        "atrasados": int(atrasados),
        "pendientes_confirmacion": por_estado[EstadoPrestamo.PENDIENTE_CONFIRMACION.value],
        "disponibles": _disponibles(db),
        "por_estado": por_estado,
        "requiere_atencion": _requiere_atencion(db, referencia),
    }
