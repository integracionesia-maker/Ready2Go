"""Borrado lógico y físico de tickets (R12): reversión de descuento del ciclo,
exclusión de listados/dashboard/brand-spend, y que un ticket borrado deje de
poder aprobarse/rechazarse. Ver doc/borrado-tickets.md."""

from pathlib import Path


def _upload(client, creator_id, brand_id, amount=100, n_files=1):
    return client.post(
        "/api/tickets/",
        data={"creator_id": str(creator_id), "brand_id": str(brand_id), "amount": str(amount)},
        files=[
            ("files", (f"f{i}.pdf", b"%PDF-1.4", "application/pdf"))
            for i in range(n_files)
        ],
    )


def test_soft_delete_approved_ticket_reverts_cycle(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=300).json()
    assert ticket["status"] == "aprobado"

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")
    assert resp.status_code == 200
    assert resp.json()["is_deleted"] is True

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 0


def test_soft_delete_pending_ticket_no_cycle_change(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=300).json()
    assert ticket["status"] == "pendiente"

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")
    assert resp.status_code == 200

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 0


def test_hard_delete_removes_file(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()
    file_path = Path(ticket["file_path"])
    assert file_path.exists()

    resp = logged_in_admin.delete(f"/api/tickets/{ticket['id']}/permanent")
    assert resp.status_code == 200
    assert not file_path.exists()


def test_hard_delete_removes_all_photos(logged_in_admin, creator_a, brand_a, db):
    from app import models

    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100, n_files=3).json()
    media_rows = db.query(models.TicketMedia).filter(
        models.TicketMedia.ticket_id == ticket["id"]
    ).all()
    assert len(media_rows) == 3
    file_paths = [Path(m.file_path) for m in media_rows]
    assert all(p.exists() for p in file_paths)

    resp = logged_in_admin.delete(f"/api/tickets/{ticket['id']}/permanent")
    assert resp.status_code == 200
    assert not any(p.exists() for p in file_paths)


def test_hard_delete_reverts_cycle_if_approved(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=400).json()

    resp = logged_in_admin.delete(f"/api/tickets/{ticket['id']}/permanent")
    assert resp.status_code == 200

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 0


def test_soft_then_hard_delete_does_not_double_revert(logged_in_admin, creator_a, brand_a):
    """Si un ticket aprobado ya fue soft-deleted (revirtió una vez) y luego se
    hard-deletea, el ciclo no debe revertirse una segunda vez."""
    other_ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=200).json()
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=400).json()

    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")
    logged_in_admin.delete(f"/api/tickets/{ticket['id']}/permanent")

    creator_resp = logged_in_admin.get(f"/api/creators/{creator_a.id}")
    assert creator_resp.json()["cycle_spent"] == 200  # solo lo del other_ticket


def test_deleted_ticket_not_in_list(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    resp = logged_in_admin.get("/api/tickets/")
    ids = [t["id"] for t in resp.json()]
    assert ticket["id"] not in ids


def test_deleted_ticket_not_in_dashboard(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=500).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    summary = logged_in_admin.get("/api/dashboard/summary").json()
    assert summary["total_spent"] == 0
    assert summary["ticket_count"] == 0

    monthly = logged_in_admin.get("/api/dashboard/monthly-spend").json()
    assert monthly == []

    creator_usage = logged_in_admin.get("/api/dashboard/creator-usage").json()
    item = next(c for c in creator_usage if c["creator_id"] == creator_a.id)
    assert item["spent"] == 0


def test_deleted_ticket_not_in_brand_spend(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=700).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    breakdown = logged_in_admin.get("/api/tickets/brand-spend").json()
    item = next(b for b in breakdown if b["brand_name"] == brand_a.name)
    assert item["total_spent"] == 0


def test_approve_deleted_ticket_fails(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=100).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/aprobar")
    assert resp.status_code == 404


def test_reject_deleted_ticket_fails(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=100).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/rechazar", json={"reason": "x"})
    assert resp.status_code == 404


def test_download_deleted_ticket_is_404(logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()
    logged_in_admin.post(f"/api/tickets/{ticket['id']}/soft-delete")

    resp = logged_in_admin.get(f"/api/tickets/file/{ticket['id']}")
    assert resp.status_code == 404


def test_soft_delete_as_creator_forbidden(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()
    resp = logged_in_creador.post(f"/api/tickets/{ticket['id']}/soft-delete")
    assert resp.status_code == 403


def test_hard_delete_as_creator_forbidden(logged_in_creador, logged_in_admin, creator_a, brand_a):
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()
    resp = logged_in_creador.delete(f"/api/tickets/{ticket['id']}/permanent")
    assert resp.status_code == 403
