"""Dashboard analytics endpoints with date-range filtering."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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


@router.get("/top-expenses", response_model=List[schemas.TopExpenseItem])
def top_expenses(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_top_expenses(db, start_date=start_date, end_date=end_date)


@router.get("/monthly-estimates", response_model=List[schemas.MonthlyEstimateItem])
def monthly_estimates(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_monthly_estimates(db, year=year)


@router.put("/monthly-estimates/{year}/{month}/{categoria}", response_model=schemas.MonthlyEstimateItem)
def update_monthly_estimate(
    year: int,
    month: int,
    categoria: str,
    data: schemas.MonthlyEstimateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12.")
    if categoria not in crud.CATEGORIAS_ESTIMATE:
        raise HTTPException(status_code=400, detail="Categoría inválida (usa 'caja_grande' o 'caja_chica').")
    if not crud.mes_es_editable(year, month):
        raise HTTPException(
            status_code=409,
            detail="La estimación de un mes ya iniciado (o pasado) no se puede editar.",
        )
    crud.upsert_monthly_estimate(
        db, year=year, month=month, categoria=categoria, amount=data.amount, actor_user_id=current_user.id
    )
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="monthly_estimate.set",
        target_type="monthly_spend_estimate",
        details=f"year={year} month={month} categoria={categoria} amount={data.amount}",
    )
    return [
        e for e in crud.get_monthly_estimates(db, year=year) if e.month == month and e.categoria == categoria
    ][0]


def _period_comparison_item(
    db: Session, start_date: Optional[date], end_date: Optional[date]
) -> schemas.PeriodComparisonItem:
    """Arma un `PeriodComparisonItem` reutilizando las funciones CRUD que ya
    existen (mismo dato que ya ve la pantalla) con el rango pedido — sin
    agregación nueva."""
    summary = crud.get_dashboard_summary(db, start_date=start_date, end_date=end_date)
    general_total = sum(m.total for m in crud.get_general_expenses_monthly(db, start_date=start_date, end_date=end_date))
    operational_total = crud_operativos.dashboard(db, start_date=start_date, end_date=end_date).total
    return schemas.PeriodComparisonItem(
        total_spent=summary.total_spent,
        general_expenses_total=general_total,
        operational_expenses_total=operational_total,
        ticket_count=summary.ticket_count,
    )


_LABEL_COMPARACION = {"mes": "el mes pasado", "anio": "el año pasado"}


def _build_period_comparison(
    db: Session, start_date: Optional[date], end_date: Optional[date]
) -> schemas.PeriodComparisonResponse:
    actual = _period_comparison_item(db, start_date, end_date)
    deteccion = crud.detectar_periodo_unico(start_date, end_date)
    if deteccion is None:
        return schemas.PeriodComparisonResponse(is_single_period=False, actual=actual)
    tipo, cmp_start, cmp_end = deteccion
    anterior = _period_comparison_item(db, cmp_start, cmp_end)
    return schemas.PeriodComparisonResponse(
        is_single_period=True,
        tipo=tipo,
        label_comparacion=_LABEL_COMPARACION[tipo],
        actual=actual,
        anterior=anterior,
    )


@router.get("/period-comparison", response_model=schemas.PeriodComparisonResponse)
def period_comparison(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return _build_period_comparison(db, start_date, end_date)


@router.get("/general-expenses-by-brand", response_model=List[schemas.BrandSpendItem])
def general_expenses_by_brand(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_general_expenses_by_brand(db, start_date=start_date, end_date=end_date)


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
    period_comparison_data = _build_period_comparison(db, start_date, end_date)
    datos = {
        "kpi": crud.get_creators_kpi(db),
        "summary": crud.get_dashboard_summary(db, start_date=start_date, end_date=end_date),
        "monthly": crud.get_monthly_spend(db, start_date=start_date, end_date=end_date),
        "creator_usage": crud.get_creator_usage(db, start_date=start_date, end_date=end_date),
        "brand_spend": crud.get_brand_spend_breakdown(db, start_date=start_date, end_date=end_date),
        "general_expenses_monthly": crud.get_general_expenses_monthly(db, start_date=start_date, end_date=end_date),
        "operational_dashboard": crud_operativos.dashboard(db, start_date=start_date, end_date=end_date),
        "top_expenses": crud.get_top_expenses(db, start_date=start_date, end_date=end_date),
        "tickets_per_day": crud.get_tickets_per_day(db, start_date=start_date, end_date=end_date),
        "period_comparison": period_comparison_data,
        "general_expenses_by_brand": (
            crud.get_general_expenses_by_brand(db, start_date=start_date, end_date=end_date)
            if period_comparison_data.is_single_period
            else []
        ),
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
