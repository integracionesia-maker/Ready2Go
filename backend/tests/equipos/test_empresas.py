"""Razones sociales (contrato §6)."""

from app.models_equipos import Empresa

from .conftest import crear_empresa, logueado, usuario_con
from ..conftest import PASSWORD_SUPERADMIN


def test_listar_solo_pide_sesion(db, catalogo):
    """El wizard de prestamo necesita la lista para llenar un `<select>`. Pedir
    `usuarios:gestionar` ahi dejaria el formulario vacio para todo marketing."""
    crear_empresa(db, razon_social="MERCASYSTEM SA DE CV")
    usuario_con(db, username="emily")

    resp = logueado("emily").get("/api/empresas/")
    assert resp.status_code == 200
    assert [e["razon_social"] for e in resp.json()] == ["MERCASYSTEM SA DE CV"]


def test_listar_sin_sesion_es_401(client):
    assert client.get("/api/empresas/").status_code == 401


def test_la_respuesta_tiene_la_forma_del_fixture(db, catalogo, fixture_empresas):
    """`fixtures/empresas.json` es un arreglo pelado, no `{items, total}`. El
    fixture de equipos si trae el sobre: los fixtures distinguen entre listado
    paginado y catalogo chico. Se sigue el fixture."""
    import seed_equipos

    seed_equipos.sembrar_empresas(db, verbose=False)
    usuario_con(db, username="emily")

    cuerpo = logueado("emily").get("/api/empresas/").json()
    assert isinstance(cuerpo, list)

    campos = {"id", "razon_social", "direccion", "ciudad", "rfc", "is_active"}
    for obtenida, esperada in zip(cuerpo, fixture_empresas):
        assert set(obtenida) == campos
        for campo in campos:
            assert obtenida[campo] == esperada[campo], campo


def test_crear_exige_usuarios_gestionar(db, catalogo):
    usuario_con(db, username="emily")
    resp = logueado("emily").post("/api/empresas/", json={"razon_social": "NUEVA SA DE CV"})
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_admin_tampoco_puede_crear(db, catalogo):
    """R4 vigente: `usuarios:*` es exclusivo del superadmin."""
    usuario_con(db, username="adm", role="admin")
    assert logueado("adm").post("/api/empresas/", json={"razon_social": "X SA"}).status_code == 403


def test_superadmin_crea_y_edita(db, catalogo, superadmin_user):
    cliente = logueado("superadmin", PASSWORD_SUPERADMIN)

    alta = cliente.post(
        "/api/empresas/",
        json={
            "razon_social": "SERVICIOS CORPORATIVOS QUANTUM DE OCCIDENTE, S.C.",
            "direccion": "Belisario Dominguez No. 30 Col. Centro",
            "ciudad": "Morelia, Michoacan",
            "rfc": "SCQ1212149P0",
        },
    )
    assert alta.status_code == 201, alta.text
    empresa_id = alta.json()["id"]
    assert alta.json()["rfc"] == "SCQ1212149P0"

    edicion = cliente.put(f"/api/empresas/{empresa_id}", json={"ciudad": "Morelia"})
    assert edicion.status_code == 200
    assert edicion.json()["ciudad"] == "Morelia"
    # Un PUT parcial no borra lo que no viene.
    assert edicion.json()["rfc"] == "SCQ1212149P0"


def test_razon_social_duplicada_es_409(db, catalogo, superadmin_user):
    cliente = logueado("superadmin", PASSWORD_SUPERADMIN)
    cliente.post("/api/empresas/", json={"razon_social": "MERCASYSTEM SA DE CV"})
    repetida = cliente.post("/api/empresas/", json={"razon_social": "MERCASYSTEM SA DE CV"})
    assert repetida.status_code == 409
    assert set(repetida.json()) == {"detail", "codigo"}


def test_editar_una_que_no_existe_es_404(db, catalogo, superadmin_user):
    resp = logueado("superadmin", PASSWORD_SUPERADMIN).put(
        "/api/empresas/9999", json={"ciudad": "X"}
    )
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_solo_activas_filtra(db, catalogo):
    crear_empresa(db, razon_social="VIGENTE SA DE CV")
    crear_empresa(db, razon_social="BAJA SA DE CV", is_active=False)
    usuario_con(db, username="emily")
    cliente = logueado("emily")

    assert len(cliente.get("/api/empresas/").json()) == 2
    activas = cliente.get("/api/empresas/", params={"solo_activas": True}).json()
    assert [e["razon_social"] for e in activas] == ["VIGENTE SA DE CV"]


def test_la_razon_social_es_unica_en_la_base(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    crear_empresa(db, razon_social="UNICA SA DE CV")
    db.add(Empresa(razon_social="UNICA SA DE CV"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
