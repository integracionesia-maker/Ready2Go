"""Gastos operativos: acumulador por rubro, fusionado en la UI con Gastos
Generales (Presupuestos). Tabla y endpoints propios (campos distintos:
`rubro_id`/dos fechas/solo borrado logico), misma puerta de acceso que
`general_expenses.py` (`require_role`, ya no el modulo RBAC aditivo
`gastos_operativos`, retirado del catalogo).

El comprobante es obligatorio y el mes se define por `fecha_gasto` (manual), no
por la fecha de subida. Los archivos se sirven SOLO por `GET /{id}/file` con
sesion — nunca por mount estatico.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import crud, crud_operativos, models, schemas_operativos as schemas
from ..database import get_db, SessionLocal
from ..dependencies import require_role
from ..upload_manager import save_upload, delete_upload

router = APIRouter(prefix="/api/operational-expenses", tags=["gastos-operativos"])


def _to_response(e: models.OperationalExpense) -> schemas.OperationalExpenseResponse:
    return schemas.OperationalExpenseResponse(
        id=e.id,
        rubro_id=e.rubro_id,
        rubro_nombre=e.rubro.nombre if e.rubro else None,
        amount=e.amount,
        description=e.description,
        fecha_gasto=e.fecha_gasto,
        file_name=e.file_name,
        mime_type=e.mime_type,
        upload_date=e.upload_date,
        created_by_user_id=e.created_by_user_id,
        is_deleted=e.is_deleted,
        deleted_at=e.deleted_at,
    )


# ── Rutas literales ANTES de /{expense_id}/... para que no las capture el int ──


@router.get("/", response_model=List[schemas.OperationalExpenseResponse])
def list_expenses(
    rubro_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expenses = crud_operativos.list_expenses(
        db, rubro_id=rubro_id, start_date=start_date, end_date=end_date
    )
    return [_to_response(e) for e in expenses]


@router.get("/dashboard", response_model=schemas.OperationalDashboardResponse)
def dashboard(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud_operativos.dashboard(db, start_date=start_date, end_date=end_date)


@router.get("/export", response_model=schemas.OperationalExportResponse)
def export_expenses(
    months: str = Query(..., description="Meses 'YYYY-MM' separados por coma (por fecha_gasto)."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    month_list = [m.strip() for m in months.split(",") if m.strip()]
    if not month_list:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos un mes.")
    expenses = crud_operativos.for_export(db, month_list)
    total = sum(e.amount for e in expenses)
    return schemas.OperationalExportResponse(
        months=month_list, items=[_to_response(e) for e in expenses], total=total
    )


@router.get("/{expense_id}/file")
def download_file(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expense = crud_operativos.get_expense(db, expense_id)
    if not expense or expense.is_deleted:
        raise HTTPException(status_code=404, detail="Gasto operativo no encontrado.")
    # `content_disposition_type="inline"`: sin esto, FileResponse con `filename`
    # manda Content-Disposition: attachment por default y el navegador
    # descarga el PDF en vez de mostrarlo en el <iframe> del visor.
    return FileResponse(
        path=expense.file_path,
        media_type=expense.mime_type,
        filename=expense.file_name,
        content_disposition_type="inline",
    )


@router.post("/", response_model=schemas.OperationalExpenseResponse, status_code=201)
def create_expense(
    rubro_id: int = Form(..., gt=0),
    amount: float = Form(..., gt=0),
    description: str = Form(..., min_length=1, max_length=500),
    fecha_gasto: date = Form(..., description="Fecha en que se hizo el gasto (define el mes)."),
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    db: Session = SessionLocal()
    file_path_on_disk: Optional[str] = None
    try:
        rubro = crud_operativos.get_rubro(db, rubro_id)
        if not rubro:
            raise HTTPException(status_code=404, detail="Rubro no encontrado.")
        if not rubro.is_active:
            raise HTTPException(status_code=400, detail="El rubro está inactivo.")

        # save_upload valida extensión + MIME + tamaño (mismo criterio que el
        # resto de comprobantes) y guarda con nombre uuid.
        file_name, file_path_on_disk, mime_type = save_upload(file)

        expense = crud_operativos.create_expense(
            db=db,
            rubro=rubro,
            amount=amount,
            description=description,
            fecha_gasto=fecha_gasto,
            file_name=file_name,
            file_path=file_path_on_disk,
            mime_type=mime_type,
            actor_user_id=current_user.id,
        )
        crud.log_audit(
            db,
            actor_user_id=current_user.id,
            action="operational-expense.create",
            target_type="operational_expense",
            target_id=expense.id,
            details=f"rubro_id={rubro_id}",
        )
        return _to_response(expense)
    except HTTPException:
        db.rollback()
        if file_path_on_disk:
            delete_upload(file_path_on_disk)
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        if file_path_on_disk:
            delete_upload(file_path_on_disk)
        raise HTTPException(status_code=500, detail=f"Error inesperado al crear el gasto operativo: {exc}")
    finally:
        db.close()


@router.post("/{expense_id}/soft-delete", response_model=schemas.OperationalExpenseResponse)
def soft_delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    expense = crud_operativos.get_expense(db, expense_id)
    if not expense or expense.is_deleted:
        raise HTTPException(status_code=404, detail="Gasto operativo no encontrado.")
    expense = crud_operativos.soft_delete_expense(db, expense, actor_user_id=current_user.id)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="operational-expense.soft-delete",
        target_type="operational_expense",
        target_id=expense.id,
    )
    return _to_response(expense)
