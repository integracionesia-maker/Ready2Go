"""CRUD del modulo Gastos Operativos.

Todo el bucketing por fecha usa `fecha_gasto` (la manual), nunca `upload_date`.
Toda query de gastos filtra `is_deleted == False` sin excepcion.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas_operativos as schemas


# ── Rubros ───────────────────────────────────────────────────────────────────


def list_rubros(db: Session, active_only: bool = False) -> List[models.ExpenseRubro]:
    q = db.query(models.ExpenseRubro)
    if active_only:
        q = q.filter(models.ExpenseRubro.is_active == True)  # noqa: E712
    return q.order_by(models.ExpenseRubro.nombre).all()


def get_rubro(db: Session, rubro_id: int) -> Optional[models.ExpenseRubro]:
    return db.query(models.ExpenseRubro).filter(models.ExpenseRubro.id == rubro_id).first()


def get_rubro_by_nombre(db: Session, nombre: str) -> Optional[models.ExpenseRubro]:
    return db.query(models.ExpenseRubro).filter(models.ExpenseRubro.nombre == nombre).first()


def create_rubro(db: Session, *, nombre: str) -> models.ExpenseRubro:
    rubro = models.ExpenseRubro(nombre=nombre, is_active=True)
    db.add(rubro)
    db.commit()
    db.refresh(rubro)
    return rubro


def update_rubro(
    db: Session,
    rubro: models.ExpenseRubro,
    *,
    nombre: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> models.ExpenseRubro:
    if nombre is not None:
        rubro.nombre = nombre
    if is_active is not None:
        rubro.is_active = is_active
    db.commit()
    db.refresh(rubro)
    return rubro


# ── Gastos ───────────────────────────────────────────────────────────────────


def create_expense(
    db: Session,
    *,
    rubro: models.ExpenseRubro,
    amount: float,
    description: str,
    fecha_gasto: date,
    file_name: str,
    file_path: str,
    mime_type: str,
    actor_user_id: int,
) -> models.OperationalExpense:
    expense = models.OperationalExpense(
        rubro_id=rubro.id,
        amount=amount,
        description=description,
        fecha_gasto=fecha_gasto,
        file_name=file_name,
        file_path=file_path,
        mime_type=mime_type,
        created_by_user_id=actor_user_id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def _rango(q, columna, start_date: Optional[date], end_date: Optional[date]):
    if start_date:
        q = q.filter(columna >= start_date)
    if end_date:
        # end_date inclusivo; columna es Date, se compara con < end+1 por simetria
        # con el resto del proyecto (donde la columna a veces es DateTime).
        q = q.filter(columna < end_date + timedelta(days=1))
    return q


def list_expenses(
    db: Session,
    *,
    rubro_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[models.OperationalExpense]:
    q = db.query(models.OperationalExpense).filter(
        models.OperationalExpense.is_deleted == False  # noqa: E712
    )
    if rubro_id is not None:
        q = q.filter(models.OperationalExpense.rubro_id == rubro_id)
    q = _rango(q, models.OperationalExpense.fecha_gasto, start_date, end_date)
    return q.order_by(
        models.OperationalExpense.fecha_gasto.desc(), models.OperationalExpense.id.desc()
    ).all()


def get_expense(db: Session, expense_id: int) -> Optional[models.OperationalExpense]:
    return (
        db.query(models.OperationalExpense)
        .filter(models.OperationalExpense.id == expense_id)
        .first()
    )


def soft_delete_expense(
    db: Session, expense: models.OperationalExpense, actor_user_id: int
) -> models.OperationalExpense:
    expense.is_deleted = True
    expense.deleted_at = datetime.now(timezone.utc)
    expense.deleted_by_user_id = actor_user_id
    db.commit()
    db.refresh(expense)
    return expense


# ── Dashboard / export ───────────────────────────────────────────────────────


def dashboard(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> schemas.OperationalDashboardResponse:
    base = db.query(models.OperationalExpense).filter(
        models.OperationalExpense.is_deleted == False  # noqa: E712
    )
    base = _rango(base, models.OperationalExpense.fecha_gasto, start_date, end_date)
    sub = base.subquery()

    total = db.query(func.coalesce(func.sum(sub.c.amount), 0.0)).scalar() or 0.0
    count = db.query(func.count(sub.c.id)).scalar() or 0

    por_rubro_q = (
        db.query(
            models.ExpenseRubro.id.label("rubro_id"),
            models.ExpenseRubro.nombre.label("rubro_nombre"),
            func.coalesce(func.sum(sub.c.amount), 0.0).label("total"),
            func.count(sub.c.id).label("count"),
        )
        .join(sub, sub.c.rubro_id == models.ExpenseRubro.id)
        .group_by(models.ExpenseRubro.id, models.ExpenseRubro.nombre)
        .order_by(func.sum(sub.c.amount).desc())
    )
    por_rubro = [
        schemas.RubroTotalItem(
            rubro_id=r.rubro_id, rubro_nombre=r.rubro_nombre, total=float(r.total), count=r.count
        )
        for r in por_rubro_q.all()
    ]

    mensual_q = (
        db.query(
            func.strftime("%Y-%m", sub.c.fecha_gasto).label("month"),
            func.coalesce(func.sum(sub.c.amount), 0.0).label("total"),
            func.count(sub.c.id).label("count"),
        )
        .group_by("month")
        .order_by("month")
    )
    mensual = [
        schemas.OperationalMonthlyItem(month=r.month, total=float(r.total), count=r.count)
        for r in mensual_q.all()
    ]

    return schemas.OperationalDashboardResponse(
        total=float(total), count=int(count), por_rubro=por_rubro, mensual=mensual
    )


def for_export(db: Session, months: List[str]) -> List[models.OperationalExpense]:
    """`months`: lista de 'YYYY-MM' (por `fecha_gasto`). Sin meses no retorna
    nada: el export siempre exige seleccion explicita."""
    if not months:
        return []
    q = db.query(models.OperationalExpense).filter(
        models.OperationalExpense.is_deleted == False,  # noqa: E712
        func.strftime("%Y-%m", models.OperationalExpense.fecha_gasto).in_(months),
    )
    return q.order_by(models.OperationalExpense.fecha_gasto.desc()).all()
