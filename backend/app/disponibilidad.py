"""Disponibilidad de equipo: una sola fuente de verdad, derivada.

**No existe `equipment.estado = 'prestado'`.** La maqueta guardaba ese estado
*y* la lista de equipos dentro del prestamo: dos fuentes para el mismo hecho. Si
un prestamo se borraba o fallaba a medias, el equipo quedaba prestado para
siempre y desaparecia del inventario disponible (§10.1 del plan).

    disponible(equipo) = estado_operativo == 'activo'
                         AND NOT EXISTS (renglon de prestamo abierto)

    renglon abierto = loan_item.devuelto_at IS NULL
                      AND loan.is_deleted = 0

Esa condicion es **exactamente** la del indice unico parcial
`ux_loan_item_equipo_abierto`. Que coincidan no es casualidad: si la formula
fuera mas laxa que el indice, la pantalla mostraria un equipo disponible que da
409 al pedirlo; si fuera mas estricta, escondaria equipos que si se pueden
prestar.

Nota sobre el plan: §4.2 enumera ademas `loan.estado IN ('prestado',
'pendiente_confirmacion')`. El contrato v1 §2 no enumera estados —dice "sin
renglon de prestamo abierto"— y §3 exige que `POST /loans/{id}/items` de 409 si
el equipo ya esta en otro prestamo abierto, con el indice unico como arbitro.
Con esa combinacion, un `borrador` que ya tiene renglones **si** reserva. Se
sigue el contrato. La contradiccion esta reportada en
`docs/avances/servidor.md`.

Consecuencia que la API debe respetar: toda operacion que libere un equipo
(cancelar, confirmar devolucion, borrar el prestamo) tiene que escribir
`devuelto_at`. Si no, el indice bloquea lo que la formula muestra libre.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import tz
from .models_equipos import EstadoOperativo, Loan, LoanItem

__all__ = [
    "PrestamoAbierto",
    "subconsulta_equipos_ocupados",
    "ids_ocupados",
    "mapa_prestamos_abiertos",
    "esta_disponible",
    "esta_disponible_en_db",
    "item_abierto_de",
]


@dataclass(frozen=True)
class PrestamoAbierto:
    """Lo que la fila del inventario necesita saber del prestamo que retiene el
    equipo. El contrato §2 lo pide **en la fila del listado**, no en un segundo
    request: la pantalla de inventario lo pinta directo."""

    loan_id: int
    loan_item_id: int
    folio: str | None
    estado: str
    responsable_user_id: int | None
    responsable_nombre: str | None
    fecha_regreso_esperada: date | None
    atrasado: bool
    dias_atraso: int


def subconsulta_equipos_ocupados():
    """`SELECT equipment_id` de los renglones abiertos. Para usar con `.in_()`
    en el listado sin traer nada a memoria."""
    return (
        select(LoanItem.equipment_id)
        .join(Loan, Loan.id == LoanItem.loan_id)
        .where(LoanItem.devuelto_at.is_(None))
        .where(Loan.is_deleted.is_(False))
    )


def ids_ocupados(db: Session) -> set[int]:
    return {fila[0] for fila in db.execute(subconsulta_equipos_ocupados()).all()}


def item_abierto_de(db: Session, equipment_id: int) -> LoanItem | None:
    """El renglon abierto de un equipo, si lo hay. Por el indice unico parcial
    hay a lo sumo uno; que devuelva uno solo no es una simplificacion."""
    return (
        db.query(LoanItem)
        .join(Loan, Loan.id == LoanItem.loan_id)
        .filter(LoanItem.equipment_id == equipment_id)
        .filter(LoanItem.devuelto_at.is_(None))
        .filter(Loan.is_deleted.is_(False))
        .first()
    )


def mapa_prestamos_abiertos(
    db: Session,
    equipment_ids: list[int] | None = None,
    referencia: date | None = None,
) -> dict[int, PrestamoAbierto]:
    """`{equipment_id: PrestamoAbierto}` en **una** consulta.

    Una consulta por equipo (N+1) es lo que convierte un listado de 8 equipos en
    9 viajes a la base y uno de 200 en 201. El atraso se calcula aqui, en
    servidor y con fecha de CDMX: el cliente nunca lo recalcula (contrato §0).
    """
    referencia = referencia or tz.hoy()

    consulta = (
        db.query(
            LoanItem.equipment_id,
            LoanItem.id,
            Loan.id,
            Loan.folio,
            Loan.estado,
            Loan.responsable_user_id,
            Loan.responsable_nombre,
            Loan.fecha_regreso_esperada,
        )
        .join(Loan, Loan.id == LoanItem.loan_id)
        .filter(LoanItem.devuelto_at.is_(None))
        .filter(Loan.is_deleted.is_(False))
    )
    if equipment_ids is not None:
        if not equipment_ids:
            return {}
        consulta = consulta.filter(LoanItem.equipment_id.in_(equipment_ids))

    salida: dict[int, PrestamoAbierto] = {}
    for (
        equipment_id,
        loan_item_id,
        loan_id,
        folio,
        estado,
        responsable_user_id,
        responsable_nombre,
        fecha_regreso_esperada,
    ) in consulta.all():
        dias = tz.dias_de_atraso(fecha_regreso_esperada, referencia)
        salida[equipment_id] = PrestamoAbierto(
            loan_id=loan_id,
            loan_item_id=loan_item_id,
            folio=folio,
            estado=estado,
            responsable_user_id=responsable_user_id,
            responsable_nombre=responsable_nombre,
            fecha_regreso_esperada=fecha_regreso_esperada,
            atrasado=dias > 0,
            dias_atraso=dias,
        )
    return salida


def esta_disponible(equipo, *, ocupado: bool) -> bool:
    """Un equipo esta disponible si opera y no tiene renglon abierto.

    `ocupado` es obligatorio y explicito a proposito. Con un default el listado
    podria olvidarse de pasarlo y todo saldria "disponible" sin que nada fallara
    — que es el mismo modo de error que el plan quiere evitar: la pantalla dice
    libre y el POST da 409.
    """
    if equipo.estado_operativo != EstadoOperativo.ACTIVO.value:
        return False
    if getattr(equipo, "is_deleted", False):
        return False
    return not ocupado


def esta_disponible_en_db(db: Session, equipo) -> bool:
    """Version de una sola fila: consulta por su cuenta. Para el listado usa
    `mapa_prestamos_abiertos` + `esta_disponible`, no esta."""
    return esta_disponible(equipo, ocupado=item_abierto_de(db, equipo.id) is not None)
