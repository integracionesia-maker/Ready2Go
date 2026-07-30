"""Rol base "usuario": piso-only, sin permisos propios. Los modulos se abren
solo via paquetes aditivos concedidos explicitamente."""

from app import rbac

from .conftest import usuario_con, logueado


def test_usuario_role_creation(db, catalogo):
    user = usuario_con(db, username="pelon", role="usuario")
    permisos = rbac.permisos_efectivos(db, user)
    assert permisos == {"inicio": {"ver"}, "perfil": {"ver", "editar_propio"}}


def test_usuario_no_acceso_presupuestos(db, catalogo):
    usuario_con(db, username="pelon2", role="usuario")
    cliente = logueado("pelon2")

    aprobar = cliente.post("/api/tickets/1/aprobar")
    assert aprobar.status_code == 403

    dashboard = cliente.get("/api/dashboard/summary")
    assert dashboard.status_code == 403


def test_usuario_no_acceso_equipos(db, catalogo):
    usuario_con(db, username="pelon3", role="usuario")
    cliente = logueado("pelon3")

    resp = cliente.get("/api/equipment/")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_aditivo_abre_equipos_a_usuario(db, catalogo):
    user = usuario_con(db, username="pelon4", role="usuario", aditivos=("APROBADOR_EQUIPO",))

    permisos = rbac.permisos_efectivos(db, user)
    assert "equipos_aprobacion" in permisos
    assert "presupuestos" not in permisos

    cliente = logueado("pelon4")
    dashboard = cliente.get("/api/dashboard/summary")
    assert dashboard.status_code == 403


def test_admin_no_gestiona_usuarios(db, catalogo, logged_in_admin, creador_user):
    listar = logged_in_admin.get("/api/users/")
    assert listar.status_code == 403

    ver_roles = logged_in_admin.get(f"/api/users/{creador_user.id}/roles")
    assert ver_roles.status_code == 403

    conceder = logged_in_admin.post(
        f"/api/users/{creador_user.id}/roles", json={"role_name": "AUDITOR"}
    )
    assert conceder.status_code == 403


def test_superadmin_gestiona_usuarios(db, catalogo, logged_in_superadmin, creador_user):
    listar = logged_in_superadmin.get("/api/users/")
    assert listar.status_code == 200

    ver_roles = logged_in_superadmin.get(f"/api/users/{creador_user.id}/roles")
    assert ver_roles.status_code == 200
