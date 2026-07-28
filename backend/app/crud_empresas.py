"""CRUD de razones sociales.

La razon social emisora de la carta responsiva sale de esta tabla, **jamas
hardcode en el PDF** (§10.21 del plan: la maqueta las tenia escritas en un
`<select>` del JavaScript, asi que cambiar una exigia tocar codigo).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models_equipos import Empresa

__all__ = [
    "listar",
    "obtener",
    "obtener_por_razon_social",
    "crear",
    "actualizar",
    "emisora_por_defecto",
]


def listar(db: Session, *, solo_activas: bool = False) -> list[Empresa]:
    consulta = db.query(Empresa)
    if solo_activas:
        consulta = consulta.filter(Empresa.is_active.is_(True))
    return consulta.order_by(Empresa.id).all()


def obtener(db: Session, empresa_id: int) -> Empresa | None:
    return db.get(Empresa, empresa_id)


def obtener_por_razon_social(db: Session, razon_social: str) -> Empresa | None:
    return db.query(Empresa).filter(Empresa.razon_social == razon_social).first()


def crear(db: Session, datos: dict) -> Empresa:
    empresa = Empresa(**datos)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


def actualizar(db: Session, empresa: Empresa, datos: dict) -> Empresa:
    for campo, valor in datos.items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa


def emisora_por_defecto(db: Session) -> Empresa | None:
    """La que emite la carta responsiva.

    Hoy es "la primera activa con RFC": la emisora es la unica que necesita RFC y
    direccion para el encabezado del PDF, las otras dos razones sociales del
    inventario son las del colaborador. Es una heuristica, no una regla de
    negocio confirmada — §14.3 del plan tiene pendiente que marketing diga cual
    es la emisora correcta. Cuando lo confirmen, esto se vuelve una columna
    explicita (`es_emisora`) y deja de adivinar.
    """
    return (
        db.query(Empresa)
        .filter(Empresa.is_active.is_(True))
        .filter(Empresa.rfc.isnot(None))
        .order_by(Empresa.id)
        .first()
    )
