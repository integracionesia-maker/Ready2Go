"""Visibilidad de tickets `pendiente` en el dashboard (monthly-spend,
creator-usage, summary): informativo, agregado por separado del gasto
`aprobado` — NUNCA se suma a los totales oficiales ni afecta el ciclo (R7)."""

from datetime import datetime

from .conftest import make_ticket


def _set_upload_date(db, ticket, iso_datetime):
    ticket.upload_date = datetime.fromisoformat(iso_datetime)
    db.commit()


def test_monthly_spend_separa_aprobado_de_pendiente(logged_in_admin, db, creator_a, brand_a):
    aprobado = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    pendiente = make_ticket(db, creator=creator_a, brand=brand_a, amount=300, status="pendiente")
    _set_upload_date(db, aprobado, "2026-08-10T09:00:00")
    _set_upload_date(db, pendiente, "2026-08-10T10:00:00")

    resp = logged_in_admin.get("/api/dashboard/monthly-spend?start_date=2026-08-01&end_date=2026-08-31")
    body = {r["month"]: r for r in resp.json()}
    assert body["2026-08"]["total"] == 1000
    assert body["2026-08"]["count"] == 1
    assert body["2026-08"]["pending_total"] == 300
    assert body["2026-08"]["pending_count"] == 1


def test_monthly_spend_mes_solo_con_pendientes_igual_aparece(logged_in_admin, db, creator_a, brand_a):
    # Mes sin nada aprobado todavia (ej. el mes en curso) debe salir igual,
    # con total=0 y pending_total>0 — antes de este cambio no aparecia.
    solo_pendiente = make_ticket(db, creator=creator_a, brand=brand_a, amount=500, status="pendiente")
    _set_upload_date(db, solo_pendiente, "2026-09-05T09:00:00")

    resp = logged_in_admin.get("/api/dashboard/monthly-spend?start_date=2026-09-01&end_date=2026-09-30")
    body = {r["month"]: r for r in resp.json()}
    assert body["2026-09"]["total"] == 0
    assert body["2026-09"]["count"] == 0
    assert body["2026-09"]["pending_total"] == 500
    assert body["2026-09"]["pending_count"] == 1


def test_creator_usage_incluye_pendiente_sin_tocar_percentage(logged_in_admin, db, creator_a, brand_a):
    aprobado = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    pendiente = make_ticket(db, creator=creator_a, brand=brand_a, amount=400, status="pendiente")
    _set_upload_date(db, aprobado, "2026-08-10T09:00:00")
    _set_upload_date(db, pendiente, "2026-08-10T10:00:00")

    resp = logged_in_admin.get("/api/dashboard/creator-usage?start_date=2026-08-01&end_date=2026-08-31")
    item = next(c for c in resp.json() if c["creator_id"] == creator_a.id)
    assert item["spent"] == 1000
    assert item["pending"] == 400
    assert item["pending_count"] == 1
    # `percentage` se calcula solo sobre `spent` — pending nunca lo toca.
    assert item["percentage"] == round((1000 / item["initial_budget"]) * 100, 1)


def test_creator_usage_creador_solo_con_pendientes_aparece(logged_in_admin, db, creator_a, brand_a):
    # Un creador que solo subio pendientes (nada aprobado aun) debe aparecer
    # en la lista con spent=0, pending>0 — antes el frontend lo filtraba por
    # spent>0 y desaparecia del todo.
    pendiente = make_ticket(db, creator=creator_a, brand=brand_a, amount=250, status="pendiente")
    _set_upload_date(db, pendiente, "2026-08-12T09:00:00")

    resp = logged_in_admin.get("/api/dashboard/creator-usage?start_date=2026-08-01&end_date=2026-08-31")
    item = next(c for c in resp.json() if c["creator_id"] == creator_a.id)
    assert item["spent"] == 0
    assert item["pending"] == 250
    assert item["pending_count"] == 1


def test_summary_pending_no_afecta_total_spent(logged_in_admin, db, creator_a, brand_a):
    aprobado = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    pendiente = make_ticket(db, creator=creator_a, brand=brand_a, amount=5000, status="pendiente")
    _set_upload_date(db, aprobado, "2026-08-10T09:00:00")
    _set_upload_date(db, pendiente, "2026-08-10T10:00:00")

    resp = logged_in_admin.get("/api/dashboard/summary?start_date=2026-08-01&end_date=2026-08-31")
    body = resp.json()
    assert body["total_spent"] == 1000
    assert body["ticket_count"] == 1
    assert body["pending_total"] == 5000
    assert body["pending_count"] == 1


def test_rechazados_no_cuentan_como_pendientes(logged_in_admin, db, creator_a, brand_a):
    rechazado = make_ticket(db, creator=creator_a, brand=brand_a, amount=800, status="rechazado")
    _set_upload_date(db, rechazado, "2026-08-10T09:00:00")

    resp = logged_in_admin.get("/api/dashboard/summary?start_date=2026-08-01&end_date=2026-08-31")
    body = resp.json()
    assert body["total_spent"] == 0
    assert body["pending_total"] == 0
    assert body["pending_count"] == 0
