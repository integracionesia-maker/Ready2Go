"""CRUD helper functions used by API routers."""

from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case, and_

from . import models, schemas
from .upload_manager import delete_upload


def _priority_rank(column):
    """CASE que ordena alta < media < baja (orden alfabético no sirve)."""
    return case(
        (column == models.BrandPriority.ALTA.value, 0),
        (column == models.BrandPriority.MEDIA.value, 1),
        (column == models.BrandPriority.BAJA.value, 2),
        else_=3,
    )


# ── Ciclos de presupuesto ────────────────────────────────────────────────────
# Implementación perezosa (doc/mejoras-diseno-fase1.md §1): un ciclo se crea la
# primera vez que se consulta o se necesita para asignar un ticket, nunca por cron.

def _week_bounds(d: date) -> tuple:
    start = d - timedelta(days=d.weekday())  # lunes
    return start, start + timedelta(days=6)  # domingo


def _month_bounds(d: date) -> tuple:
    start = d.replace(day=1)
    next_month = (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )
    return start, next_month - timedelta(days=1)


def _period_bounds(period_type: str, d: date) -> tuple:
    if period_type == models.CyclePeriod.SEMANAL.value:
        return _week_bounds(d)
    return _month_bounds(d)


def get_or_create_cycle_for_date(
    db: Session, creator: models.Creator, target_date: date
) -> models.BudgetCycle:
    existing = (
        db.query(models.BudgetCycle)
        .filter(
            models.BudgetCycle.creator_id == creator.id,
            models.BudgetCycle.start_date <= target_date,
            models.BudgetCycle.end_date >= target_date,
        )
        .first()
    )
    if existing:
        return existing

    period_type = creator.cycle_period or models.CyclePeriod.MENSUAL.value
    amount = creator.cycle_budget_amount or 0.0

    last_cycle = (
        db.query(models.BudgetCycle)
        .filter(models.BudgetCycle.creator_id == creator.id)
        .order_by(models.BudgetCycle.end_date.desc())
        .first()
    )

    cursor = last_cycle.end_date + timedelta(days=1) if last_cycle else target_date

    created = None
    while True:
        start, end = _period_bounds(period_type, cursor)
        created = models.BudgetCycle(
            creator_id=creator.id,
            period_type=period_type,
            amount=amount,
            spent=0.0,
            start_date=start,
            end_date=end,
        )
        db.add(created)
        db.flush()
        if end >= target_date:
            break
        cursor = end + timedelta(days=1)

    db.commit()
    db.refresh(created)
    return created


def list_cycles_for_creator(db: Session, creator_id: int) -> List[models.BudgetCycle]:
    return (
        db.query(models.BudgetCycle)
        .filter(models.BudgetCycle.creator_id == creator_id)
        .order_by(models.BudgetCycle.start_date.desc())
        .all()
    )


def cycle_to_response(cycle: models.BudgetCycle) -> schemas.BudgetCycleResponse:
    return schemas.BudgetCycleResponse(
        id=cycle.id,
        creator_id=cycle.creator_id,
        period_type=cycle.period_type,
        amount=cycle.amount,
        spent=cycle.spent,
        remaining=cycle.amount - cycle.spent,
        start_date=cycle.start_date,
        end_date=cycle.end_date,
        created_at=cycle.created_at,
    )


# ── Creators ─────────────────────────────────────────────────────────────────

def get_creators(db: Session, active_only: bool = False) -> List[models.Creator]:
    q = db.query(models.Creator)
    if active_only:
        q = q.filter(models.Creator.is_active == True)
    return q.order_by(models.Creator.name).all()


def get_creator(db: Session, creator_id: int) -> Optional[models.Creator]:
    return db.query(models.Creator).filter(models.Creator.id == creator_id).first()


def create_creator(db: Session, data: schemas.CreatorCreate) -> models.Creator:
    creator = models.Creator(
        name=data.name,
        initial_budget=data.initial_budget,
        remaining_budget=data.initial_budget,
        cycle_budget_amount=data.cycle_budget_amount,
        cycle_period=data.cycle_period,
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return creator


def update_creator(
    db: Session, creator: models.Creator, data: schemas.CreatorUpdate
) -> models.Creator:
    update_data = data.model_dump(exclude_unset=True)
    if "initial_budget" in update_data:
        delta = update_data["initial_budget"] - creator.initial_budget
        creator.remaining_budget += delta
    for field, value in update_data.items():
        setattr(creator, field, value)
    db.commit()
    db.refresh(creator)
    return creator


def creator_to_response(db: Session, creator: models.Creator) -> schemas.CreatorResponse:
    cycle = get_or_create_cycle_for_date(db, creator, date.today())
    return schemas.CreatorResponse(
        id=creator.id,
        name=creator.name,
        initial_budget=creator.initial_budget,
        spent_budget=creator.spent_budget,
        remaining_budget=creator.remaining_budget,
        is_active=creator.is_active,
        created_at=creator.created_at,
        cycle_period=cycle.period_type,
        cycle_amount=cycle.amount,
        cycle_spent=cycle.spent,
        cycle_remaining=cycle.amount - cycle.spent,
        cycle_start_date=cycle.start_date,
        cycle_end_date=cycle.end_date,
    )


def get_creators_kpi(db: Session) -> schemas.CreatorKpiResponse:
    active = (
        db.query(models.Creator)
        .filter(models.Creator.is_active == True)
        .all()
    )
    total_budget = 0.0
    total_spent = 0.0
    for creator in active:
        cycle = get_or_create_cycle_for_date(db, creator, date.today())
        total_budget += cycle.amount
        total_spent += cycle.spent
    return schemas.CreatorKpiResponse(
        total_budget=total_budget,
        total_spent=total_spent,
        total_remaining=total_budget - total_spent,
        active_creators=len(active),
    )


# ── Brands ───────────────────────────────────────────────────────────────────

def get_brands(db: Session, active_only: bool = False) -> List[models.Brand]:
    q = db.query(models.Brand)
    if active_only:
        q = q.filter(models.Brand.is_active == True)
    return q.order_by(_priority_rank(models.Brand.priority), models.Brand.name).all()


def get_brand(db: Session, brand_id: int) -> Optional[models.Brand]:
    return db.query(models.Brand).filter(models.Brand.id == brand_id).first()


def create_brand(db: Session, data: schemas.BrandCreate) -> models.Brand:
    brand = models.Brand(name=data.name, priority=data.priority)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def update_brand(
    db: Session, brand: models.Brand, data: schemas.BrandUpdate
) -> models.Brand:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    return brand


# ── Tickets ──────────────────────────────────────────────────────────────────

def get_tickets(
    db: Session,
    creator_name: Optional[str] = None,
    brand_name: Optional[str] = None,
    status: Optional[str] = None,
    creator_id: Optional[int] = None,
    uploaded_by_user_id: Optional[int] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[models.Ticket]:
    q = db.query(models.Ticket).filter(models.Ticket.is_deleted == False)
    if creator_name:
        q = q.join(models.Creator).filter(models.Creator.name.ilike(f"%{creator_name}%"))
    if brand_name:
        q = q.join(models.Brand).filter(models.Brand.name.ilike(f"%{brand_name}%"))
    if status:
        q = q.filter(models.Ticket.status == status)
    if creator_id is not None:
        q = q.filter(models.Ticket.creator_id == creator_id)
    if uploaded_by_user_id is not None:
        q = q.filter(models.Ticket.uploaded_by_user_id == uploaded_by_user_id)
    q = q.order_by(models.Ticket.upload_date.desc())
    if limit is not None:
        q = q.offset(offset).limit(limit)
    return q.all()


def get_ticket(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    return db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()


def create_ticket(
    db: Session,
    *,
    creator: models.Creator,
    brand: models.Brand,
    amount: float,
    file_name: str,
    file_path: str,
    mime_type: str,
    notes: Optional[str],
    status: str,
    actor_user_id: int,
) -> models.Ticket:
    """Crea un ticket asignado a su ciclo (por fecha de subida, hoy). Si nace
    `aprobado` (tickets de admin/superadmin, R10) descuenta de inmediato del
    ciclo — sin validar fondos: los ciclos pueden quedar en negativo a propósito
    (decisión del usuario, doc/mejoras-diseno-fase1.md §0.B)."""
    cycle = get_or_create_cycle_for_date(db, creator, date.today())

    ticket = models.Ticket(
        creator_id=creator.id,
        brand_id=brand.id,
        budget_cycle_id=cycle.id,
        amount=amount,
        file_name=file_name,
        file_path=file_path,
        mime_type=mime_type,
        notes=notes,
        status=status,
        uploaded_by_user_id=actor_user_id,
    )

    if status == models.TicketStatus.APROBADO.value:
        cycle.spent += amount
        ticket.reviewed_by_user_id = actor_user_id
        ticket.reviewed_at = datetime.now(timezone.utc)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def approve_ticket(db: Session, ticket: models.Ticket, actor_user_id: int) -> models.Ticket:
    """Aprueba un ticket pendiente: descuenta incondicionalmente del ciclo
    asignado (puede quedar en negativo, decisión del usuario)."""
    cycle = ticket.budget_cycle
    if cycle is None:
        cycle = get_or_create_cycle_for_date(db, ticket.creator, date.today())
        ticket.budget_cycle_id = cycle.id

    cycle.spent += ticket.amount
    ticket.status = models.TicketStatus.APROBADO.value
    ticket.reviewed_by_user_id = actor_user_id
    ticket.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket


def reject_ticket(
    db: Session, ticket: models.Ticket, reason: str, actor_user_id: int
) -> models.Ticket:
    ticket.status = models.TicketStatus.RECHAZADO.value
    ticket.rejection_reason = reason
    ticket.reviewed_by_user_id = actor_user_id
    ticket.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket


def _revert_cycle_if_approved(ticket: models.Ticket) -> None:
    """Si el ticket estaba aprobado, revierte su monto del ciclo asignado sin
    dejarlo nunca negativo (R12). Pendiente/rechazado nunca descontaron: no-op."""
    if ticket.status == models.TicketStatus.APROBADO.value and ticket.budget_cycle is not None:
        cycle = ticket.budget_cycle
        cycle.spent = max(0.0, cycle.spent - ticket.amount)


def soft_delete_ticket(db: Session, ticket: models.Ticket, actor_user_id: int) -> models.Ticket:
    """Marca un ticket como eliminado lógicamente. No borra el archivo del disco."""
    _revert_cycle_if_approved(ticket)
    ticket.is_deleted = True
    ticket.deleted_at = datetime.now(timezone.utc)
    ticket.deleted_by_user_id = actor_user_id
    db.commit()
    db.refresh(ticket)
    return ticket


def hard_delete_ticket(db: Session, ticket: models.Ticket) -> None:
    """Borra el registro de la BD y el archivo del disco. Si el ticket ya
    estaba soft-deleted, el ciclo ya se revirtió antes — no revertir de nuevo."""
    if not ticket.is_deleted:
        _revert_cycle_if_approved(ticket)
    file_path = ticket.file_path
    db.delete(ticket)
    db.commit()
    delete_upload(file_path)


def get_brand_spend_breakdown(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[schemas.BrandSpendItem]:
    # Solo cuentan tickets aprobados (R10); el filtro va en el ON del join (no en
    # el WHERE) para que las marcas sin gasto en el rango sigan apareciendo con $0.
    join_conditions = [
        models.Brand.id == models.Ticket.brand_id,
        models.Ticket.status == models.TicketStatus.APROBADO.value,
        models.Ticket.is_deleted == False,
    ]
    if start_date:
        join_conditions.append(models.Ticket.upload_date >= start_date)
    if end_date:
        join_conditions.append(models.Ticket.upload_date < end_date + timedelta(days=1))

    q = db.query(
        models.Brand.name.label("brand_name"),
        models.Brand.priority.label("priority"),
        func.coalesce(func.sum(models.Ticket.amount), 0.0).label("total_spent"),
    ).outerjoin(models.Ticket, and_(*join_conditions))

    rows = (
        q.group_by(models.Brand.id, models.Brand.name, models.Brand.priority)
        .order_by(func.sum(models.Ticket.amount).desc())
        .all()
    )
    return [
        schemas.BrandSpendItem(brand_name=r.brand_name, total_spent=float(r.total_spent), priority=r.priority)
        for r in rows
    ]


# ── Dashboard ──────────────────────────────────────────────────────────────────


def get_monthly_spend(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[schemas.MonthlySpendItem]:
    def _por_mes(status: str):
        q = db.query(
            func.strftime("%Y-%m", models.Ticket.upload_date).label("month"),
            func.coalesce(func.sum(models.Ticket.amount), 0.0).label("total"),
            func.count(models.Ticket.id).label("count"),
        ).filter(
            models.Ticket.status == status,
            models.Ticket.is_deleted == False,
        )
        if start_date:
            q = q.filter(models.Ticket.upload_date >= start_date)
        if end_date:
            q = q.filter(models.Ticket.upload_date < end_date + timedelta(days=1))
        return {r.month: (float(r.total), r.count) for r in q.group_by("month").all()}

    aprobados = _por_mes(models.TicketStatus.APROBADO.value)
    # Pendientes: informativo (R7 — nunca cuentan contra el ciclo). Un mes con
    # SOLO tickets pendientes (ej. el mes en curso, sin nada revisado todavia)
    # debe aparecer igual, por eso se unen las llaves de ambos diccionarios.
    pendientes = _por_mes(models.TicketStatus.PENDIENTE.value)

    meses = sorted(set(aprobados) | set(pendientes))
    resultado = []
    for mes in meses:
        total, count = aprobados.get(mes, (0.0, 0))
        pending_total, pending_count = pendientes.get(mes, (0.0, 0))
        resultado.append(
            schemas.MonthlySpendItem(
                month=mes, total=total, count=count,
                pending_total=pending_total, pending_count=pending_count,
            )
        )
    return resultado


def get_tickets_per_day(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[schemas.TicketsPerDayItem]:
    """Cuantos tickets se SUBIERON cada dia — metrica de actividad/uso, no de
    gasto aprobado: cuenta todos los estados (pendiente/aprobado/rechazado),
    a diferencia de `get_monthly_spend`. Solo excluye borrados."""
    q = db.query(
        func.strftime("%Y-%m-%d", models.Ticket.upload_date).label("day"),
        func.count(models.Ticket.id).label("count"),
    ).filter(models.Ticket.is_deleted == False)
    if start_date:
        q = q.filter(models.Ticket.upload_date >= start_date)
    if end_date:
        q = q.filter(models.Ticket.upload_date < end_date + timedelta(days=1))
    rows = q.group_by("day").order_by("day").all()
    return [schemas.TicketsPerDayItem(day=r.day, count=r.count) for r in rows]


def _peek_cycle_budget(db: Session, creator: models.Creator, target_date: date) -> float:
    """Version de solo lectura de `get_or_create_cycle_for_date`: para el
    dashboard (GET) no tiene sentido materializar un ciclo -- y menos un
    commit por creador dentro de un loop en un endpoint de solo lectura. Si
    no hay ciclo vigente, el monto es el mismo que se usaria para crear uno."""
    existing = (
        db.query(models.BudgetCycle)
        .filter(
            models.BudgetCycle.creator_id == creator.id,
            models.BudgetCycle.start_date <= target_date,
            models.BudgetCycle.end_date >= target_date,
        )
        .first()
    )
    if existing:
        return existing.amount
    return creator.cycle_budget_amount or 0.0


def get_creator_usage(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[schemas.CreatorUsageItem]:
    """El denominador ('initial_budget' del schema) ahora es el monto del ciclo
    vigente de cada creador (R7), no un presupuesto histórico acumulado."""
    def _por_creador(status: str):
        q = db.query(
            models.Ticket.creator_id,
            func.coalesce(func.sum(models.Ticket.amount), 0.0).label("total"),
            func.count(models.Ticket.id).label("count"),
        ).filter(
            models.Ticket.status == status,
            models.Ticket.is_deleted == False,
        )
        if start_date:
            q = q.filter(models.Ticket.upload_date >= start_date)
        if end_date:
            q = q.filter(models.Ticket.upload_date < end_date + timedelta(days=1))
        return q.group_by(models.Ticket.creator_id).subquery()

    ticket_spent = _por_creador(models.TicketStatus.APROBADO.value)
    ticket_pending = _por_creador(models.TicketStatus.PENDIENTE.value)

    rows = (
        db.query(
            models.Creator,
            func.coalesce(ticket_spent.c.total, 0.0).label("spent"),
            func.coalesce(ticket_pending.c.total, 0.0).label("pending"),
            func.coalesce(ticket_pending.c.count, 0).label("pending_count"),
        )
        .outerjoin(ticket_spent, models.Creator.id == ticket_spent.c.creator_id)
        .outerjoin(ticket_pending, models.Creator.id == ticket_pending.c.creator_id)
        .filter(models.Creator.is_active == True)
        .all()
    )

    items = []
    for creator, spent, pending, pending_count in rows:
        budget = _peek_cycle_budget(db, creator, date.today())
        items.append(
            schemas.CreatorUsageItem(
                creator_id=creator.id,
                name=creator.name,
                spent=float(spent),
                initial_budget=float(budget),
                percentage=round((float(spent) / budget) * 100, 1) if budget > 0 else 0.0,
                # Informativo (R7): nunca entra al calculo de `percentage`.
                pending=float(pending),
                pending_count=pending_count,
            )
        )
    items.sort(key=lambda i: i.spent, reverse=True)
    return items


def get_dashboard_summary(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> schemas.DashboardSummary:
    q = db.query(
        func.coalesce(func.sum(models.Ticket.amount), 0.0),
        func.count(models.Ticket.id),
    ).filter(
        models.Ticket.status == models.TicketStatus.APROBADO.value,
        models.Ticket.is_deleted == False,
    )
    if start_date:
        q = q.filter(models.Ticket.upload_date >= start_date)
    if end_date:
        q = q.filter(models.Ticket.upload_date < end_date + timedelta(days=1))
    total_spent, ticket_count = q.first()

    qp = db.query(
        func.coalesce(func.sum(models.Ticket.amount), 0.0),
        func.count(models.Ticket.id),
    ).filter(
        models.Ticket.status == models.TicketStatus.PENDIENTE.value,
        models.Ticket.is_deleted == False,
    )
    if start_date:
        qp = qp.filter(models.Ticket.upload_date >= start_date)
    if end_date:
        qp = qp.filter(models.Ticket.upload_date < end_date + timedelta(days=1))
    pending_total, pending_count = qp.first()

    active_brands = (
        db.query(func.count(func.distinct(models.Brand.id)))
        .filter(models.Brand.is_active == True)
        .join(models.Ticket, models.Brand.id == models.Ticket.brand_id)
        .filter(
            models.Ticket.status == models.TicketStatus.APROBADO.value,
            models.Ticket.is_deleted == False,
        )
    )
    if start_date:
        active_brands = active_brands.filter(models.Ticket.upload_date >= start_date)
    if end_date:
        active_brands = active_brands.filter(models.Ticket.upload_date < end_date + timedelta(days=1))
    active_brands = active_brands.scalar() or 0

    avg_ticket = float(total_spent) / ticket_count if ticket_count > 0 else 0.0

    return schemas.DashboardSummary(
        total_spent=float(total_spent),
        ticket_count=ticket_count,
        avg_ticket=round(avg_ticket, 2),
        active_brands=active_brands,
        # Informativo (R7): nunca se suma a `total_spent`.
        pending_total=float(pending_total),
        pending_count=pending_count,
    )


# ── Gastos generales (R12) ──────────────────────────────────────────────────
# Independientes de creadores/marcas/ciclos: no pasan por validación, se crean
# y cuentan de inmediato. Ver doc/gastos-generales-manual.md.

def create_general_expense(
    db: Session,
    *,
    brand: models.Brand,
    amount: float,
    description: str,
    file_name: str,
    file_path: str,
    mime_type: str,
    actor_user_id: int,
) -> models.GeneralExpense:
    expense = models.GeneralExpense(
        brand_id=brand.id,
        amount=amount,
        description=description,
        file_name=file_name,
        file_path=file_path,
        mime_type=mime_type,
        created_by_user_id=actor_user_id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def get_general_expenses(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[models.GeneralExpense]:
    q = db.query(models.GeneralExpense).filter(models.GeneralExpense.is_deleted == False)
    if start_date:
        q = q.filter(models.GeneralExpense.upload_date >= start_date)
    if end_date:
        q = q.filter(models.GeneralExpense.upload_date < end_date + timedelta(days=1))
    return q.order_by(models.GeneralExpense.upload_date.desc()).all()


def get_top_expenses(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[schemas.TopExpenseItem]:
    """Top 3 gastos INDIVIDUALES del período mezclando gastos generales y
    operativos (sin sumatorias por marca/rubro). Cada tabla se filtra por su
    campo de fecha semántico: generales por `upload_date`, operativos por
    `fecha_gasto` (nunca al revés). `limit(3)` por tabla es correcto: el top-3
    global siempre está contenido en la unión de los top-3 de cada tabla."""
    generales = db.query(models.GeneralExpense).filter(
        models.GeneralExpense.is_deleted == False
    )
    if start_date:
        generales = generales.filter(models.GeneralExpense.upload_date >= start_date)
    if end_date:
        generales = generales.filter(models.GeneralExpense.upload_date < end_date + timedelta(days=1))
    generales = generales.order_by(models.GeneralExpense.amount.desc()).limit(3).all()

    operativos = db.query(models.OperationalExpense).filter(
        models.OperationalExpense.is_deleted == False
    )
    if start_date:
        operativos = operativos.filter(models.OperationalExpense.fecha_gasto >= start_date)
    if end_date:
        operativos = operativos.filter(models.OperationalExpense.fecha_gasto < end_date + timedelta(days=1))
    operativos = operativos.order_by(models.OperationalExpense.amount.desc()).limit(3).all()

    items = [
        schemas.TopExpenseItem(
            tipo="general",
            id=g.id,
            descripcion=g.description,
            monto=float(g.amount),
            fecha=g.upload_date.date(),
            etiqueta=g.brand.name if g.brand else f"ID {g.brand_id}",
        )
        for g in generales
    ] + [
        schemas.TopExpenseItem(
            tipo="operativo",
            id=o.id,
            descripcion=o.description,
            monto=float(o.amount),
            fecha=o.fecha_gasto,
            etiqueta=o.rubro.nombre if o.rubro else f"ID {o.rubro_id}",
        )
        for o in operativos
    ]
    # Solo por monto: comparar date (fecha_gasto) con datetime (upload_date) en
    # la clave lanzaría TypeError. El sort es estable: los empates quedan
    # deterministas (generales primero, en el orden amount.desc() de SQL).
    items.sort(key=lambda i: i.monto, reverse=True)
    return items[:3]


def get_general_expense(db: Session, expense_id: int) -> Optional[models.GeneralExpense]:
    return db.query(models.GeneralExpense).filter(models.GeneralExpense.id == expense_id).first()


def soft_delete_general_expense(
    db: Session, expense: models.GeneralExpense, actor_user_id: int
) -> models.GeneralExpense:
    expense.is_deleted = True
    expense.deleted_at = datetime.now(timezone.utc)
    expense.deleted_by_user_id = actor_user_id
    db.commit()
    db.refresh(expense)
    return expense


def hard_delete_general_expense(db: Session, expense: models.GeneralExpense) -> None:
    file_path = expense.file_path
    db.delete(expense)
    db.commit()
    delete_upload(file_path)


def get_general_expenses_monthly(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[schemas.GeneralExpenseMonthlyItem]:
    q = db.query(
        func.strftime("%Y-%m", models.GeneralExpense.upload_date).label("month"),
        func.coalesce(func.sum(models.GeneralExpense.amount), 0.0).label("total"),
        func.count(models.GeneralExpense.id).label("count"),
    ).filter(models.GeneralExpense.is_deleted == False)
    if start_date:
        q = q.filter(models.GeneralExpense.upload_date >= start_date)
    if end_date:
        q = q.filter(models.GeneralExpense.upload_date < end_date + timedelta(days=1))
    rows = q.group_by("month").order_by("month").all()
    return [
        schemas.GeneralExpenseMonthlyItem(month=r.month, total=float(r.total), count=r.count)
        for r in rows
    ]


def get_general_expenses_for_export(db: Session, months: List[str]) -> List[models.GeneralExpense]:
    """`months`: lista de 'YYYY-MM'. Sin meses, no retorna nada (el export
    siempre exige una selección explícita)."""
    if not months:
        return []
    q = db.query(models.GeneralExpense).filter(
        models.GeneralExpense.is_deleted == False,
        func.strftime("%Y-%m", models.GeneralExpense.upload_date).in_(months),
    )
    return q.order_by(models.GeneralExpense.upload_date.desc()).all()


# ── Usuarios ─────────────────────────────────────────────────────────────────

MAX_FAILED_LOGIN_ATTEMPTS = 5
BASE_LOCK_MINUTES = 5
MAX_LOCK_MINUTES = 60


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_identifier(db: Session, identifier: str) -> Optional[models.User]:
    return get_user_by_username(db, identifier) or get_user_by_email(db, identifier)


def list_users(
    db: Session,
    *,
    role: Optional[str] = None,
    exclude_role: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "username",
    sort_dir: str = "asc",
) -> tuple[list, int]:
    q = db.query(models.User)
    if role:
        q = q.filter(models.User.role == role)
    if exclude_role:
        # ANTES del count(): el total de paginación debe respetar la exclusión
        # (la tabla principal de Usuarios excluye superadmins, 2026-08-19).
        q = q.filter(models.User.role != exclude_role)
    if is_active is not None:
        q = q.filter(models.User.is_active == is_active)
    if search:
        patron = f"%{search}%"
        q = q.filter(
            (models.User.username.like(patron))
            | (models.User.email.like(patron))
            | (models.User.full_name.like(patron))
        )
    total = q.count()

    columna = getattr(models.User, sort_by, models.User.username)
    columna = columna.desc() if sort_dir == "desc" else columna.asc()

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    filas = q.order_by(columna).offset((page - 1) * page_size).limit(page_size).all()
    return filas, total


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password_hash: str,
    full_name: str,
    role: str,
    creator_id: Optional[int] = None,
    must_change_password: bool = True,
) -> models.User:
    user = models.User(
        username=username,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=role,
        creator_id=creator_id,
        must_change_password=must_change_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session, user: models.User, full_name: Optional[str], email: Optional[str]
) -> models.User:
    if full_name is not None:
        user.full_name = full_name
    if email is not None:
        user.email = email
    db.commit()
    db.refresh(user)
    return user


def update_user_admin(db: Session, user: models.User, update_data: dict) -> models.User:
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def set_user_password(
    db: Session, user: models.User, password_hash: str, must_change_password: bool
) -> models.User:
    user.password_hash = password_hash
    user.must_change_password = must_change_password
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, user: models.User, is_active: bool) -> models.User:
    user.is_active = is_active
    if not is_active:
        user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def is_locked(user: models.User) -> bool:
    # Naive UTC: SQLite devuelve locked_until sin tzinfo; ambos lados deben coincidir.
    return user.locked_until is not None and user.locked_until > datetime.now(timezone.utc).replace(tzinfo=None)


def register_failed_login(db: Session, user: models.User) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        extra = user.failed_login_attempts - MAX_FAILED_LOGIN_ATTEMPTS
        lock_minutes = min(BASE_LOCK_MINUTES * (2 ** extra), MAX_LOCK_MINUTES)
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=lock_minutes)
    db.commit()


def register_successful_login(db: Session, user: models.User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    db.commit()


# ── Refresh tokens ───────────────────────────────────────────────────────────

def create_refresh_token_record(
    db: Session, user_id: int, token_hash: str, expires_at: datetime
) -> models.RefreshToken:
    rt = models.RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def get_refresh_token_by_hash(db: Session, token_hash: str) -> Optional[models.RefreshToken]:
    return (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash)
        .first()
    )


def rotate_refresh_token(
    db: Session, old_token: models.RefreshToken, new_token_hash: str, new_expires_at: datetime
) -> models.RefreshToken:
    new_rt = models.RefreshToken(
        user_id=old_token.user_id, token_hash=new_token_hash, expires_at=new_expires_at
    )
    db.add(new_rt)
    db.flush()
    old_token.revoked_at = datetime.now(timezone.utc)
    old_token.replaced_by_id = new_rt.id
    db.commit()
    db.refresh(new_rt)
    return new_rt


def revoke_refresh_token(db: Session, token: models.RefreshToken) -> None:
    token.revoked_at = datetime.now(timezone.utc)
    db.commit()


def revoke_all_refresh_tokens_for_user(db: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.revoked_at.is_(None),
        )
        .update({"revoked_at": now}, synchronize_session=False)
    )
    db.commit()


# ── Auditoría ────────────────────────────────────────────────────────────────

def log_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    http_method: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    request_params: Optional[str] = None,
    request_body_summary: Optional[str] = None,
    response_status: Optional[int] = None,
    user_agent: Optional[str] = None,
    duration_ms: Optional[int] = None,
    standard_fields: Optional[str] = None,
) -> None:
    entry = models.AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
        http_method=http_method,
        endpoint_path=endpoint_path,
        request_params=request_params,
        request_body_summary=request_body_summary,
        response_status=response_status,
        user_agent=user_agent,
        duration_ms=duration_ms,
        standard_fields=standard_fields,
    )
    db.add(entry)
    db.commit()
