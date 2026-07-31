"""Middleware de auditoria automatica + endpoints de consulta (solo superadmin)."""

from app import models


def test_middleware_registra_request_autenticada(client, logged_in_superadmin, superadmin_user, db):
    resp = logged_in_superadmin.get("/api/auth/me")
    assert resp.status_code == 200

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/me")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.actor_user_id == superadmin_user.id
    assert fila.http_method == "GET"
    assert fila.response_status == 200
    assert fila.duration_ms is not None and fila.duration_ms >= 0


def test_middleware_registra_request_no_autenticada(client, db):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/me")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.actor_user_id is None
    assert fila.response_status == 401


def test_middleware_no_audita_audit_logs(client, logged_in_superadmin, db):
    antes = db.query(models.AuditLog).filter(
        models.AuditLog.endpoint_path.like("/api/audit-logs%")
    ).count()

    resp = logged_in_superadmin.get("/api/audit-logs/")
    assert resp.status_code == 200

    despues = db.query(models.AuditLog).filter(
        models.AuditLog.endpoint_path.like("/api/audit-logs%")
    ).count()
    assert despues == antes


def test_get_audit_logs_requiere_superadmin(client, logged_in_admin, logged_in_superadmin):
    sin_token = client.get("/api/audit-logs/")
    assert sin_token.status_code == 401

    con_admin = logged_in_admin.get("/api/audit-logs/")
    assert con_admin.status_code == 403

    con_superadmin = logged_in_superadmin.get("/api/audit-logs/")
    assert con_superadmin.status_code == 200


def test_filtros_y_paginacion(client, logged_in_superadmin):
    # Genera trafico variado: varios GET (a /auth/me) y un POST real (login
    # de otro usuario, que ya pasa por el middleware antes de que exista sesion).
    for _ in range(3):
        logged_in_superadmin.get("/api/auth/me")
    client.post("/api/auth/login", json={"identificador": "no-existe", "password": "x"})

    resp = logged_in_superadmin.get(
        "/api/audit-logs/", params={"page": 1, "page_size": 2, "http_method": "POST"}
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["page"] == 1
    assert cuerpo["page_size"] == 2
    assert len(cuerpo["items"]) <= 2
    assert cuerpo["total"] >= 1
    assert all(item["http_method"] == "POST" for item in cuerpo["items"])
