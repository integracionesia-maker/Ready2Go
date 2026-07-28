"""Fallo al resolver permisos = 503, jamas 403 y jamas 401.

Leccion Bruckner CRITICO-2 (§10.6 del plan): si la base falla y el motor
devuelve `{}`, todos los endpoints contestan 403. El cliente lee 403 como
politica, no como averia; en el mejor caso esconde toda la interfaz y en el peor
desloguea. El 503 con `codigo: PERMISOS_NO_DISPONIBLES` es lo unico que le dice
"esto es infraestructura, reintenta, no cierres la sesion".
"""

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import rbac
from app.errores import PermisosNoDisponibles

from .conftest import PASSWORD_MKT, logueado, romper_tabla_grants, usuario_con


def test_motor_levanta_permisos_no_disponibles_si_falla_la_base(db, catalogo):
    user = usuario_con(db, username="victima", role="colaborador_mkt")
    romper_tabla_grants(db)

    with pytest.raises(PermisosNoDisponibles):
        rbac.permisos_efectivos(db, user)


def test_permisos_no_disponibles_es_503_con_codigo_estable(db, catalogo):
    """El endpoint que en condiciones normales daria 403 por falta de permiso
    tiene que dar 503 cuando lo que falla es la base. Esa es la distincion
    completa de esta prueba: mismo usuario, mismo endpoint, distinto motivo."""
    usuario_con(db, username="admin.rbac", role="admin")

    # Sano: admin no tiene usuarios:gestionar_roles -> 403 SIN_PERMISO.
    cliente = logueado("admin.rbac")
    sano = cliente.get("/api/roles/")
    assert sano.status_code == 403
    assert sano.json()["codigo"] == "SIN_PERMISO"

    # Roto: la resolucion falla antes de decidir. 503, no 403.
    romper_tabla_grants(db)
    roto = cliente.get("/api/roles/")
    assert roto.status_code == 503, roto.text
    assert roto.json()["codigo"] == "PERMISOS_NO_DISPONIBLES"
    assert roto.status_code not in (401, 403)


def test_el_503_no_invalida_la_sesion(db, catalogo):
    """No desloguear: la cookie sigue siendo valida despues del 503."""
    usuario_con(db, username="admin.sesion", role="admin")
    cliente = logueado("admin.sesion")

    romper_tabla_grants(db)
    assert cliente.get("/api/roles/").status_code == 503

    # /me sigue resolviendo identidad; lo unico roto son los permisos.
    me = cliente.get("/api/auth/me")
    assert me.status_code == 503
    assert me.json()["codigo"] == "PERMISOS_NO_DISPONIBLES"
    assert cliente.cookies.get("access_token")


def test_error_de_sqlalchemy_arbitrario_tambien_da_503(db, catalogo, monkeypatch):
    """No solo "tabla ausente": cualquier `SQLAlchemyError` del camino de
    resolucion tiene que salir como 503, no escaparse como 500."""
    user = usuario_con(db, username="otro", role="colaborador_mkt")

    def _explota(*_args, **_kwargs):
        raise SQLAlchemyError("base caida")

    monkeypatch.setattr(rbac, "_aditivos_concedidos", _explota)

    with pytest.raises(PermisosNoDisponibles):
        rbac.permisos_efectivos(db, user)


def test_superadmin_pasa_aunque_la_base_de_grants_este_rota(db, catalogo):
    """El bypass del superadmin no consulta la base: si todo se cae, sigue
    habiendo alguien que pueda entrar a mirar."""
    usuario_con(db, username="root2", role="superadmin")
    cliente = logueado("root2")
    romper_tabla_grants(db)

    resp = cliente.get("/api/roles/")
    assert resp.status_code == 200


def test_sobre_de_error_tiene_la_forma_del_contrato(db, catalogo):
    usuario_con(db, username="admin.forma", role="admin")
    cuerpo = logueado("admin.forma").get("/api/roles/").json()
    assert set(cuerpo) == {"detail", "codigo"}
    assert isinstance(cuerpo["detail"], str)
    assert cuerpo["detail"]


def test_sin_sesion_sigue_siendo_401_no_503(client):
    """El 503 es para fallo de infraestructura. Falta de cookie sigue siendo
    401: confundirlos haria que un no autenticado parezca una caida."""
    assert client.get("/api/roles/").status_code == 401
