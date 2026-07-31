"""REST endpoints for brands."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/brands", tags=["brands"])

VALID_PRIORITIES = {p.value for p in models.BrandPriority}


def _validate_priority(priority: str) -> None:
    if priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=400, detail=f"Prioridad inválida: '{priority}'. Usa 'alta', 'media' o 'baja'."
        )


@router.get("/", response_model=List[schemas.BrandResponse])
def list_brands(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_brands(db, active_only=active_only)


@router.get("/{brand_id}", response_model=schemas.BrandResponse)
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    brand = crud.get_brand(db, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Marca no encontrada.")
    return brand


@router.post("/", response_model=schemas.BrandResponse, status_code=201)
def create_brand(
    data: schemas.BrandCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    _validate_priority(data.priority)
    try:
        return crud.create_brand(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una marca con ese nombre.")


@router.put("/{brand_id}", response_model=schemas.BrandResponse)
def update_brand(
    brand_id: int,
    data: schemas.BrandUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    brand = crud.get_brand(db, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Marca no encontrada.")
    if data.priority is not None:
        _validate_priority(data.priority)
    try:
        return crud.update_brand(db, brand, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una marca con ese nombre.")
