"""Dashboard analytics endpoints with date-range filtering."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import crud, crud_operativos, models, schemas
from ..database import get_db
from ..dependencies import require_role
from ..pdf import dashboard_reporte

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_dashboard_summary(db, start_date=start_date, end_date=end_date)


@router.get("/monthly-spend", response_model=List[schemas.MonthlySpendItem])
def monthly_spend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_monthly_spend(db, start_date=start_date, end_date=end_date)


@router.get("/creator-usage", response_model=List[schemas.CreatorUsageItem])
def creator_usage(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_creator_usage(db, start_date=start_date, end_date=end_date)


@router.get("/general-expenses-monthly", response_model=List[schemas.GeneralExpenseMonthlyItem])
def general_expenses_monthly(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_general_expenses_monthly(db, start_date=start_date, end_date=end_date)


@router.get("/tickets-per-day", response_model=List[schemas.TicketsPerDayItem])
def tickets_per_day(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_tickets_per_day(db, start_date=start_date, end_date=end_date)


@router.get("/report.pdf")
def dashboard_report_pdf(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    """Reporte del dashboard generado en backend con reportlab (vectores
    nativos, sin captura de pantalla) — mismo dato que ya ve la pantalla,
    reunido de las funciones CRUD existentes, ninguna logica de negocio nueva.
    `attachment` (no `inline`, a diferencia de la carta responsiva): el boton
    dice "Descargar PDF", es una descarga explicita, no una previsualizacion.
    """
    datos = {
        "kpi": crud.get_creators_kpi(db),
        "summary": crud.get_dashboard_summary(db, start_date=start_date, end_date=end_date),
        "monthly": crud.get_monthly_spend(db, start_date=start_date, end_date=end_date),
        "creator_usage": crud.get_creator_usage(db, start_date=start_date, end_date=end_date),
        "brand_spend": crud.get_brand_spend_breakdown(db, start_date=start_date, end_date=end_date),
        "general_expenses_monthly": crud.get_general_expenses_monthly(db, start_date=start_date, end_date=end_date),
        "operational_dashboard": crud_operativos.dashboard(db, start_date=start_date, end_date=end_date),
        "tickets_per_day": crud.get_tickets_per_day(db, start_date=start_date, end_date=end_date),
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now(),
        "generated_by_name": current_user.full_name,
    }
    pdf_bytes = dashboard_reporte.generar_pdf(datos)
    filename = f"reporte-presupuesto_{start_date or 'historico'}_a_{end_date or 'actual'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
