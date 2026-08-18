"""Middleware de auditoria automatica + endpoints de consulta (solo superadmin).

La cola de auditoria (`audit_queue`) es asincrona; los tests usan TestClient
sin lifespan, asi que se llama `audit_queue.drenar_para_test()` despues de
cada request que deba generar eventos, para flushearlos sincronicamente antes
de consultar la DB.
"""

import json
import time as time_module

from app import models
from app import audit_queue


# ── Helpers ────────────────────────────────────────────────────────────────────

def _flush():
    """Drena la cola de auditoria para que los eventos sean visibles en la DB."""
    audit_queue.drenar_para_test()


# ── Tests de mutaciones (POST/PUT/PATCH/DELETE) ────────────────────────────────

def test_middleware_registra_mutacion_autenticada(client, logged_in_superadmin, superadmin_user, db):
    resp = logged_in_superadmin.post("/api/auth/logout")
    assert resp.status_code == 200
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/logout")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.actor_user_id == superadmin_user.id
    assert fila.http_method == "POST"
    assert fila.response_status == 200
    assert fila.duration_ms is not None and fila.duration_ms >= 0


def test_middleware_registra_mutacion_no_autenticada(client, db):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/logout")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.actor_user_id is None
    assert fila.response_status == 401


# ── Tests de GET (ahora SI se auditan) ─────────────────────────────────────────

def test_middleware_audita_get(client, logged_in_superadmin, superadmin_user, db):
    """GET a /api/* ahora SI genera fila en audit_log (compliance)."""
    resp = logged_in_superadmin.get("/api/auth/me")
    assert resp.status_code == 200
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/me")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None, "GET /api/auth/me deberia generar auditoria"
    assert fila.actor_user_id == superadmin_user.id
    assert fila.http_method == "GET"
    assert fila.response_status == 200


def test_middleware_no_audita_asset_estatico(client, db):
    """Rutas no-/api/* (assets, catch-all SPA) NO generan fila."""
    antes = db.query(models.AuditLog).count()

    # Simula un request a un asset estatico (no hay ruta real, pero el
    # middleware corre igual y debe descartarlo por el allowlist positivo).
    resp = client.get("/assets/index.js")
    # 404 o lo que sea — no importa, lo importante es que no se audite.
    assert resp.status_code in (404, 200)
    _flush()

    despues = db.query(models.AuditLog).count()
    assert despues == antes, "GET a /assets/ no deberia generar auditoria"


# ── Rutas excluidas ────────────────────────────────────────────────────────────

def test_middleware_no_audita_audit_logs(client, logged_in_superadmin, db):
    antes = db.query(models.AuditLog).filter(
        models.AuditLog.endpoint_path.like("/api/audit-logs%")
    ).count()

    resp = logged_in_superadmin.get("/api/audit-logs/")
    assert resp.status_code == 200
    _flush()

    despues = db.query(models.AuditLog).filter(
        models.AuditLog.endpoint_path.like("/api/audit-logs%")
    ).count()
    assert despues == antes


def test_middleware_no_audita_health(client, db):
    antes = db.query(models.AuditLog).count()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    _flush()
    despues = db.query(models.AuditLog).count()
    assert despues == antes, "GET /api/health no deberia generar auditoria"


# ── Endpoint de consulta de auditoria ──────────────────────────────────────────

def test_get_audit_logs_requiere_superadmin(client, logged_in_admin, logged_in_superadmin):
    sin_token = client.get("/api/audit-logs/")
    assert sin_token.status_code == 401

    con_admin = logged_in_admin.get("/api/audit-logs/")
    assert con_admin.status_code == 403

    con_superadmin = logged_in_superadmin.get("/api/audit-logs/")
    assert con_superadmin.status_code == 200


def test_filtros_y_paginacion(client, logged_in_superadmin):
    # Genera trafico variado: varios GET y un POST fallido (login invalido).
    for _ in range(3):
        logged_in_superadmin.get("/api/auth/me")
    client.post("/api/auth/login", json={"identificador": "no-existe", "password": "x"})
    _flush()

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


# ── Esquema standard_fields ────────────────────────────────────────────────────

def test_standard_fields_estructura(client, logged_in_superadmin, db):
    """Verifica que standard_fields contenga las 10 claves del esquema estandar."""
    resp = logged_in_superadmin.get("/api/auth/me")
    assert resp.status_code == 200
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/me")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.standard_fields is not None

    sf = json.loads(fila.standard_fields)

    # Las 10 claves requeridas
    assert "endpoint" in sf
    assert "type" in sf["endpoint"]
    assert sf["endpoint"]["type"] == "get"
    assert "name" in sf["endpoint"]
    assert sf["endpoint"]["name"] == "api/auth/me"

    assert "user" in sf
    assert "name" in sf["user"]

    assert "host" in sf
    assert "name" in sf["host"]
    assert isinstance(sf["host"]["name"], str) and len(sf["host"]["name"]) > 0

    assert "date" in sf
    assert isinstance(sf["date"], str)

    assert "status" in sf
    assert sf["status"] == 200

    assert "api" in sf
    assert "metod" in sf["api"]
    assert sf["api"]["metod"] == "GET"
    assert "response" in sf["api"]
    assert isinstance(sf["api"]["response"], int)

    assert "time" in sf
    assert isinstance(sf["time"], float)

    assert "log" in sf
    assert "GET /api/auth/me -> 200" in sf["log"]


def test_user_name_resuelto_por_lote(client, logged_in_superadmin, superadmin_user, db):
    """user.name debe ser el username real, no el id numerico."""
    resp = logged_in_superadmin.get("/api/auth/me")
    assert resp.status_code == 200
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/me")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    sf = json.loads(fila.standard_fields)
    assert sf["user"]["name"] == superadmin_user.username
    # Verificar que NO es el id numerico
    assert sf["user"]["name"] != str(superadmin_user.id)


def test_user_name_desconocido_sin_exception(client, db):
    """Request no autenticado: user.name es None sin lanzar excepcion."""
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/logout")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    sf = json.loads(fila.standard_fields)
    assert sf["user"]["name"] is None


def test_date_time_capturados_en_request_no_en_flush(client, db):
    """Dos eventos encolados con espera entre ellos deben reflejar timestamps
    distintos (el instante se captura en el enqueue, no en el flush)."""
    # Dos requests con un pequeno retraso entre ellos
    client.get("/api/health")  # excluido, no se audita
    resp1 = client.post("/api/auth/logout")
    time_module.sleep(0.35)
    resp2 = client.post("/api/auth/logout")
    _flush()

    filas = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/logout")
        .order_by(models.AuditLog.id.desc())
        .limit(2)
        .all()
    )
    assert len(filas) == 2

    sf1 = json.loads(filas[0].standard_fields)
    sf2 = json.loads(filas[1].standard_fields)

    # Los timestamps deben ser diferentes (diferencia >= 0.3s aprox)
    diff = abs(sf1["time"] - sf2["time"])
    assert diff >= 0.3, (
        f"Timestamps muy cercanos: diff={diff:.4f}s — "
        f"el instante se capturo en el flush, no en el enqueue"
    )

    # La fila mas reciente (id mas alto) debe tener el timestamp mas reciente
    assert sf1["time"] >= sf2["time"], (
        "La fila mas nueva debe tener timestamp >= la mas vieja"
    )


def test_standard_fields_en_mutacion(client, logged_in_superadmin, db):
    """Las mutaciones (POST) tambien deben tener standard_fields poblado."""
    resp = logged_in_superadmin.post("/api/auth/logout")
    assert resp.status_code == 200
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == "/api/auth/logout")
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    assert fila.standard_fields is not None
    sf = json.loads(fila.standard_fields)
    assert sf["endpoint"]["type"] == "post"
    assert sf["api"]["metod"] == "POST"


# ── Redacción de cuerpos sensibles (auditoría de seguridad 2026-08-18) ────────


def _ultima_fila(db, path):
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path == path)
        .order_by(models.AuditLog.id.desc())
        .first()
    )


def test_change_password_no_persiste_el_body(client, logged_in_superadmin, db):
    """POST /api/auth/change-password lleva contraseñas en el body: la fila de
    auditoría debe quedar sin request_body_summary."""
    resp = logged_in_superadmin.post(
        "/api/auth/change-password",
        json={"current_password": "SuperClaveTest123!", "new_password": "OtraClaveNueva2026!"},
    )
    assert resp.status_code == 200
    _flush()

    fila = _ultima_fila(db, "/api/auth/change-password")
    assert fila is not None
    assert fila.request_body_summary is None


def test_login_con_trailing_slash_no_persiste_password(client, db):
    """POST /api/auth/login/ (con barra final) no debe dejar la contraseña en la
    auditoría. Con el catch-all del SPA registrado (frontend/dist presente), la
    ruta responde 405; sin dist, 404 — en ambos casos el middleware captura el
    body ANTES de esa respuesta: la ruta debe quedar excluida tras normalizar
    la barra final."""
    resp = client.post(
        "/api/auth/login/",
        json={"identificador": "nadie", "password": "ClaveMuySecreta123!"},
    )
    assert resp.status_code in (404, 405)
    _flush()

    fila = _ultima_fila(db, "/api/auth/login/")
    assert fila is not None
    assert fila.request_body_summary is None


def test_alta_de_usuario_redacta_password(client, logged_in_superadmin, db):
    """POST /api/users con password explícito: la fila de auditoría debe tener
    el campo redactado (***), nunca el valor en claro."""
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "nuevo.empleado",
            "email": "nuevo@test.com",
            "full_name": "Nuevo Empleado",
            "role": "usuario",
            "password": "ClaveMuySecreta123!",
        },
    )
    assert resp.status_code == 201
    _flush()

    fila = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.endpoint_path.like("/api/users%"))
        .order_by(models.AuditLog.id.desc())
        .first()
    )
    assert fila is not None
    body = fila.request_body_summary or ""
    assert "ClaveMuySecreta123!" not in body
    assert '"password":"***"' in body
