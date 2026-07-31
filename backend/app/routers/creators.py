"""REST endpoints for creators, incluida la gestión de su ciclo de presupuesto (R7)."""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/creators", tags=["creators"])

VALID_PERIODS = {p.value for p in models.CyclePeriod}


def _validate_period(period: str) -> None:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400, detail=f"Periodicidad inválida: '{period}'. Usa 'semanal' o 'mensual'."
        )


@router.get("/", response_model=List[schemas.CreatorResponse])
def list_creators(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    creators = crud.get_creators(db, active_only=active_only)
    if current_user.role == "creador":
        creators = [c for c in creators if c.id == current_user.creator_id]
    return [crud.creator_to_response(db, c) for c in creators]


@router.get("/kpi", response_model=schemas.CreatorKpiResponse)
def get_kpi(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_creators_kpi(db)


@router.get("/{creator_id}", response_model=schemas.CreatorResponse)
def get_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "creador" and creator_id != current_user.creator_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")
    creator = crud.get_creator(db, creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creador no encontrado.")
    return crud.creator_to_response(db, creator)


@router.get("/{creator_id}/ciclos", response_model=List[schemas.BudgetCycleResponse])
def get_creator_cycles(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "creador" and creator_id != current_user.creator_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")
    creator = crud.get_creator(db, creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creador no encontrado.")
    # Asegura que el ciclo vigente ya esté materializado antes de listar el histórico.
    crud.get_or_create_cycle_for_date(db, creator, date.today())
    cycles = crud.list_cycles_for_creator(db, creator_id)
    return [crud.cycle_to_response(c) for c in cycles]


@router.post("/", response_model=schemas.CreatorResponse, status_code=201)
def create_creator(
    data: schemas.CreatorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    _validate_period(data.cycle_period)
    creator = crud.create_creator(db, data)
    return crud.creator_to_response(db, creator)


@router.put("/{creator_id}", response_model=schemas.CreatorResponse)
def update_creator(
    creator_id: int,
    data: schemas.CreatorUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    creator = crud.get_creator(db, creator_id)
    if not creator:
        raise HTTPException(status_code=404, detail="Creador no encontrado.")
    if data.cycle_period is not None:
        _validate_period(data.cycle_period)
    creator = crud.update_creator(db, creator, data)
    return crud.creator_to_response(db, creator)
