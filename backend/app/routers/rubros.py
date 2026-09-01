"""Catalogo de rubros de Gastos Operativos (fusionado en la UI con Gastos
Generales de Presupuestos).

Rubro = la clasificacion del gasto (E-commerce, IA, Aplicaciones, ...). Editable
desde la app. Misma puerta de acceso que `general_expenses.py`/`operational_expenses.py`
(`require_role`, ya no el modulo RBAC aditivo `gastos_operativos`, retirado del
catalogo).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, crud_operativos, models, schemas_operativos as schemas
from ..database import get_db
from ..dependencies import require_role

router = APIRouter(prefix="/api/rubros", tags=["gastos-operativos"])


@router.get("/", response_model=List[schemas.RubroResponse])
def list_rubros(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud_operativos.list_rubros(db, active_only=active_only)


@router.post("/", response_model=schemas.RubroResponse, status_code=201)
def create_rubro(
    data: schemas.RubroCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    nombre = data.nombre.strip()
    if crud_operativos.get_rubro_by_nombre(db, nombre):
        raise HTTPException(status_code=409, detail=f"Ya existe un rubro con el nombre '{nombre}'.")
    rubro = crud_operativos.create_rubro(db, nombre=nombre)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="rubro.create",
        target_type="expense_rubro",
        target_id=rubro.id,
        details=f"nombre={nombre}",
    )
    return rubro


@router.put("/{rubro_id}", response_model=schemas.RubroResponse)
def update_rubro(
    rubro_id: int,
    data: schemas.RubroUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    rubro = crud_operativos.get_rubro(db, rubro_id)
    if not rubro:
        raise HTTPException(status_code=404, detail="Rubro no encontrado.")

    nombre = data.nombre.strip() if data.nombre is not None else None
    if nombre is not None and nombre != rubro.nombre:
        existente = crud_operativos.get_rubro_by_nombre(db, nombre)
        if existente and existente.id != rubro.id:
            raise HTTPException(status_code=409, detail=f"Ya existe un rubro con el nombre '{nombre}'.")

    rubro = crud_operativos.update_rubro(db, rubro, nombre=nombre, is_active=data.is_active)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="rubro.update",
        target_type="expense_rubro",
        target_id=rubro.id,
    )
    return rubro
