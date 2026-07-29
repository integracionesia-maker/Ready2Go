"""Acceso a datos del inventario.

Dos cosas que aqui se hacen a proposito y conviene no "simplificar":

1. La condicion, el estado fisico y el comentario de un equipo **no** son
   columnas de `equipment`: salen de su ultima fila de `equipment_audit`. La
   maqueta guardaba solo el ultimo valor y por eso no habia forma de saber si un
   rayon venia de antes del prestamo.
2. El listado resuelve prestamos abiertos y condiciones en **consultas fijas**,
   no una por fila. Con 8 equipos el N+1 no se nota; con 200 son 401 viajes.
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import disponibilidad, tz
from .models import User
from .models_equipos import (
    CondicionEquipo,
    Equipment,
    EquipmentAudit,
    EstadoOperativo,
    Loan,
    LoanItem,
)

__all__ = [
    "LIMITE_DEFAULT",
    "LIMITE_MAXIMO",
    "accesorios_de",
    "serializar_accesorios",
    "obtener",
    "listar",
    "ultima_auditoria_por_equipo",
    "crear",
    "actualizar",
    "registrar_auditoria",
    "dar_de_baja",
    "auditorias_de",
    "historial_de",
]

LIMITE_DEFAULT = 50
LIMITE_MAXIMO = 200


def accesorios_de(equipo: Equipment) -> list[str]:
    """`accesorios_tipicos` es JSON en texto. Un valor corrupto no debe tumbar el
    listado completo: se devuelve vacio y el equipo sigue apareciendo."""
    if not equipo.accesorios_tipicos:
        return []
    try:
        valor = json.loads(equipo.accesorios_tipicos)
    except (TypeError, ValueError):
        return []
    return [str(x) for x in valor] if isinstance(valor, list) else []


def serializar_accesorios(accesorios: list[str] | None) -> str | None:
    if accesorios is None:
        return None
    return json.dumps(list(accesorios), ensure_ascii=False)


def _subconsulta_ultima_auditoria():
    return (
        select(
            EquipmentAudit.equipment_id.label("equipment_id"),
            func.max(EquipmentAudit.id).label("audit_id"),
        )
        .group_by(EquipmentAudit.equipment_id)
        .subquery()
    )


def ultima_auditoria_por_equipo(
    db: Session, equipment_ids: list[int] | None = None
) -> dict[int, EquipmentAudit]:
    """`{equipment_id: ultima auditoria}` en una consulta."""
    ultima = _subconsulta_ultima_auditoria()
    consulta = db.query(EquipmentAudit).join(
        ultima, EquipmentAudit.id == ultima.c.audit_id
    )
    if equipment_ids is not None:
        if not equipment_ids:
            return {}
        consulta = consulta.filter(EquipmentAudit.equipment_id.in_(equipment_ids))
    return {fila.equipment_id: fila for fila in consulta.all()}


def obtener(db: Session, equipment_id: int, *, incluir_borrados: bool = False) -> Equipment | None:
    equipo = db.get(Equipment, equipment_id)
    if equipo is None:
        return None
    if equipo.is_deleted and not incluir_borrados:
        return None
    return equipo


def listar(
    db: Session,
    *,
    q: str | None = None,
    categoria: str | None = None,
    condicion: str | None = None,
    disponible: bool | None = None,
    limit: int = LIMITE_DEFAULT,
    offset: int = 0,
    referencia: date | None = None,
) -> tuple[list[tuple[Equipment, EquipmentAudit | None, disponibilidad.PrestamoAbierto | None, bool]], int]:
    """Devuelve `([(equipo, auditoria, prestamo_abierto, disponible)], total)`.

    El filtro `disponible` se aplica **despues** de resolver los renglones
    abiertos, no en SQL: disponibilidad no es una columna, es una derivada de
    dos cosas (`estado_operativo` y renglon abierto). Meterla en el WHERE
    obligaria a duplicar la formula en SQL y en Python, que es como se
    desincronizan.
    """
    referencia = referencia or tz.hoy()

    ultima = _subconsulta_ultima_auditoria()
    consulta = (
        db.query(Equipment, EquipmentAudit)
        .outerjoin(ultima, ultima.c.equipment_id == Equipment.id)
        .outerjoin(EquipmentAudit, EquipmentAudit.id == ultima.c.audit_id)
        .filter(Equipment.is_deleted.is_(False))
    )

    if q:
        patron = f"%{q.strip()}%"
        consulta = consulta.filter(
            or_(
                Equipment.nombre.ilike(patron),
                Equipment.codigo.ilike(patron),
                Equipment.categoria.ilike(patron),
                Equipment.marca.ilike(patron),
                Equipment.modelo.ilike(patron),
                Equipment.numero_serie.ilike(patron),
                Equipment.activo_fijo.ilike(patron),
                Equipment.cuenta_gmail.ilike(patron),
            )
        )
    if categoria:
        consulta = consulta.filter(Equipment.categoria == categoria)
    if condicion:
        consulta = consulta.filter(EquipmentAudit.condicion == condicion)

    filas = consulta.order_by(Equipment.id).all()

    abiertos = disponibilidad.mapa_prestamos_abiertos(
        db, [equipo.id for equipo, _ in filas], referencia=referencia
    )

    enriquecidas = []
    for equipo, auditoria in filas:
        abierto = abiertos.get(equipo.id)
        libre = disponibilidad.esta_disponible(equipo, ocupado=abierto is not None)
        if disponible is not None and libre is not disponible:
            continue
        enriquecidas.append((equipo, auditoria, abierto, libre))

    total = len(enriquecidas)
    limite = max(1, min(limit, LIMITE_MAXIMO))
    desplazamiento = max(0, offset)
    return enriquecidas[desplazamiento : desplazamiento + limite], total


def crear(db: Session, datos: dict) -> Equipment:
    accesorios = datos.pop("accesorios_tipicos", None)
    equipo = Equipment(**datos, accesorios_tipicos=serializar_accesorios(accesorios or []))
    db.add(equipo)
    db.commit()
    db.refresh(equipo)
    return equipo


def actualizar(db: Session, equipo: Equipment, cambios: dict) -> Equipment:
    if "accesorios_tipicos" in cambios:
        cambios["accesorios_tipicos"] = serializar_accesorios(cambios["accesorios_tipicos"])
    for campo, valor in cambios.items():
        setattr(equipo, campo, valor)
    db.commit()
    db.refresh(equipo)
    return equipo


def registrar_auditoria(
    db: Session, equipo: Equipment, datos: dict, actor_user_id: int | None
) -> EquipmentAudit:
    """Alta en el historial. **Nunca** sobrescribe la anterior.

    Si la auditoria reporta espacio, se copia al equipo: la columna de
    `equipment` es el valor vigente y la fila de auditoria es el registro de
    cuando se midio.
    """
    auditoria = EquipmentAudit(
        equipment_id=equipo.id,
        condicion=datos.get("condicion", CondicionEquipo.BUENO.value),
        estado_fisico=datos.get("estado_fisico"),
        espacio_disponible=datos.get("espacio_disponible"),
        comentario=datos.get("comentario"),
        fecha=datos.get("fecha") or tz.hoy(),
        actor_user_id=actor_user_id,
    )
    db.add(auditoria)

    if datos.get("espacio_disponible") is not None:
        equipo.espacio_disponible = datos["espacio_disponible"]

    db.commit()
    db.refresh(auditoria)
    return auditoria


def dar_de_baja(db: Session, equipo: Equipment, actor_user_id: int | None, motivo: str | None) -> Equipment:
    """Retira el equipo del inventario. Borrado logico: el registro y su
    historial se conservan porque la responsiva ya firmada los referencia."""
    equipo.estado_operativo = EstadoOperativo.BAJA.value
    equipo.is_deleted = True
    equipo.deleted_at = tz.ahora_utc_naive()
    equipo.deleted_by_user_id = actor_user_id

    if motivo:
        db.add(
            EquipmentAudit(
                equipment_id=equipo.id,
                condicion=CondicionEquipo.DANADO.value
                if "dan" in motivo.lower()
                else CondicionEquipo.ATENCION.value,
                comentario=f"Baja de inventario: {motivo}",
                fecha=tz.hoy(),
                actor_user_id=actor_user_id,
            )
        )

    db.commit()
    db.refresh(equipo)
    return equipo


def auditorias_de(db: Session, equipment_id: int) -> list[tuple[EquipmentAudit, str | None]]:
    """Historial completo, de la mas reciente a la mas vieja, con el nombre del
    actor resuelto en la misma consulta."""
    return (
        db.query(EquipmentAudit, User.full_name)
        .outerjoin(User, User.id == EquipmentAudit.actor_user_id)
        .filter(EquipmentAudit.equipment_id == equipment_id)
        .order_by(EquipmentAudit.id.desc())
        .all()
    )


def historial_de(db: Session, equipment_id: int) -> list[tuple[LoanItem, Loan]]:
    """Prestamos por los que paso el equipo, del mas reciente al mas viejo."""
    return (
        db.query(LoanItem, Loan)
        .join(Loan, Loan.id == LoanItem.loan_id)
        .filter(LoanItem.equipment_id == equipment_id)
        .filter(Loan.is_deleted.is_(False))
        .order_by(Loan.id.desc())
        .all()
    )
