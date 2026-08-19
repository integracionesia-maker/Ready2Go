"""Reglas de gestión de usuarios (R4: exclusiva de superadmin desde
doc/prompt-mejoras-integrales.md): un admin ya NO tiene ningún acceso a
/api/users/*; solo superadmin gestiona usuarios. El rol/estado del superadmin
sigue siendo inmutable por API; su contraseña SOLO puede resetearla otro
superadmin (POST /{id}/reset-password-superadmin, 2026-08-19)."""

from datetime import datetime, timedelta, timezone

import pytest

from app import crud, models

from .conftest import login, make_user


ADMIN_FORBIDDEN_CALLS = [
    ("get", "/api/users/", None),
    ("post", "/api/users/", {"username": "x", "email": "x@test.com", "full_name": "X", "role": "creador", "password": "ClaveValida123!"}),
    ("post", "/api/users/1/reset-password-superadmin", None),
]


@pytest.mark.parametrize("method,path,body", ADMIN_FORBIDDEN_CALLS)
def test_admin_forbidden_from_user_management(logged_in_admin, method, path, body):
    kwargs = {"json": body} if body is not None else {}
    resp = getattr(logged_in_admin, method)(path, **kwargs)
    assert resp.status_code == 403


def test_admin_forbidden_from_user_detail_endpoints(logged_in_admin, db, creador_user):
    other_admin = make_user(db, username="admin2", password="Clave123456!", role="admin")
    assert logged_in_admin.get(f"/api/users/{creador_user.id}").status_code == 403
    assert logged_in_admin.put(f"/api/users/{creador_user.id}", json={"full_name": "Hackeado"}).status_code == 403
    assert logged_in_admin.post(f"/api/users/{creador_user.id}/reset-password").status_code == 403
    assert logged_in_admin.post(f"/api/users/{creador_user.id}/reset-password-superadmin").status_code == 403
    assert logged_in_admin.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": False}).status_code == 403
    assert logged_in_admin.get(f"/api/users/{other_admin.id}").status_code == 403


def test_creador_forbidden_from_user_management(logged_in_creador):
    assert logged_in_creador.get("/api/users/").status_code == 403


def test_superadmin_sees_all_roles(logged_in_superadmin, superadmin_user, admin_user, creador_user):
    resp = logged_in_superadmin.get("/api/users/")
    assert resp.status_code == 200
    data = resp.json()
    usernames = {u["username"] for u in data["items"]}
    assert {superadmin_user.username, admin_user.username, creador_user.username} <= usernames
    assert data["total"] >= 3


def test_superadmin_can_create_admin(logged_in_superadmin):
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "nuevo.admin",
            "email": "nuevo.admin@test.com",
            "full_name": "Nuevo Admin",
            "role": "admin",
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 201


def test_superadmin_can_create_creador_linked_to_a_creator(logged_in_superadmin, creator_b):
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "nuevo.creador",
            "email": "nuevo.creador@test.com",
            "full_name": "Nuevo Creador",
            "role": "creador",
            "creator_id": creator_b.id,
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["must_change_password"] is True


def test_superadmin_cannot_create_superadmin(logged_in_superadmin):
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "otro.sa",
            "email": "otro.sa@test.com",
            "full_name": "Otro SA",
            "role": "superadmin",
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 400


def test_superadmin_role_immutable(logged_in_superadmin, superadmin_user):
    resp = logged_in_superadmin.put(f"/api/users/{superadmin_user.id}", json={"role": "admin"})
    assert resp.status_code == 403


def test_superadmin_status_immutable(logged_in_superadmin, superadmin_user):
    resp = logged_in_superadmin.patch(f"/api/users/{superadmin_user.id}/estado", json={"is_active": False})
    assert resp.status_code == 403


def test_superadmin_can_deactivate_admin(logged_in_superadmin, admin_user):
    resp = logged_in_superadmin.patch(f"/api/users/{admin_user.id}/estado", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_deactivated_user_cannot_login(logged_in_superadmin, creador_user):
    from .conftest import PASSWORD_CREADOR, login
    from fastapi.testclient import TestClient
    from app.main import app

    resp = logged_in_superadmin.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": False})
    assert resp.status_code == 200

    other = TestClient(app)
    login_resp = login(other, creador_user.username, PASSWORD_CREADOR)
    assert login_resp.status_code == 401


def test_reset_password_returns_temporary_password_once(logged_in_superadmin, creador_user):
    resp = logged_in_superadmin.post(f"/api/users/{creador_user.id}/reset-password")
    assert resp.status_code == 200
    assert len(resp.json()["temporary_password"]) > 0


def test_weak_password_rejected_on_create(logged_in_superadmin):
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "debil",
            "email": "debil@test.com",
            "full_name": "Debil",
            "role": "creador",
            "password": "short1",
        },
    )
    assert resp.status_code in (400, 422)


def test_creador_role_requires_creator_id(logged_in_superadmin):
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "sin.creador",
            "email": "sin.creador@test.com",
            "full_name": "Sin Creador",
            "role": "creador",
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 400


# ── Reset de contraseña ENTRE superadmins (2026-08-19) ────────────────────────


def test_superadmin_resetea_a_otro_superadmin(
    client, logged_in_superadmin, superadmin_user, superadmin_user_b, db
):
    # Estado previo: bloqueado por intentos fallidos (el reset debe desbloquearlo,
    # igual que el script de servidor) + una sesión refresh viva (debe revocarse).
    superadmin_user_b.failed_login_attempts = 5
    superadmin_user_b.locked_until = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    tv_antes = superadmin_user_b.token_version
    rt = crud.create_refresh_token_record(
        db,
        superadmin_user_b.id,
        "hash-de-prueba",
        datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
    )

    resp = logged_in_superadmin.post(f"/api/users/{superadmin_user_b.id}/reset-password-superadmin")
    assert resp.status_code == 200
    temp = resp.json()["temporary_password"]
    assert len(temp) > 0

    db.refresh(superadmin_user_b)
    assert superadmin_user_b.must_change_password is True
    assert superadmin_user_b.token_version == tv_antes + 1
    assert superadmin_user_b.failed_login_attempts == 0
    assert superadmin_user_b.locked_until is None

    db.refresh(rt)
    assert rt.revoked_at is not None

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action == "password.reset_superadmin")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.actor_user_id == superadmin_user.id
    assert fila.target_id == superadmin_user_b.id

    # La contraseña temporal sirve para entrar y exige cambio.
    resp_login = login(client, "superadmin2", temp)
    assert resp_login.status_code == 200
    assert resp_login.json()["user"]["must_change_password"] is True


def test_superadmin_no_se_resetea_a_si_mismo(logged_in_superadmin, superadmin_user):
    resp = logged_in_superadmin.post(f"/api/users/{superadmin_user.id}/reset-password-superadmin")
    assert resp.status_code == 400


def test_reset_superadmin_a_no_superadmin_da_400(logged_in_superadmin, admin_user):
    resp = logged_in_superadmin.post(f"/api/users/{admin_user.id}/reset-password-superadmin")
    assert resp.status_code == 400


def test_reset_superadmin_inexistente_da_404(logged_in_superadmin):
    assert logged_in_superadmin.post("/api/users/999999/reset-password-superadmin").status_code == 404


def test_list_users_exclude_role_superadmin(logged_in_superadmin, superadmin_user, admin_user):
    resp = logged_in_superadmin.get("/api/users/", params={"exclude_role": "superadmin"})
    assert resp.status_code == 200
    roles = {u["role"] for u in resp.json()["items"]}
    assert "superadmin" not in roles


def test_list_users_role_superadmin_alimenta_la_card(logged_in_superadmin, superadmin_user, superadmin_user_b):
    resp = logged_in_superadmin.get("/api/users/", params={"role": "superadmin"})
    assert resp.status_code == 200
    data = resp.json()
    assert {u["role"] for u in data["items"]} == {"superadmin"}
    assert data["total"] >= 2
