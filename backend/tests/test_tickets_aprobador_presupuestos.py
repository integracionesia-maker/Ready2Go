"""Paquete aditivo APROBADOR_PRESUPUESTOS: excepcion puntual para aprobar,
rechazar y borrar (logico) tickets sin ser admin/superadmin.

Este candado es deliberadamente distinto al del resto del RBAC aditivo (ver
`rbac.require_rol_o_paquete`): NO pasa por `permisos_efectivos`, solo mira la
concesion explicita via `user_role_grants`. La razon (y lo que estas pruebas
existen para blindar) es que `rbac_catalog.py` ya lista "validar_ticket"/
"borrar_ticket" para marketing_presupuestos/marketing_admin sin que
`tickets.py` los deje pasar hoy -- si el candado nuevo usara la union general
de permisos, esos roles colarian por una puerta de atras sin que nadie lo haya
decidido.
"""

from app import crud_rbac


def _upload(client, creator_id, brand_id, amount=100):
    return client.post(
        "/api/tickets/",
        data={"creator_id": str(creator_id), "brand_id": str(brand_id), "amount": str(amount)},
        files={"file": ("comprobante.pdf", b"%PDF-1.4 contenido", "application/pdf")},
    )


def _conceder_aprobador(db, user):
    crud_rbac.sembrar_catalogo(db)
    crud_rbac.conceder(db, user.id, "APROBADOR_PRESUPUESTOS", granted_by=None)


def test_usuario_sin_paquete_no_puede_aprobar(
    logged_in_usuario, logged_in_creador, creator_a, brand_a
):
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id).json()

    resp = logged_in_usuario.post(f"/api/tickets/{ticket['id']}/aprobar")

    assert resp.status_code == 403


def test_usuario_con_paquete_puede_aprobar(
    db, usuario_user, logged_in_usuario, logged_in_creador, creator_a, brand_a
):
    _conceder_aprobador(db, usuario_user)
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id, amount=250).json()

    resp = logged_in_usuario.post(f"/api/tickets/{ticket['id']}/aprobar")

    assert resp.status_code == 200
    assert resp.json()["status"] == "aprobado"


def test_usuario_con_paquete_puede_rechazar(
    db, usuario_user, logged_in_usuario, logged_in_creador, creator_a, brand_a
):
    _conceder_aprobador(db, usuario_user)
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id).json()

    resp = logged_in_usuario.post(
        f"/api/tickets/{ticket['id']}/rechazar", json={"reason": "Comprobante ilegible"}
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "rechazado"


def test_usuario_con_paquete_puede_soft_delete(
    db, usuario_user, logged_in_usuario, logged_in_admin, creator_a, brand_a
):
    _conceder_aprobador(db, usuario_user)
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()

    resp = logged_in_usuario.post(f"/api/tickets/{ticket['id']}/soft-delete")

    assert resp.status_code == 200
    assert resp.json()["is_deleted"] is True


def test_usuario_con_paquete_no_puede_hard_delete(
    db, usuario_user, logged_in_usuario, logged_in_admin, creator_a, brand_a
):
    """El borrado FISICO se queda exclusivo de admin/superadmin a proposito:
    borra archivo y fila sin dejar rastro, a diferencia del soft-delete."""
    _conceder_aprobador(db, usuario_user)
    ticket = _upload(logged_in_admin, creator_a.id, brand_a.id, amount=100).json()

    resp = logged_in_usuario.delete(f"/api/tickets/{ticket['id']}/permanent")

    assert resp.status_code == 403


def test_revocar_paquete_quita_el_permiso(
    db, usuario_user, logged_in_usuario, logged_in_creador, creator_a, brand_a
):
    _conceder_aprobador(db, usuario_user)
    crud_rbac.revocar(db, usuario_user.id, "APROBADOR_PRESUPUESTOS")
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id).json()

    resp = logged_in_usuario.post(f"/api/tickets/{ticket['id']}/aprobar")

    assert resp.status_code == 403


def test_marketing_presupuestos_sin_grant_sigue_sin_poder_aprobar(
    logged_in_marketing_presupuestos, logged_in_creador, creator_a, brand_a
):
    """Regresion: el catalogo ya lista validar_ticket para marketing_presupuestos,
    pero el candado de tickets.py sigue sin reconocerlo (discrepancia
    preexistente, fuera de alcance de este cambio). Confirma que agregar el
    paquete nuevo no abrio esa puerta sin querer."""
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id).json()

    resp = logged_in_marketing_presupuestos.post(f"/api/tickets/{ticket['id']}/aprobar")

    assert resp.status_code == 403


def test_admin_no_necesita_el_paquete(logged_in_admin, logged_in_creador, creator_a, brand_a):
    """Admin sigue pasando por el require_role de siempre, sin depender del
    paquete nuevo en absoluto."""
    ticket = _upload(logged_in_creador, creator_a.id, brand_a.id).json()

    resp = logged_in_admin.post(f"/api/tickets/{ticket['id']}/aprobar")

    assert resp.status_code == 200


def test_usuario_sin_paquete_no_puede_listar_pendientes(logged_in_usuario):
    """Rol base `usuario` no esta en ROLES_CON_TICKETS -- sin el paquete, ni
    siquiera puede ver la cola de Validacion."""
    resp = logged_in_usuario.get("/api/tickets/?status=pendiente")

    assert resp.status_code == 403


def test_usuario_con_paquete_puede_listar_pendientes(
    db, usuario_user, logged_in_usuario, logged_in_creador, creator_a, brand_a
):
    """Regresion del bug real: sin este permiso, aprobar_ticket ya funcionaba
    via API pero la cola de Validacion (GET /api/tickets/?status=pendiente)
    seguia devolviendo 403 para un rol base fuera de ROLES_CON_TICKETS -- la
    UI no tenia nada que mostrar aunque el candado de aprobar ya lo dejara
    pasar."""
    _conceder_aprobador(db, usuario_user)
    _upload(logged_in_creador, creator_a.id, brand_a.id)

    resp = logged_in_usuario.get("/api/tickets/?status=pendiente")

    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_me_expone_paquetes_aditivos_concedidos(db, usuario_user, logged_in_usuario):
    """GET /api/auth/me debe traer el paquete tal cual, no diluido en la union
    de `permisos` -- es lo que el frontend usa para decidir si muestra la
    cola de Validacion (ver puedeValidarTickets en roles.js)."""
    _conceder_aprobador(db, usuario_user)

    resp = logged_in_usuario.get("/api/auth/me")

    assert resp.status_code == 200
    assert resp.json()["paquetes_aditivos"] == ["APROBADOR_PRESUPUESTOS"]


def test_me_sin_paquetes_trae_lista_vacia(logged_in_usuario):
    resp = logged_in_usuario.get("/api/auth/me")

    assert resp.status_code == 200
    assert resp.json()["paquetes_aditivos"] == []
