"""Flujo de validación de tickets (R10): pendiente/aprobado/rechazado,
descuento solo al aprobar, motivo obligatorio al rechazar, permisos."""

from .conftest import PASSWORD_ADMIN, PASSWORD_CREADOR


def _upload(client, creator_id, brand_id, amount=100, n_files=1):
    return client.post(
        "/api/tickets/",
        data={"creator_id": str(creator_id), "brand_id": str(brand_id), "amount": str(amount)},
        files=[
            ("files", (f"f{i}.pdf", b"%PDF-1.4", "application/pdf"))
            for i in range(n_files)
        ],
    )


def test_creador_ticket_born_pending_no_deduction(logged_in_creador, creator_a, brand_a):
    resp = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=100)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pendiente"
    assert body["reviewed_at"] is None

    creator_resp = logged_in_creador.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 0  # no descontó


def test_admin_ticket_auto_approved_and_deducts(logged_in_admin, creator_a, brand_a):
    resp = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=250)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "aprobado"
    assert body["reviewed_at"] is not None

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 250


def test_admin_approves_pending_ticket_and_it_deducts(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=300).json()

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/aprobar")
    assert resp.status_code == 200
    assert resp.json()["status"] == "aprobado"

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 300


def test_admin_rejects_pending_ticket_requires_reason(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=150).json()

    # Sin razon -> 422 (Pydantic exige el campo)
    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/rechazar", json={})
    assert resp.status_code == 422

    resp = logged_in_admin.post(
        f"/api/tickets/{ticket['id']}/rechazar", json={"reason": "Comprobante ilegible"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rechazado"
    assert body["rejection_reason"] == "Comprobante ilegible"

    # No debe haber descontado del ciclo.
    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 0


def test_creador_sees_rejection_reason_on_own_ticket(client, creator_a, brand_a, creador_user, db):
    from .conftest import login

    login(client, "creador.a", PASSWORD_CREADOR)
    ticket = _upload(client, creator_a.id, brand_a.id, amount=80).json()

    from fastapi.testclient import TestClient
    from app.main import app
    from .conftest import make_user

    admin = make_user(db, username="admin.rev", password=PASSWORD_ADMIN, role="admin")
    admin_client = TestClient(app)
    login(admin_client, "admin.rev", PASSWORD_ADMIN)
    admin_client.post(f"/api/tickets/{ticket['id']}/rechazar", json={"reason": "Monto no coincide"})

    resp = client.get("/api/tickets/")
    own = next(t for t in resp.json() if t["id"] == ticket["id"])
    assert own["status"] == "rechazado"
    assert own["rejection_reason"] == "Monto no coincide"


def test_cannot_approve_already_approved_ticket(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=90).json()
    assert ticket["status"] == "aprobado"

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/aprobar")
    assert resp.status_code == 400


def test_creador_cannot_approve_or_reject(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=90).json()
    assert logged_in_creador.post(f"/api/tickets/{ticket['id']}/aprobar").status_code == 403
    assert (
        logged_in_creador.post(f"/api/tickets/{ticket['id']}/rechazar", json={"reason": "x"}).status_code
        == 403
    )


def test_filter_tickets_by_status(logged_in_admin, creator_a, brand_a, creador_user, logged_in_creador):
    _upload(logged_in_admin, creator_a.id, brand_a.id, amount=50)  # aprobado
    _upload(logged_in_creador, creator_a.id, brand_a.id, amount=60)  # pendiente

    pendientes = logged_in_admin.get("/api/tickets/?status=pendiente").json()
    aprobados = logged_in_admin.get("/api/tickets/?status=aprobado").json()
    assert len(pendientes) == 1
    assert len(aprobados) == 1
    assert pendientes[0]["amount"] == 60
    assert aprobados[0]["amount"] == 50


def test_approve_pushes_cycle_negative_without_blocking(logged_in_creador, logged_in_admin, creator_a, brand_a):
    # creator_a tiene cycle_budget_amount == initial_budget == 10_000 (ver conftest)
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=50_000).json()
    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/aprobar")
    assert resp.status_code == 200

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    data = creator_resp.json()
    assert data["cycle_spent"] == 50_000
    assert data["cycle_remaining"] < 0


def test_soft_deleted_pending_ticket_not_in_validation_queue(logged_in_creador, logged_in_admin, creator_a, brand_a):
    """R12: un ticket pendiente borrado (lógico) ya no debe aparecer en la cola de validación."""
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=90).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    pendientes = logged_in_admin.get("/api/tickets/?status=pendiente").json()
    assert all(t["id"] != ticket["id"] for t in pendientes)


def test_ticket_can_have_multiple_photos(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=90, n_files=3).json()
    assert len(ticket["media"]) == 3
    # Las columnas legacy siguen reflejando la primera foto.
    assert ticket["file_name"] == ticket["media"][0]["file_name"]


def test_ticket_upload_requires_at_least_one_file(logged_in_admin, creator_a, brand_a):
    resp = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=90, n_files=0)
    assert resp.status_code in (400, 422)


def test_ticket_upload_rejects_over_max_files(logged_in_admin, creator_a, brand_a):
    from app.upload_manager import MAX_FILES_PER_TICKET

    resp = _upload(
        logged_in_admin, creator_a.id, brand_a.id, amount=90,
        n_files=MAX_FILES_PER_TICKET + 1,
    )
    assert resp.status_code == 400


def test_download_individual_media_by_id(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=90, n_files=2).json()

    for media in ticket["media"]:
        resp = logged_in_admin.get(f"/api/tickets/media/{media['id']}")
        assert resp.status_code == 200


def test_creador_cannot_download_media_of_other_creador_ticket(
    logged_in_creador, logged_in_admin, creator_b, brand_a
):
    """`logged_in_creador` está ligado a creator_a; un ticket de creator_b no es suyo."""
    ticket = _upload(logged_in_admin, creator_b.id, brand_a.id, amount=90, n_files=1).json()
    media_id = ticket["media"][0]["id"]

    resp = logged_in_creador.get(f"/api/tickets/media/{media_id}")
    assert resp.status_code == 403
