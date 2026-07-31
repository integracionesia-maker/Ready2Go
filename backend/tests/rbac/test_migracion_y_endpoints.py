"""Migracion idempotente, `usuarios_con_permiso()`, modo legacy y los endpoints
de roles del contrato §7.
"""

import pytest

from app import crud_rbac, rbac, rbac_catalog
from app.models_rbac import Role, RolePermission, UserRoleGrant

from .conftest import PASSWORD_MKT, logueado, usuario_con
from ..conftest import PASSWORD_SUPERADMIN


# ── Migracion ───────────────────────────────────────────────────────────────


def test_sembrar_catalogo_dos_veces_no_falla_ni_duplica(db):
    primera = crud_rbac.sembrar_catalogo(db)
    assert primera["roles_nuevos"] == len(rbac_catalog.PAQUETES)
    assert primera["permisos_nuevos"] > 0

    roles_1 = db.query(Role).count()
    permisos_1 = db.query(RolePermission).count()

    segunda = crud_rbac.sembrar_catalogo(db)
    assert segunda == {
        "roles_nuevos": 0,
        "roles_actualizados": 0,
        "permisos_nuevos": 0,
        "permisos_borrados": 0,
    }
    assert db.query(Role).count() == roles_1
    assert db.query(RolePermission).count() == permisos_1


def test_sembrar_reconcilia_filas_que_ya_no_estan_en_el_catalogo(db, catalogo):
    """Quitar una accion del catalogo tiene que borrar su fila. Sin esto, la
    fila sobrevive y un dia alguien la lee como permiso vigente."""
    db.add(RolePermission(role_name="creador", modulo="presupuestos", accion="exportar"))
    db.commit()

    conteo = crud_rbac.sembrar_catalogo(db)
    assert conteo["permisos_borrados"] == 1
    assert (
        db.query(RolePermission)
        .filter(
            RolePermission.role_name == "creador",
            RolePermission.accion == "exportar",
        )
        .first()
        is None
    )


def test_sembrar_no_revive_un_paquete_apagado(db, catalogo):
    """Apagar un paquete es decision de operacion. Re-sembrar no la revierte."""
    db.query(Role).filter(Role.name == "AUDITOR").update({"is_active": False})
    db.commit()
    crud_rbac.sembrar_catalogo(db)
    assert db.query(Role).filter(Role.name == "AUDITOR").first().is_active is False


def test_sembrar_no_toca_usuarios_ni_concesiones(db, catalogo):
    user = usuario_con(db, username="intacto", role="colaborador_mkt", aditivos=("AUDITOR",))
    rol_antes = user.role

    crud_rbac.sembrar_catalogo(db)
    db.refresh(user)

    assert user.role == rol_antes
    assert db.query(UserRoleGrant).filter(UserRoleGrant.user_id == user.id).count() == 1


def test_catalogo_invalido_no_se_siembra(db, monkeypatch):
    """Sembrar un catalogo roto dejaria filas huerfanas que nadie vuelve a
    mirar. Mejor reventar en la migracion."""
    monkeypatch.setitem(
        rbac_catalog.PAQUETES,
        "AUDITOR",
        {"kind": "aditivo", "descripcion": "x", "permisos": {"modulo_fantasma": ("ver",)}},
    )
    with pytest.raises(ValueError, match="Catalogo de permisos invalido"):
        crud_rbac.sembrar_catalogo(db)


# ── Concesiones ─────────────────────────────────────────────────────────────


def test_conceder_es_idempotente(db, catalogo):
    user = usuario_con(db, username="dos.veces", role="colaborador_mkt")
    crud_rbac.conceder(db, user.id, "AUDITOR", granted_by=None)
    crud_rbac.conceder(db, user.id, "AUDITOR", granted_by=None)
    assert db.query(UserRoleGrant).filter(UserRoleGrant.user_id == user.id).count() == 1


def test_revocar_devuelve_false_si_no_habia_nada(db, catalogo):
    user = usuario_con(db, username="sin.nada", role="colaborador_mkt")
    assert crud_rbac.revocar(db, user.id, "AUDITOR") is False


# ── usuarios_con_permiso ────────────────────────────────────────────────────


def test_usuarios_con_permiso_resuelve_aprobadores_desde_la_base(db, catalogo):
    """§7 del plan: los destinatarios de correo salen de la base por rol, nunca
    de una constante con el correo de Melisa adentro."""
    mel = usuario_con(db, username="mel", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",))
    usuario_con(db, username="emily", role="colaborador_mkt")
    usuario_con(db, username="admin.x", role="admin")

    aprobadores = crud_rbac.usuarios_con_permiso(
        db, "equipos_aprobacion", "autorizar_entrega", incluir_superadmin=False
    )
    # admin ahora incluye equipos_aprobacion, asi que admin.x tambien cuenta
    assert sorted(u.username for u in aprobadores) == ["admin.x", "mel"]
    assert mel.id in {u.id for u in aprobadores}


def test_usuarios_con_permiso_incluye_superadmin_por_default(db, catalogo):
    """Para la pregunta "quien puede hacer esto" el superadmin cuenta. Para
    destinatarios de correo no, y por eso existe la bandera."""
    usuario_con(db, username="root", role="superadmin")
    usuario_con(db, username="mel2", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",))

    con = crud_rbac.usuarios_con_permiso(db, "equipos_aprobacion", "autorizar_entrega")
    sin = crud_rbac.usuarios_con_permiso(
        db, "equipos_aprobacion", "autorizar_entrega", incluir_superadmin=False
    )
    assert {u.username for u in con} == {"root", "mel2"}
    assert {u.username for u in sin} == {"mel2"}


def test_usuarios_con_permiso_ignora_inactivos(db, catalogo):
    from ..conftest import make_user

    user = make_user(
        db, username="baja", password=PASSWORD_MKT, role="colaborador_mkt", is_active=False
    )
    crud_rbac.conceder(db, user.id, "APROBADOR_EQUIPO", granted_by=None)

    assert crud_rbac.usuarios_con_permiso(db, "equipos_aprobacion", "cerrar_incidencia") == []


def test_usuarios_con_permiso_ignora_grant_de_paquete_apagado(db, catalogo):
    usuario_con(db, username="mel3", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",))
    db.query(Role).filter(Role.name == "APROBADOR_EQUIPO").update({"is_active": False})
    db.commit()

    assert (
        crud_rbac.usuarios_con_permiso(
            db, "equipos_aprobacion", "autorizar_entrega", incluir_superadmin=False
        )
        == []
    )


def test_usuarios_con_permiso_del_piso_son_todos(db, catalogo):
    usuario_con(db, username="a1", role="creador")
    usuario_con(db, username="a2", role="colaborador_mkt")
    assert len(crud_rbac.usuarios_con_permiso(db, "inicio", "ver")) == 2


# ── Modo legacy (rollback §13) ──────────────────────────────────────────────


def test_modo_legacy_ignora_los_aditivos(db, catalogo, monkeypatch):
    """`RBAC_MODO=legacy` deja las 3 tablas pero no las consulta. Consecuencia
    que hay que conocer antes de activarlo: la aprobacion de equipos queda solo
    en manos del superadmin."""
    user = usuario_con(db, username="mel.legacy", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",))
    assert "equipos_aprobacion" in rbac.permisos_efectivos(db, user)

    monkeypatch.setenv("RBAC_MODO", "legacy")
    assert rbac.modo_rbac() == rbac.MODO_LEGACY
    assert "equipos_aprobacion" not in rbac.permisos_efectivos(db, user)


def test_modo_legacy_no_rompe_el_rol_base(db, catalogo, monkeypatch):
    monkeypatch.setenv("RBAC_MODO", "legacy")
    user = usuario_con(db, username="adm.legacy", role="admin")
    permisos = rbac.permisos_efectivos(db, user)
    assert "presupuestos" in permisos
    assert "inicio" in permisos


def test_modo_legacy_sobrevive_sin_las_tablas(db, catalogo, monkeypatch):
    """El rollback duro es DROP de las 3 tablas. En legacy la app sigue de pie."""
    from .conftest import romper_tabla_grants

    monkeypatch.setenv("RBAC_MODO", "legacy")
    user = usuario_con(db, username="mel.drop", role="colaborador_mkt")
    romper_tabla_grants(db)
    assert "equipos_prestamos" in rbac.permisos_efectivos(db, user)


def test_valor_desconocido_de_rbac_modo_cae_en_aditivo(monkeypatch):
    """Un typo en la variable de entorno no debe apagar los aditivos en
    silencio: solo la palabra exacta `legacy` activa el rollback."""
    monkeypatch.setenv("RBAC_MODO", "legacyy")
    assert rbac.modo_rbac() == rbac.MODO_ADITIVO


# ── Endpoints del contrato §7 ───────────────────────────────────────────────


def test_get_roles_lista_el_catalogo_completo(db, catalogo, superadmin_user):
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).get("/api/roles/")
    assert resp.status_code == 200
    nombres = [r["name"] for r in resp.json()]
    assert set(nombres) == set(rbac_catalog.PAQUETES)
    # Orden estable: piso, luego base, luego aditivo.
    kinds = [r["kind"] for r in resp.json()]
    assert kinds == sorted(kinds, key=lambda k: {"piso": 0, "base": 1, "aditivo": 2}[k])


def test_get_roles_prohibido_para_admin(db, catalogo):
    usuario_con(db, username="adm", role="admin")
    resp = logueado("adm").get("/api/roles/")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_conceder_y_revocar_aditivo(db, catalogo, superadmin_user):
    target = usuario_con(db, username="objetivo", role="colaborador_mkt")
    cliente = logueado("superadmin", PASSWORD_SUPERADMIN)

    alta = cliente.post(f"/api/users/{target.id}/roles", json={"role_name": "APROBADOR_EQUIPO"})
    assert alta.status_code == 201, alta.text
    cuerpo = alta.json()
    assert cuerpo["role_base"] == "colaborador_mkt"
    assert [g["role_name"] for g in cuerpo["aditivos"]] == ["APROBADOR_EQUIPO"]
    assert "equipos_aprobacion" in cuerpo["permisos_efectivos"]
    assert "presupuestos" not in cuerpo["permisos_efectivos"]

    baja = cliente.delete(f"/api/users/{target.id}/roles/APROBADOR_EQUIPO")
    assert baja.status_code == 200

    ver = cliente.get(f"/api/users/{target.id}/roles").json()
    assert ver["aditivos"] == []


def test_no_se_puede_conceder_un_paquete_base_como_aditivo(db, catalogo, superadmin_user):
    """El rol base vive en `users.role` y se cambia por PUT /api/users/{id}.
    Meterlo por la puerta de los aditivos duplicaria la fuente de verdad."""
    target = usuario_con(db, username="obj2", role="creador")
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).post(
        f"/api/users/{target.id}/roles", json={"role_name": "admin"}
    )
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_paquete_inexistente_es_404(db, catalogo, superadmin_user):
    target = usuario_con(db, username="obj3", role="creador")
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).post(
        f"/api/users/{target.id}/roles", json={"role_name": "NO_EXISTE"}
    )
    assert resp.status_code == 404


def test_superadmin_es_inmutable_tambien_para_aditivos(db, catalogo, superadmin_user):
    """Regla vigente del proyecto: ningun endpoint modifica la cuenta
    superadmin. Un aditivo no le agregaria nada (ya tiene todo por bypass) pero
    si dejaria rastro de modificacion sobre una cuenta declarada inmutable."""
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).post(
        f"/api/users/{superadmin_user.id}/roles", json={"role_name": "AUDITOR"}
    )
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_revocar_lo_que_no_estaba_concedido_es_404(db, catalogo, superadmin_user):
    target = usuario_con(db, username="obj4", role="creador")
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).delete(
        f"/api/users/{target.id}/roles/AUDITOR"
    )
    assert resp.status_code == 404


def test_usuario_inexistente_es_404(db, catalogo, superadmin_user):
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).get("/api/users/99999/roles")
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_gestionar_roles_no_lo_tiene_nadie_mas_que_superadmin(db, catalogo):
    """R4 vigente: la gestion de usuarios es exclusiva de superadmin. El RBAC
    nuevo no la afloja."""
    for nombre in rbac_catalog.PAQUETES:
        if nombre == "superadmin":
            continue
        permisos = rbac_catalog.permisos_de_paquete(nombre)
        assert "gestionar_roles" not in permisos.get("usuarios", set()), nombre
        assert "gestionar" not in permisos.get("usuarios", set()), nombre
