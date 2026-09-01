"""GET /api/dashboard/tickets-per-day: cuenta TODOS los tickets no borrados
subidos cada día (cualquier status — es actividad/uso, no gasto aprobado),
filtrable por rango, misma puerta que el resto del dashboard."""

from datetime import datetime

from .conftest import make_ticket


def _set_upload_date(db, ticket, iso_datetime):
    ticket.upload_date = datetime.fromisoformat(iso_datetime)
    db.commit()


def test_cuenta_tickets_por_dia(logged_in_admin, db, creator_a, brand_a):
    t1 = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    t2 = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    t3 = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    _set_upload_date(db, t1, "2026-08-10T09:00:00")
    _set_upload_date(db, t2, "2026-08-10T15:00:00")
    _set_upload_date(db, t3, "2026-08-12T09:00:00")

    resp = logged_in_admin.get("/api/dashboard/tickets-per-day?start_date=2026-08-01&end_date=2026-08-31")
    assert resp.status_code == 200
    por_dia = {r["day"]: r["count"] for r in resp.json()}
    assert por_dia["2026-08-10"] == 2
    assert por_dia["2026-08-12"] == 1


def test_cuenta_pendientes_y_rechazados_tambien(logged_in_admin, db, creator_a, brand_a):
    # A diferencia de monthly-spend (solo aprobados): esto es actividad, cuenta todo.
    aprobado = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    pendiente = make_ticket(db, creator=creator_a, brand=brand_a, status="pendiente")
    rechazado = make_ticket(db, creator=creator_a, brand=brand_a, status="rechazado")
    for t in (aprobado, pendiente, rechazado):
        _set_upload_date(db, t, "2026-08-15T09:00:00")

    resp = logged_in_admin.get("/api/dashboard/tickets-per-day?start_date=2026-08-01&end_date=2026-08-31")
    por_dia = {r["day"]: r["count"] for r in resp.json()}
    assert por_dia["2026-08-15"] == 3


def test_excluye_borrados(logged_in_admin, db, creator_a, brand_a):
    t1 = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    t2 = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    _set_upload_date(db, t1, "2026-08-20T09:00:00")
    _set_upload_date(db, t2, "2026-08-20T10:00:00")

    logged_in_admin.post(f"/api/tickets/{t1.id}/soft-delete")

    resp = logged_in_admin.get("/api/dashboard/tickets-per-day?start_date=2026-08-01&end_date=2026-08-31")
    por_dia = {r["day"]: r["count"] for r in resp.json()}
    assert por_dia["2026-08-20"] == 1


def test_filtro_de_rango_excluye_fuera_de_rango(logged_in_admin, db, creator_a, brand_a):
    dentro = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    fuera = make_ticket(db, creator=creator_a, brand=brand_a, status="aprobado")
    _set_upload_date(db, dentro, "2026-08-10T09:00:00")
    _set_upload_date(db, fuera, "2026-07-10T09:00:00")

    resp = logged_in_admin.get("/api/dashboard/tickets-per-day?start_date=2026-08-01&end_date=2026-08-31")
    por_dia = {r["day"]: r["count"] for r in resp.json()}
    assert "2026-08-10" in por_dia
    assert "2026-07-10" not in por_dia


def test_forbidden_para_creador(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/tickets-per-day").status_code == 403


def test_no_autenticado_da_401(client):
    assert client.get("/api/dashboard/tickets-per-day").status_code == 401
