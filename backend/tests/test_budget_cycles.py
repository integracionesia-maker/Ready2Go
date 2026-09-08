"""Lógica de ciclos de presupuesto (R7): apertura perezosa, límites de semana/mes,
relleno de huecos, y que cambiar la config no toca ciclos ya creados."""

from datetime import date, timedelta

from app import crud, models, schemas

from .conftest import make_creator, make_user


def test_monthly_cycle_bounds(db):
    creator = make_creator(db, name="C1", cycle_budget_amount=1000, cycle_period="mensual")
    cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    assert cycle.start_date == date(2026, 7, 1)
    assert cycle.end_date == date(2026, 7, 31)
    assert cycle.amount == 1000
    assert cycle.spent == 0


def test_monthly_cycle_bounds_february_leap_year(db):
    creator = make_creator(db, name="C2", cycle_budget_amount=1000, cycle_period="mensual")
    cycle = crud.get_or_create_cycle_for_date(db, creator, date(2028, 2, 10))  # 2028 es bisiesto
    assert cycle.start_date == date(2028, 2, 1)
    assert cycle.end_date == date(2028, 2, 29)


def test_weekly_cycle_bounds_monday_to_sunday(db):
    creator = make_creator(db, name="C3", cycle_budget_amount=500, cycle_period="semanal")
    # 16 de julio de 2026 es jueves
    cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    assert cycle.start_date == date(2026, 7, 13)  # lunes
    assert cycle.end_date == date(2026, 7, 19)  # domingo


def test_cycle_is_idempotent(db):
    creator = make_creator(db, name="C4", cycle_budget_amount=1000, cycle_period="mensual")
    cycle1 = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    cycle2 = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 20))
    assert cycle1.id == cycle2.id


def test_next_month_opens_a_new_cycle(db):
    creator = make_creator(db, name="C5", cycle_budget_amount=1000, cycle_period="mensual")
    july_cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    august_cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 8, 5))
    assert july_cycle.id != august_cycle.id
    assert august_cycle.start_date == date(2026, 8, 1)
    assert august_cycle.end_date == date(2026, 8, 31)


def test_gap_filling_creates_intermediate_cycles(db):
    """Si nadie consulta nada por 3 meses, al pedir el ciclo de octubre deben
    quedar materializados también los de agosto y septiembre (huecos rellenos)."""
    creator = make_creator(db, name="C6", cycle_budget_amount=1000, cycle_period="mensual")
    crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    crud.get_or_create_cycle_for_date(db, creator, date(2026, 10, 5))

    cycles = crud.list_cycles_for_creator(db, creator.id)
    months = sorted(c.start_date.month for c in cycles)
    assert months == [7, 8, 9, 10]


def test_changing_config_does_not_affect_existing_cycle(db):
    creator = make_creator(db, name="C7", cycle_budget_amount=1000, cycle_period="mensual")
    current = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    assert current.amount == 1000

    # El admin cambia el monto configurado — no debe tocar el ciclo ya creado.
    creator.cycle_budget_amount = 5000
    db.commit()

    same_cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 20))
    assert same_cycle.id == current.id
    assert same_cycle.amount == 1000  # sin cambios

    next_cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 8, 5))
    assert next_cycle.amount == 5000  # el nuevo monto sí aplica al ciclo futuro


def test_late_approval_charges_original_cycle_not_current(db, brand_a):
    """Un ticket se asigna a su ciclo por fecha de subida (R7/R10). Si se aprueba
    después de que ya abrió un ciclo nuevo, debe seguir descontando del ciclo
    ORIGINAL (el de cuando se subió), nunca del que esté vigente al aprobar."""
    creator = make_creator(db, name="C9", cycle_budget_amount=1000, cycle_period="mensual")
    approver = make_user(db, username="revisor2", password="ClaveValida123!", role="admin")

    # El ticket se sube y queda pendiente en julio (ciclo de julio ya materializado).
    july_cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))
    ticket = models.Ticket(
        creator_id=creator.id,
        brand_id=brand_a.id,
        budget_cycle_id=july_cycle.id,
        amount=300,
        file_name="f.pdf",
        file_path=__file__,
        mime_type="application/pdf",
        status="pendiente",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Pasa el tiempo: se materializa (y queda "vigente") el ciclo de agosto.
    august_cycle = crud.get_or_create_cycle_for_date(db, creator, date(2026, 8, 5))
    assert august_cycle.id != july_cycle.id

    # El admin aprueba el ticket recién en agosto — debe cargarse a julio, no a agosto.
    approved = crud.approve_ticket(db, ticket, actor_user_id=approver.id)
    assert approved.budget_cycle_id == july_cycle.id

    db.refresh(july_cycle)
    db.refresh(august_cycle)
    assert july_cycle.spent == 300
    assert august_cycle.spent == 0


def test_cycles_endpoint_lists_history_newest_first(logged_in_admin, db):
    creator = make_creator(db, name="C10", cycle_budget_amount=1000, cycle_period="mensual")
    crud.get_or_create_cycle_for_date(db, creator, date(2026, 5, 10))
    crud.get_or_create_cycle_for_date(db, creator, date(2026, 7, 16))  # rellena junio y julio también

    resp = logged_in_admin.get(f"/api/creators/{creator.id}/ciclos")
    assert resp.status_code == 200
    body = resp.json()
    months = [c["start_date"][:7] for c in body]
    assert months == sorted(months, reverse=True)
    assert {"2026-05", "2026-06", "2026-07"}.issubset(set(months))


def test_approve_can_push_cycle_negative(db, brand_a):
    """Decisión confirmada por el usuario: aprobar nunca bloquea por fondos,
    aunque deje el ciclo en negativo (doc/mejoras-diseno-fase1.md §0.B)."""
    creator = make_creator(db, name="C8", cycle_budget_amount=100, cycle_period="mensual")
    approver = make_user(db, username="revisor", password="ClaveValida123!", role="admin")
    ticket = crud.create_ticket(
        db=db,
        creator=creator,
        brand=brand_a,
        amount=500,
        file_name="f.pdf",
        file_path=__file__,
        mime_type="application/pdf",
        notes=None,
        status="pendiente",
        actor_user_id=approver.id,
    )
    approved = crud.approve_ticket(db, ticket, actor_user_id=approver.id)
    assert approved.status == "aprobado"
    cycle = approved.budget_cycle
    assert cycle.spent == 500
    assert cycle.amount - cycle.spent == -400  # negativo, permitido


def test_soft_delete_reverts_cycle_spent(db, brand_a):
    """R12: borrar (lógico) un ticket aprobado revierte su monto del ciclo."""
    creator = make_creator(db, name="C11", cycle_budget_amount=1000, cycle_period="mensual")
    approver = make_user(db, username="revisor3", password="ClaveValida123!", role="admin")
    ticket = crud.create_ticket(
        db=db,
        creator=creator,
        brand=brand_a,
        amount=300,
        file_name="f.pdf",
        file_path=__file__,
        mime_type="application/pdf",
        notes=None,
        status="aprobado",
        actor_user_id=approver.id,
    )
    cycle = ticket.budget_cycle
    assert cycle.spent == 300

    crud.soft_delete_ticket(db, ticket, actor_user_id=approver.id)
    db.refresh(cycle)
    assert cycle.spent == 0


def test_update_creator_without_aplicar_ahora_only_affects_next_cycle(db):
    """Default (sin `aplicar_ahora`): crud.update_creator no toca el ciclo
    vigente (el de HOY, que es lo que resuelve `aplicar_ahora` internamente),
    solo el que se materialice después — mismo comportamiento de siempre,
    ahora verificado pasando por el flujo real de edición."""
    creator = make_creator(db, name="C12", cycle_budget_amount=1000, cycle_period="semanal")
    current = crud.get_or_create_cycle_for_date(db, creator, date.today())
    assert current.amount == 1000

    crud.update_creator(db, creator, schemas.CreatorUpdate(cycle_budget_amount=5000))

    db.refresh(current)
    assert current.amount == 1000  # sin cambios

    next_cycle = crud.get_or_create_cycle_for_date(db, creator, current.end_date + timedelta(days=1))
    assert next_cycle.amount == 5000


def test_update_creator_con_aplicar_ahora_sobreescribe_ciclo_vigente(db):
    """`aplicar_ahora=True`: el nuevo monto rige de inmediato en el ciclo YA
    en curso (el de HOY), sin esperar a que abra el siguiente."""
    creator = make_creator(db, name="C13", cycle_budget_amount=1000, cycle_period="semanal")
    current = crud.get_or_create_cycle_for_date(db, creator, date.today())
    assert current.amount == 1000

    crud.update_creator(
        db, creator, schemas.CreatorUpdate(cycle_budget_amount=5000, aplicar_ahora=True)
    )

    db.refresh(current)
    assert current.amount == 5000

    # El siguiente ciclo también usa el monto nuevo (comportamiento normal).
    next_cycle = crud.get_or_create_cycle_for_date(db, creator, current.end_date + timedelta(days=1))
    assert next_cycle.amount == 5000


def test_aplicar_ahora_no_revierte_lo_ya_gastado(db, brand_a):
    """Aplicar ahora un monto menor a lo ya gastado deja el ciclo en negativo
    (mismo principio que R7 §2.5: nunca se bloquea ni se ajusta `spent`)."""
    creator = make_creator(db, name="C14", cycle_budget_amount=1000, cycle_period="mensual")
    approver = make_user(db, username="revisor4", password="ClaveValida123!", role="admin")
    ticket = crud.create_ticket(
        db=db, creator=creator, brand=brand_a, amount=800,
        file_name="f.pdf", file_path=__file__, mime_type="application/pdf",
        notes=None, status="aprobado", actor_user_id=approver.id,
    )
    cycle = ticket.budget_cycle
    assert cycle.spent == 800

    crud.update_creator(
        db, creator, schemas.CreatorUpdate(cycle_budget_amount=500, aplicar_ahora=True)
    )
    db.refresh(cycle)
    assert cycle.amount == 500
    assert cycle.spent == 800  # no se toca
    assert cycle.amount - cycle.spent == -300  # negativo, permitido
