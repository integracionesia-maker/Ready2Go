"""Paquete aditivo ADMIN_USUARIOS: administrar cuentas sin ser superadmin.

Lo que estas pruebas blindan:
- abre SOLO `usuarios:administrar_cuentas` y `usuarios:ver_roles` (nada de
  `gestionar`, `gestionar_roles`, auditoria, empresas ni notificaciones);
- solo existe para el rol base `admin` (no se concede a otros ni sobrevive a un
  cambio de rol);
- el delegado opera solo sobre cuentas POR DEBAJO de admin: no toca superadmin,
  ni otros admin, ni al titular de la firma de Equipos, y no promueve a nadie a
  admin;
- no concede ni revoca paquetes (solo los ve).
"""

import pytest
from fastapi.testclient import TestClient

from app import crud_rbac, models, rbac, rbac_catalog
from app.main import app

from .conftest import login, make_creator, make_user

PASSWORD_DELEGADO = "DelegadoClave123!"


@pytest.fixture
def catalogo_sembrado(db):
    crud_rbac.sembrar_catalogo(db)


@pytest.fixture
def delegado_user(db, catalogo_sembrado):
    u = make_user(db, username="delegado", password=PASSWORD_DELEGADO, role="admin", full_name="Delegado")
    crud_rbac.conceder(db, u.id, "ADMIN_USUARIOS", granted_by=None)
    return u


@pytest.fixture
def logged_in_delegado(delegado_user):
    c = TestClient(app)
    assert login(c, "delegado", PASSWORD_DELEGADO).status_code == 200
    return c


def _recargar(db, user_id):
    db.expire_all()
    return db.get(models.User, user_id)


# ── El paquete en el catalogo ───────────────────────────────────────────────


def test_el_paquete_abre_solo_dos_acciones_de_usuarios():
    assert rbac_catalog.kind_de("ADMIN_USUARIOS") == rbac_catalog.KIND_ADITIVO
    assert rbac_catalog.permisos_de_paquete("ADMIN_USUARIOS") == {
        "usuarios": {"administrar_cuentas", "ver_roles"}
    }


def test_ningun_otro_paquete_trae_las_acciones_nuevas():
    for nombre in rbac_catalog.PAQUETES:
        if nombre in ("superadmin", "ADMIN_USUARIOS"):
            continue
        usuarios = rbac_catalog.permisos_de_paquete(nombre).get("usuarios", set())
        assert not usuarios & {"administrar_cuentas", "ver_roles"}, nombre


def test_el_delegado_no_gana_permisos_fuera_de_usuarios(db, delegado_user):
    efectivos = rbac.permisos_efectivos(db, delegado_user)
    admin_solo = rbac.permisos_efectivos(db, make_user(db, username="otro.admin", password="x" * 12, role="admin"))
    extra = {m: a - admin_solo.get(m, set()) for m, a in efectivos.items()}
    extra = {m: a for m, a in extra.items() if a}
    assert extra == {"usuarios": {"administrar_cuentas", "ver_roles"}}
    assert "gestionar" not in efectivos.get("usuarios", set())
    assert "gestionar_roles" not in efectivos.get("usuarios", set())
    assert "auditoria" not in efectivos


def test_me_del_delegado_muestra_el_paquete_y_los_permisos(logged_in_delegado):
    me = logged_in_delegado.get("/api/auth/me").json()
    assert "ADMIN_USUARIOS" in me["paquetes_aditivos"]
    assert set(me["permisos"]["usuarios"]) == {"administrar_cuentas", "ver_roles"}


# ── Quien puede tenerlo ─────────────────────────────────────────────────────


def test_superadmin_lo_concede_a_un_admin(logged_in_superadmin, db, catalogo_sembrado):
    admin = make_user(db, username="admin.nuevo", password="Clave123456!", role="admin")
    resp = logged_in_superadmin.post(f"/api/users/{admin.id}/roles", json={"role_name": "ADMIN_USUARIOS"})
    assert resp.status_code == 201
    assert [g["role_name"] for g in resp.json()["aditivos"]] == ["ADMIN_USUARIOS"]


@pytest.mark.parametrize("rol", ["creador", "marketing_admin", "marketing_basico", "usuario"])
def test_no_se_concede_a_quien_no_es_admin(logged_in_superadmin, db, catalogo_sembrado, rol):
    otro = make_user(db, username=f"u.{rol}", password="Clave123456!", role=rol)
    resp = logged_in_superadmin.post(f"/api/users/{otro.id}/roles", json={"role_name": "ADMIN_USUARIOS"})
    assert resp.status_code == 400
    assert crud_rbac.listar_grants(db, otro.id) == []


def test_una_concesion_colgada_no_da_poder_si_ya_no_es_admin(db, catalogo_sembrado):
    """Aunque la fila exista (puesta a mano o de antes de un cambio de rol), el
    motor la ignora si el usuario ya no tiene rol base admin."""
    creador = make_user(db, username="colgado", password=PASSWORD_DELEGADO, role="creador")
    crud_rbac.conceder(db, creador.id, "ADMIN_USUARIOS", granted_by=None)

    assert "administrar_cuentas" not in rbac.permisos_efectivos(db, creador).get("usuarios", set())
    assert rbac.paquetes_aditivos_de(db, creador) == []
    c = TestClient(app)
    login(c, "colgado", PASSWORD_DELEGADO)
    assert c.get("/api/users/").status_code == 403


def test_sacar_a_un_admin_de_ese_rol_le_revoca_el_paquete(
    logged_in_superadmin, db, delegado_user
):
    resp = logged_in_superadmin.put(f"/api/users/{delegado_user.id}", json={"role": "marketing_admin"})
    assert resp.status_code == 200
    assert crud_rbac.listar_grants(db, delegado_user.id) == []

    # y si vuelve a ser admin no revive solo
    logged_in_superadmin.put(f"/api/users/{delegado_user.id}", json={"role": "admin"})
    assert crud_rbac.listar_grants(db, delegado_user.id) == []


def test_el_delegado_no_concede_ni_revoca_paquetes(
    logged_in_delegado, db, delegado_user, creador_user
):
    r = logged_in_delegado.post(f"/api/users/{creador_user.id}/roles", json={"role_name": "AUDITOR"})
    assert r.status_code == 403
    r = logged_in_delegado.post(f"/api/users/{delegado_user.id}/roles", json={"role_name": "APROBADOR_EQUIPO"})
    assert r.status_code == 403
    r = logged_in_delegado.delete(f"/api/users/{delegado_user.id}/roles/ADMIN_USUARIOS")
    assert r.status_code == 403
    assert [g.role_name for g in crud_rbac.listar_grants(db, delegado_user.id)] == ["ADMIN_USUARIOS"]


# ── Lo que SI puede hacer ───────────────────────────────────────────────────


def test_lista_usuarios_sin_ver_superadmins(logged_in_delegado, superadmin_user, creador_user):
    resp = logged_in_delegado.get("/api/users/")
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()["items"]}
    assert creador_user.username in usernames
    assert superadmin_user.username not in usernames


def test_no_puede_pedir_la_lista_de_superadmins(logged_in_delegado, superadmin_user):
    assert logged_in_delegado.get("/api/users/?role=superadmin").status_code == 403
    assert logged_in_delegado.get(f"/api/users/{superadmin_user.id}").status_code == 404


def test_crea_un_usuario_de_rol_bajo(logged_in_delegado):
    resp = logged_in_delegado.post(
        "/api/users/",
        json={
            "username": "nuevo.mkt",
            "email": "nuevo.mkt@test.com",
            "full_name": "Nuevo Mkt",
            "role": "marketing_basico",
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 201


def test_no_crea_admins(logged_in_delegado):
    resp = logged_in_delegado.post(
        "/api/users/",
        json={
            "username": "nuevo.admin",
            "email": "nuevo.admin@test.com",
            "full_name": "Nuevo Admin",
            "role": "admin",
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 403


def test_cambia_el_rol_de_un_usuario_de_rol_bajo(logged_in_delegado, db, creador_user, creator_a):
    resp = logged_in_delegado.put(f"/api/users/{creador_user.id}", json={"role": "marketing_basico"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "marketing_basico"
    # La regla creador<->perfil sigue valiendo para el delegado.
    assert resp.json()["creador_accion"] == "desactivado"


def test_no_promueve_a_nadie_a_admin(logged_in_delegado, db, creador_user):
    resp = logged_in_delegado.put(f"/api/users/{creador_user.id}", json={"role": "admin"})
    assert resp.status_code == 403
    assert _recargar(db, creador_user.id).role == "creador"


def test_resetea_la_contrasena_de_un_creador(logged_in_delegado, creador_user):
    resp = logged_in_delegado.post(f"/api/users/{creador_user.id}/reset-password")
    assert resp.status_code == 200
    assert resp.json()["temporary_password"]


def test_desactiva_y_reactiva_y_desbloquea(logged_in_delegado, db, creador_user):
    assert logged_in_delegado.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": False}).status_code == 200
    assert logged_in_delegado.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": True}).status_code == 200
    assert logged_in_delegado.post(f"/api/users/{creador_user.id}/unlock").status_code == 200


def test_ve_el_catalogo_de_roles_y_los_paquetes_de_un_usuario(logged_in_delegado, creador_user):
    resp = logged_in_delegado.get("/api/roles/")
    assert resp.status_code == 200
    assert "ADMIN_USUARIOS" in {r["name"] for r in resp.json()}
    assert logged_in_delegado.get(f"/api/users/{creador_user.id}/roles").status_code == 200


def test_no_ve_los_paquetes_de_un_superadmin(logged_in_delegado, superadmin_user):
    assert logged_in_delegado.get(f"/api/users/{superadmin_user.id}/roles").status_code == 404


# ── Lo que NO puede hacer ───────────────────────────────────────────────────


def test_no_toca_a_otros_admins_ni_a_si_mismo(logged_in_delegado, db, delegado_user):
    otro = make_user(db, username="otro.admin2", password="Clave123456!", role="admin")
    for destino in (otro.id, delegado_user.id):
        assert logged_in_delegado.put(f"/api/users/{destino}", json={"full_name": "X"}).status_code == 403
        assert logged_in_delegado.post(f"/api/users/{destino}/reset-password").status_code == 403
        assert logged_in_delegado.post(f"/api/users/{destino}/unlock").status_code == 403
        assert logged_in_delegado.patch(f"/api/users/{destino}/estado", json={"is_active": False}).status_code == 403
    assert _recargar(db, otro.id).full_name != "X"
    assert _recargar(db, otro.id).is_active is True


def test_no_toca_al_superadmin(logged_in_delegado, superadmin_user):
    sid = superadmin_user.id
    assert logged_in_delegado.put(f"/api/users/{sid}", json={"full_name": "X"}).status_code == 403
    assert logged_in_delegado.post(f"/api/users/{sid}/reset-password").status_code == 403
    assert logged_in_delegado.post(f"/api/users/{sid}/reset-password-superadmin").status_code == 403
    assert logged_in_delegado.post(f"/api/users/{sid}/unlock").status_code == 403
    assert logged_in_delegado.patch(f"/api/users/{sid}/estado", json={"is_active": False}).status_code == 403


def test_no_toma_la_cuenta_del_titular_de_la_firma(logged_in_delegado, db, catalogo_sembrado):
    """Resetear su contraseña seria tomar la identidad que firma como aprobador
    en la responsiva: ningun permiso la cubre, solo un superadmin la gestiona."""
    melisa = make_user(db, username="melisa.t", password="Clave123456!", role="marketing_equipos")
    crud_rbac.conceder(db, melisa.id, "TITULAR_FIRMA_EQUIPO", granted_by=None)

    assert logged_in_delegado.post(f"/api/users/{melisa.id}/reset-password").status_code == 403
    assert logged_in_delegado.put(f"/api/users/{melisa.id}", json={"role": "usuario"}).status_code == 403
    assert logged_in_delegado.patch(f"/api/users/{melisa.id}/estado", json={"is_active": False}).status_code == 403


def test_el_superadmin_si_puede_con_todos(logged_in_superadmin, db, delegado_user):
    assert logged_in_superadmin.post(f"/api/users/{delegado_user.id}/reset-password").status_code == 200
    resp = logged_in_superadmin.post(
        "/api/users/",
        json={
            "username": "otro.admin3",
            "email": "otro.admin3@test.com",
            "full_name": "Otro",
            "role": "admin",
            "password": "ClaveValida123!",
        },
    )
    assert resp.status_code == 201


@pytest.mark.parametrize(
    "metodo,ruta,cuerpo",
    [
        ("get", "/api/audit-logs/", None),
        ("get", "/api/audit-logs/stats", None),
        ("get", "/api/notifications/", None),
        ("get", "/api/notifications/config", None),
        ("post", "/api/empresas/", {"razon_social": "Empresa X"}),
    ],
)
def test_sigue_sin_acceso_a_auditoria_notificaciones_y_empresas(
    logged_in_delegado, metodo, ruta, cuerpo
):
    kwargs = {"json": cuerpo} if cuerpo is not None else {}
    assert getattr(logged_in_delegado, metodo)(ruta, **kwargs).status_code == 403


def test_un_admin_sin_el_paquete_sigue_sin_gestionar_usuarios(logged_in_admin, creador_user):
    assert logged_in_admin.get("/api/users/").status_code == 403
    assert logged_in_admin.get("/api/roles/").status_code == 403
    assert logged_in_admin.get(f"/api/users/{creador_user.id}/roles").status_code == 403
