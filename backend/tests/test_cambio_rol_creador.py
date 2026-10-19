"""Cambio de rol <-> perfil de creador (PUT /api/users/{id}, PATCH /estado,
POST /api/creators/).

Regla: un usuario con rol 'creador' siempre tiene su perfil de creador. Al
promover a alguien (admin -> creador) el perfil se crea o reactiva solo; al
sacarlo del rol se desactiva (no se borra) y conserva el enlace para
reactivarlo si vuelve."""

from app import models

from .conftest import make_creator, make_user


def _perfil(db, creator_id):
    db.expire_all()
    return db.get(models.Creator, creator_id)


def _usuario(db, user_id):
    db.expire_all()
    return db.get(models.User, user_id)


def _admin_adair(db):
    return make_user(
        db, username="adair.garcia", password="Clave123456!", role="admin", full_name="Adair García"
    )


def test_admin_a_creador_crea_y_enlaza_el_perfil(logged_in_superadmin, db):
    adair = _admin_adair(db)
    assert adair.creator_id is None

    resp = logged_in_superadmin.put(f"/api/users/{adair.id}", json={"role": "creador"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "creador"
    assert body["creador_accion"] == "creado"
    assert body["creador_nombre"] == "Adair García"
    assert body["creator_id"] is not None

    perfil = _perfil(db, body["creator_id"])
    assert perfil.name == "Adair García"
    assert perfil.is_active is True
    assert _usuario(db, adair.id).creator_id == perfil.id

    # Ya es seleccionable como beneficiario de Equipos (activos, con user_id).
    lista = logged_in_superadmin.get("/api/creators/?active_only=true").json()
    fila = next(c for c in lista if c["id"] == perfil.id)
    assert fila["user_id"] == adair.id
    assert fila["email"] == adair.email


def test_el_frontend_manda_creator_id_null_y_no_pasa_nada_malo(logged_in_superadmin, db):
    adair = _admin_adair(db)
    resp = logged_in_superadmin.put(
        f"/api/users/{adair.id}",
        json={"full_name": "Adair García", "email": adair.email, "role": "creador", "creator_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["creador_accion"] == "creado"


def test_creador_a_admin_desactiva_el_perfil_y_conserva_el_enlace(
    logged_in_superadmin, db, creador_user, creator_a
):
    resp = logged_in_superadmin.put(f"/api/users/{creador_user.id}", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["creador_accion"] == "desactivado"

    assert _perfil(db, creator_a.id).is_active is False
    assert _usuario(db, creador_user.id).creator_id == creator_a.id

    activos = logged_in_superadmin.get("/api/creators/?active_only=true").json()
    assert creator_a.id not in {c["id"] for c in activos}


def test_ida_y_vuelta_reutiliza_el_mismo_perfil(logged_in_superadmin, db):
    adair = _admin_adair(db)
    creator_id = logged_in_superadmin.put(
        f"/api/users/{adair.id}", json={"role": "creador"}
    ).json()["creator_id"]

    logged_in_superadmin.put(f"/api/users/{adair.id}", json={"role": "admin", "creator_id": None})
    assert _perfil(db, creator_id).is_active is False

    back = logged_in_superadmin.put(f"/api/users/{adair.id}", json={"role": "creador"}).json()
    assert back["creador_accion"] == "reactivado"
    assert back["creator_id"] == creator_id
    assert _perfil(db, creator_id).is_active is True
    assert db.query(models.Creator).filter(models.Creator.name == "Adair García").count() == 1


def test_editar_nombre_de_un_creador_no_reactiva_su_perfil_desactivado(
    logged_in_superadmin, db, creador_user, creator_a
):
    creator_a.is_active = False
    db.commit()
    resp = logged_in_superadmin.put(f"/api/users/{creador_user.id}", json={"full_name": "Otro Nombre"})
    assert resp.status_code == 200
    assert resp.json()["creador_accion"] is None
    assert _perfil(db, creator_a.id).is_active is False


def test_promocion_vinculando_a_un_creador_existente(logged_in_superadmin, db, creator_b):
    adair = _admin_adair(db)
    resp = logged_in_superadmin.put(
        f"/api/users/{adair.id}", json={"role": "creador", "creator_id": creator_b.id}
    )
    assert resp.status_code == 200
    assert resp.json()["creador_accion"] == "vinculado"
    assert _usuario(db, adair.id).creator_id == creator_b.id


def test_no_se_puede_vincular_un_creador_ya_enlazado_a_otro_usuario(
    logged_in_superadmin, db, creador_user, creator_a
):
    adair = _admin_adair(db)
    resp = logged_in_superadmin.put(
        f"/api/users/{adair.id}", json={"role": "creador", "creator_id": creator_a.id}
    )
    assert resp.status_code == 409
    # Nada quedó a medias: sigue siendo admin y sin perfil.
    assert _usuario(db, adair.id).role == "admin"
    assert _usuario(db, adair.id).creator_id is None


def test_creator_id_exige_rol_creador(logged_in_superadmin, db, creator_b):
    adair = _admin_adair(db)
    resp = logged_in_superadmin.put(f"/api/users/{adair.id}", json={"creator_id": creator_b.id})
    assert resp.status_code == 400


def test_creator_id_inexistente_da_404(logged_in_superadmin, db):
    adair = _admin_adair(db)
    resp = logged_in_superadmin.put(f"/api/users/{adair.id}", json={"role": "creador", "creator_id": 9999})
    assert resp.status_code == 404
    assert _usuario(db, adair.id).role == "admin"


def test_creador_sin_perfil_se_repara_al_editarlo(logged_in_superadmin, db):
    roto = make_user(db, username="roto", password="Clave123456!", role="creador", full_name="Usuario Roto")
    assert roto.creator_id is None
    resp = logged_in_superadmin.put(f"/api/users/{roto.id}", json={"full_name": "Usuario Roto"})
    assert resp.status_code == 200
    assert resp.json()["creador_accion"] == "creado"
    assert _usuario(db, roto.id).creator_id is not None


def test_cambio_entre_roles_no_creador_no_toca_perfiles(logged_in_superadmin, db):
    antes = db.query(models.Creator).count()
    adair = _admin_adair(db)
    resp = logged_in_superadmin.put(f"/api/users/{adair.id}", json={"role": "marketing_admin"})
    assert resp.status_code == 200
    assert resp.json()["creador_accion"] is None
    assert db.query(models.Creator).count() == antes


# ── Desactivar / reactivar la cuenta ────────────────────────────────────────


def test_desactivar_la_cuenta_de_un_creador_desactiva_su_perfil(
    logged_in_superadmin, db, creador_user, creator_a
):
    r = logged_in_superadmin.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": False})
    assert r.status_code == 200
    assert _perfil(db, creator_a.id).is_active is False

    r = logged_in_superadmin.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": True})
    assert r.status_code == 200
    assert _perfil(db, creator_a.id).is_active is True


def test_reactivar_una_cuenta_que_ya_no_es_creador_no_revive_el_perfil(
    logged_in_superadmin, db, creador_user, creator_a
):
    logged_in_superadmin.put(f"/api/users/{creador_user.id}", json={"role": "admin"})
    logged_in_superadmin.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": False})
    logged_in_superadmin.patch(f"/api/users/{creador_user.id}/estado", json={"is_active": True})
    assert _perfil(db, creator_a.id).is_active is False


# ── POST /api/creators/: sin creadores huérfanos ───────────────────────────


def test_post_creator_con_usuario_repetido_no_deja_un_creador_huerfano(logged_in_admin, db, admin_user):
    antes = db.query(models.Creator).count()
    resp = logged_in_admin.post(
        "/api/creators/",
        json={"name": "Duplicado", "username": admin_user.username, "email": "nuevo@test.com"},
    )
    assert resp.status_code == 409
    assert db.query(models.Creator).count() == antes


def test_post_creator_crea_creador_y_usuario_juntos(logged_in_admin, db):
    resp = logged_in_admin.post(
        "/api/creators/",
        json={"name": "Nueva Persona", "username": "nueva.persona", "email": "nueva.persona@test.com"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["temporary_password"]
    user = db.query(models.User).filter(models.User.username == "nueva.persona").one()
    assert user.role == "creador" and user.creator_id == body["id"]
