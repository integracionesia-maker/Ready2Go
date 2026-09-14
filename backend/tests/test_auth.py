"""Login, cambio de contraseña, bloqueo por intentos fallidos, rate limiting,
rotación/reuso de refresh token, logout, y auto-desbloqueo con rompecabezas."""

import time

from app import security

from .conftest import (
    PASSWORD_CREADOR,
    PASSWORD_SUPERADMIN,
    login,
    make_user,
)


def test_login_success_returns_user_and_cookies(client, creador_user):
    resp = login(client, creador_user.username, PASSWORD_CREADOR)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == creador_user.username
    assert body["user"]["role"] == "creador"
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies


def test_login_wrong_password_generic_message(client, creador_user):
    resp = login(client, creador_user.username, "clave-incorrecta-123")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Usuario o contraseña incorrectos."


def test_login_unknown_user_same_generic_message(client):
    resp = login(client, "no-existe", "cualquier-cosa-123")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Usuario o contraseña incorrectos."


def test_login_inactive_account_same_generic_message(client, db):
    make_user(db, username="inactivo", password="ClaveValida123!", role="creador", is_active=False)
    resp = login(client, "inactivo", "ClaveValida123!")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Usuario o contraseña incorrectos."


def test_login_by_email_also_works(client, creador_user):
    resp = login(client, creador_user.email, PASSWORD_CREADOR)
    assert resp.status_code == 200


def test_must_change_password_flag_present(client, db):
    make_user(db, username="nuevo", password="ClaveTemporal123!", role="creador", must_change_password=True)
    resp = login(client, "nuevo", "ClaveTemporal123!")
    assert resp.json()["user"]["must_change_password"] is True


def test_account_lockout_after_five_failed_attempts(client, creador_user):
    for _ in range(5):
        r = login(client, creador_user.username, "clave-mala")
        assert r.status_code == 401

    resp = login(client, creador_user.username, PASSWORD_CREADOR)
    assert resp.status_code == 401
    assert "bloqueada" in resp.json()["detail"].lower()


def test_locked_response_carries_stable_codigo_y_locked_until(client, creador_user):
    """El 401 de cuenta bloqueada lleva `codigo`/`locked_until` en la raiz del
    cuerpo (no anidados en `detail`) para que el cliente pueda mostrar el
    rompecabezas en vez de solo un texto de error generico."""
    for _ in range(5):
        login(client, creador_user.username, "clave-mala")

    body = login(client, creador_user.username, PASSWORD_CREADOR).json()
    assert body["codigo"] == "CUENTA_BLOQUEADA"
    assert body["locked_until"] is not None


# ── Auto-desbloqueo con rompecabezas ────────────────────────────────────────


def _bloquear(client, username):
    for _ in range(5):
        client.post("/api/auth/login", json={"identificador": username, "password": "clave-mala"})


def _trail_hacia(target_percent):
    return [
        {"x": 0, "t": 0},
        {"x": target_percent / 2, "t": 100},
        {"x": target_percent, "t": 200},
    ]


def _pedir_challenge(client, username):
    return client.post("/api/auth/unlock/challenge", json={"identificador": username}).json()


def _verificar(client, username, reto, posicion=None):
    return client.post(
        "/api/auth/unlock/verify",
        json={
            "challenge_id": reto["challenge_id"],
            "identificador": username,
            "posicion_percent": posicion if posicion is not None else reto["target_percent"],
            "trail": _trail_hacia(posicion if posicion is not None else reto["target_percent"]),
        },
    )


def test_unlock_challenge_exige_cuenta_bloqueada(client, creador_user):
    resp = client.post("/api/auth/unlock/challenge", json={"identificador": creador_user.username})
    assert resp.status_code == 404


def test_unlock_resuelto_desbloquea_pero_no_inicia_sesion(client, creador_user):
    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)

    time.sleep(0.4)
    resp = _verificar(client, creador_user.username, reto)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # La contraseña sigue haciendo falta: el puzzle limpia el bloqueo, no
    # abre sesion por si mismo.
    assert login(client, creador_user.username, PASSWORD_CREADOR).status_code == 200


def test_unlock_posicion_incorrecta_no_desbloquea(client, creador_user):
    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)

    time.sleep(0.4)
    resp = _verificar(client, creador_user.username, reto, posicion=reto["target_percent"] + 20)
    assert resp.status_code == 400
    assert login(client, creador_user.username, PASSWORD_CREADOR).status_code == 401


def test_unlock_demasiado_rapido_falla(client, creador_user):
    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)

    resp = _verificar(client, creador_user.username, reto)  # sin esperar
    assert resp.status_code == 400


def test_unlock_sin_arrastre_real_falla(client, creador_user):
    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)

    time.sleep(0.4)
    resp = client.post(
        "/api/auth/unlock/verify",
        json={
            "challenge_id": reto["challenge_id"],
            "identificador": creador_user.username,
            "posicion_percent": reto["target_percent"],
            "trail": [{"x": reto["target_percent"], "t": 0}],  # un solo punto
        },
    )
    assert resp.status_code == 400


def test_unlock_challenge_vencido_falla(client, creador_user, monkeypatch):
    monkeypatch.setattr(security, "_CHALLENGE_TTL_SECONDS", 0.05)
    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)

    time.sleep(0.1)
    resp = _verificar(client, creador_user.username, reto)
    assert resp.status_code == 400


def test_unlock_challenge_se_agota_tras_max_intentos(client, creador_user, monkeypatch):
    monkeypatch.setattr(security, "_CHALLENGE_MAX_INTENTOS", 2)
    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)

    time.sleep(0.4)
    for _ in range(3):
        resp = _verificar(client, creador_user.username, reto, posicion=reto["target_percent"] + 20)
    assert resp.status_code == 400
    assert "nuevo" in resp.json()["detail"].lower()


def test_self_unlock_tiene_limite_diario(client, creador_user, monkeypatch):
    monkeypatch.setattr(security, "_SELF_UNLOCK_MAX_PER_DAY", 1)

    _bloquear(client, creador_user.username)
    reto = _pedir_challenge(client, creador_user.username)
    time.sleep(0.4)
    assert _verificar(client, creador_user.username, reto).status_code == 200

    _bloquear(client, creador_user.username)
    resp = client.post("/api/auth/unlock/challenge", json={"identificador": creador_user.username})
    assert resp.status_code == 429


def test_ip_rate_limit_returns_429(client):
    for _ in range(30):
        client.post("/api/auth/login", json={"identificador": "x", "password": "y"})
    resp = client.post("/api/auth/login", json={"identificador": "x", "password": "y"})
    assert resp.status_code == 429


def test_change_password_requires_correct_current_password(logged_in_creador):
    resp = logged_in_creador.post(
        "/api/auth/change-password",
        json={"current_password": "clave-incorrecta", "new_password": "NuevaClaveValida123!"},
    )
    assert resp.status_code == 400


def test_change_password_rejects_weak_composition(logged_in_creador):
    resp = logged_in_creador.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD_CREADOR, "new_password": "sololetrassinnumero"},
    )
    assert resp.status_code == 400


def test_change_password_success_and_old_password_stops_working(client, creador_user):
    login(client, creador_user.username, PASSWORD_CREADOR)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD_CREADOR, "new_password": "NuevaClaveValida123!"},
    )
    assert resp.status_code == 200

    # La sesion actual sigue viva (se reemitieron las cookies)
    assert client.get("/api/auth/me").status_code == 200

    # Login en un cliente nuevo: la clave vieja ya no sirve, la nueva si.
    from fastapi.testclient import TestClient
    from app.main import app

    other = TestClient(app)
    assert login(other, creador_user.username, PASSWORD_CREADOR).status_code == 401
    assert login(other, creador_user.username, "NuevaClaveValida123!").status_code == 200


def test_refresh_rotates_cookie(client, creador_user):
    login(client, creador_user.username, PASSWORD_CREADOR)
    old_refresh = client.cookies.get("refresh_token")

    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != old_refresh


def test_refresh_reuse_detected_revokes_chain(client, creador_user):
    login(client, creador_user.username, PASSWORD_CREADOR)
    old_refresh = client.cookies.get("refresh_token")

    assert client.post("/api/auth/refresh").status_code == 200
    new_refresh = client.cookies.get("refresh_token")

    # Reutilizar el token viejo (ya rotado) debe ser rechazado...
    client.cookies.set("refresh_token", old_refresh)
    assert client.post("/api/auth/refresh").status_code == 401

    # ...y debe haber revocado también el token nuevo (toda la cadena).
    client.cookies.set("refresh_token", new_refresh)
    assert client.post("/api/auth/refresh").status_code == 401


def test_refresh_without_cookie_is_401(client):
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_revokes_refresh_and_access(client, creador_user):
    login(client, creador_user.username, PASSWORD_CREADOR)
    assert client.get("/api/auth/me").status_code == 200

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200

    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/refresh").status_code == 401


def test_password_cannot_equal_username(client, db):
    # Username de 10+ caracteres para aislar la regla de igualdad de la de longitud mínima.
    long_username = "usuariolargo"
    make_user(db, username=long_username, password=PASSWORD_CREADOR, role="creador")
    login(client, long_username, PASSWORD_CREADOR)

    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD_CREADOR, "new_password": long_username},
    )
    assert resp.status_code == 400
    assert "igual al nombre de usuario" in resp.json()["detail"]
