"""El catalogo en codigo tiene que ser identico al del contrato congelado.

`docs/contratos/permisos_catalogo.json` es contrato: el cliente pinta botones
segun esas claves. Renombrar una accion en el servidor sin cambiarla alla no
produce ningun error visible — simplemente desaparecen botones. Por eso la
comparacion es una prueba y no un comentario.
"""

from app import crud_rbac, rbac_catalog


def _normalizar_permisos(bruto) -> dict[str, set[str]] | str:
    if bruto == "*":
        return "*"
    return {modulo: set(acciones) for modulo, acciones in bruto.items()}


def test_modulos_y_acciones_identicos_al_contrato(contrato_permisos):
    del_contrato = {
        modulo: set(acciones) for modulo, acciones in contrato_permisos["modulos"].items()
    }
    del_codigo = {modulo: set(acciones) for modulo, acciones in rbac_catalog.MODULOS.items()}
    assert del_codigo == del_contrato


def test_paquetes_identicos_al_contrato(contrato_permisos):
    paquetes_contrato = contrato_permisos["paquetes"]
    assert set(rbac_catalog.PAQUETES) == set(paquetes_contrato)

    for nombre, definicion in paquetes_contrato.items():
        assert rbac_catalog.kind_de(nombre) == definicion["kind"], nombre

        esperado = _normalizar_permisos(definicion["permisos"])
        if esperado == "*":
            assert rbac_catalog.permisos_de_paquete(nombre) == rbac_catalog.catalogo_completo()
            continue
        assert rbac_catalog.permisos_de_paquete(nombre) == esperado, nombre


def test_catalogo_es_internamente_consistente():
    """Ningun paquete lista un (modulo, accion) que no exista."""
    assert rbac_catalog.validar_catalogo() == []


def test_a_json_devuelve_listas_en_orden_del_catalogo():
    """El contrato transporta listas, no sets. El orden es el del catalogo para
    que dos respuestas iguales sean byte-identicas y las guardias de contrato no
    dependan del hash de Python."""
    permisos = rbac_catalog.permisos_de_paquete("admin")
    salida = rbac_catalog.a_json(permisos)

    assert all(isinstance(v, list) for v in salida.values())
    assert salida["equipos_prestamos"] == [
        "solicitar",
        "ver_propios",
        "ver_global",
        "registrar_devolucion",
        "exportar",
    ]


def test_materializacion_en_base_coincide_con_el_catalogo(db, catalogo):
    """Las tablas `roles`/`role_permissions` son copia del catalogo. Si divergen,
    la pantalla de administracion muestra un mundo y el motor decide con otro."""
    en_db = crud_rbac.catalogo_en_db(db)
    en_codigo = {
        nombre: rbac_catalog.permisos_de_paquete(nombre) for nombre in rbac_catalog.PAQUETES
    }
    # Un paquete sin permisos no genera filas; se comparan solo los que si tienen.
    en_codigo = {n: p for n, p in en_codigo.items() if p}
    assert en_db == en_codigo


def test_permisos_de_melisa_iguales_al_fixture_del_contrato(db, melisa, contrato_auth_me):
    """`docs/contratos/auth_me.json` retrata a la aprobadora real: rol base
    colaborador_mkt + APROBADOR_EQUIPO. Si el motor no reproduce ese bloque
    exacto, el cliente que mockea contra el fixture pinta otra cosa."""
    from app import rbac

    obtenido = rbac_catalog.a_json(rbac.permisos_efectivos(db, melisa))
    assert obtenido == contrato_auth_me["permisos"]


def test_endpoint_me_devuelve_los_permisos_del_contrato(db, melisa, contrato_auth_me):
    from .conftest import logueado

    cuerpo = logueado("melisa").get("/api/auth/me").json()
    assert cuerpo["role"] == contrato_auth_me["role"]
    assert cuerpo["permisos"] == contrato_auth_me["permisos"]


def test_me_de_un_creador_no_trae_nada_de_equipos(db, catalogo, creador_user):
    from .conftest import logueado
    from ..conftest import PASSWORD_CREADOR

    cuerpo = logueado("creador.a", PASSWORD_CREADOR).get("/api/auth/me").json()
    assert set(cuerpo["permisos"]) == {"inicio", "perfil", "presupuestos"}


def test_login_no_resuelve_permisos_los_deja_en_default(db, catalogo, colaborador):
    """El contrato dice `default {}`: solo /me los llena. Resolver RBAC en login
    y refresh seria trabajo por request que nadie usa."""
    from .conftest import PASSWORD_MKT
    from ..conftest import login
    from fastapi.testclient import TestClient
    from app.main import app

    cliente = TestClient(app)
    cuerpo = login(cliente, "emily", PASSWORD_MKT).json()
    assert cuerpo["user"]["permisos"] == {}
