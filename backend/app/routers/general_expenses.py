"""REST endpoints para gastos generales (R12): gastos operativos vinculados a
una marca. Solo admin/superadmin — no pasan por validación, no tienen ciclo de
presupuesto. Ver doc/gastos-generales-manual.md."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db, SessionLocal
from ..dependencies import require_role
from ..upload_manager import save_upload, delete_upload

router = APIRouter(prefix="/api/general-expenses", tags=["general-expenses"])


def _expense_to_response(e: models.GeneralExpense) -> schemas.GeneralExpenseResponse:
    return schemas.GeneralExpenseResponse(
        id=e.id,
        brand_id=e.brand_id,
        amount=e.amount,
        description=e.description,
        file_name=e.file_name,
        file_path=e.file_path,
        mime_type=e.mime_type,
        upload_date=e.upload_date,
        created_by_user_id=e.created_by_user_id,
        is_deleted=e.is_deleted,
        deleted_at=e.deleted_at,
        brand_name=e.brand.name if e.brand else None,
        brand_priority=e.brand.priority if e.brand else None,
    )


@router.get("/", response_model=List[schemas.GeneralExpenseResponse])
def list_general_expenses(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expenses = crud.get_general_expenses(db, start_date=start_date, end_date=end_date)
    return [_expense_to_response(e) for e in expenses]


@router.get("/export", response_model=schemas.GeneralExpensesExportResponse)
def export_general_expenses(
    months: str = Query(..., description="Meses separados por coma, ej. '2026-07,2026-08'"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    month_list = [m.strip() for m in months.split(",") if m.strip()]
    if not month_list:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos un mes.")

    expenses = crud.get_general_expenses_for_export(db, month_list)
    total = sum(e.amount for e in expenses)
    return schemas.GeneralExpensesExportResponse(
        months=month_list,
        items=[_expense_to_response(e) for e in expenses],
        total=total,
    )


@router.get("/{expense_id}/file")
def download_general_expense_file(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expense = crud.get_general_expense(db, expense_id)
    if not expense or expense.is_deleted:
        raise HTTPException(status_code=404, detail="Gasto general no encontrado.")
    return FileResponse(path=expense.file_path, media_type=expense.mime_type, filename=expense.file_name)


@router.post("/", response_model=schemas.GeneralExpenseResponse, status_code=201)
def create_general_expense(
    brand_id: int = Form(..., gt=0),
    amount: float = Form(..., gt=0),
    description: str = Form(..., min_length=1, max_length=500),
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    db: Session = SessionLocal()
    file_path_on_disk: Optional[str] = None

    try:
        brand = crud.get_brand(db, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Marca no encontrada.")
        if not brand.is_active:
            raise HTTPException(status_code=400, detail="La marca está inactiva.")

        file_name, file_path_on_disk, mime_type = save_upload(file)

        expense = crud.create_general_expense(
            db=db,
            brand=brand,
            amount=amount,
            description=description,
            file_name=file_name,
            file_path=file_path_on_disk,
            mime_type=mime_type,
            actor_user_id=current_user.id,
        )
        crud.log_audit(
            db,
            actor_user_id=current_user.id,
            action="general-expense.create",
            target_type="general_expense",
            target_id=expense.id,
            details=f"brand_id={brand_id}",
        )
        return _expense_to_response(expense)

    except HTTPException:
        db.rollback()
        if file_path_on_disk:
            delete_upload(file_path_on_disk)
        raise
    except Exception as exc:
        db.rollback()
        if file_path_on_disk:
            delete_upload(file_path_on_disk)
        raise HTTPException(status_code=500, detail=f"Error inesperado al crear el gasto general: {exc}")
    finally:
        db.close()


@router.post("/{expense_id}/soft-delete", response_model=schemas.GeneralExpenseResponse)
def soft_delete_general_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expense = crud.get_general_expense(db, expense_id)
    if not expense or expense.is_deleted:
        raise HTTPException(status_code=404, detail="Gasto general no encontrado.")

    expense = crud.soft_delete_general_expense(db, expense, actor_user_id=current_user.id)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="general-expense.soft-delete",
        target_type="general_expense",
        target_id=expense.id,
    )
    return _expense_to_response(expense)


@router.delete("/{expense_id}/permanent", response_model=schemas.MessageResponse)
def hard_delete_general_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expense = crud.get_general_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Gasto general no encontrado.")

    expense_id_for_log = expense.id
    crud.hard_delete_general_expense(db, expense)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="general-expense.hard-delete",
        target_type="general_expense",
        target_id=expense_id_for_log,
    )
    return schemas.MessageResponse(message="Gasto general eliminado permanentemente.")
