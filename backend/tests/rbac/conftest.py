"""Fixtures del RBAC aditivo.

Hereda del conftest raiz (DB de prueba aislada, `_clean_state` autouse que hace
drop_all + create_all antes de cada prueba). Como `_clean_state` deja las tablas
de RBAC vacias, cualquier prueba que dependa del catalogo sembrado pide
`catalogo`.
"""

import json
from pathlib import Path

import pytest

from app import crud_rbac, security
from app.models_rbac import UserRoleGrant

from ..conftest import make_user

RAIZ_REPO = Path(__file__).resolve().parents[3]
CONTRATO_PERMISOS = RAIZ_REPO / "docs" / "equipos" / "contratos" / "permisos_catalogo.json"
CONTRATO_AUTH_ME = RAIZ_REPO / "docs" / "equipos" / "contratos" / "auth_me.json"

PASSWORD_MKT = "MarketingClave123!"


@pytest.fixture
def catalogo(db):
    """Catalogo materializado en la base, como despues de correr la migracion."""
    crud_rbac.sembrar_catalogo(db)
    return db


@pytest.fixture
def contrato_permisos() -> dict:
    return json.loads(CONTRATO_PERMISOS.read_text(encoding="utf-8"))


@pytest.fixture
def contrato_auth_me() -> dict:
    return json.loads(CONTRATO_AUTH_ME.read_text(encoding="utf-8"))


def usuario_con(db, *, username, role, aditivos=()):
    """Usuario con rol base y cero o mas paquetes aditivos concedidos."""
    user = make_user(db, username=username, password=PASSWORD_MKT, role=role)
    for nombre in aditivos:
        crud_rbac.conceder(db, user.id, nombre, granted_by=None)
    return user


@pytest.fixture
def colaborador(db, catalogo):
    return usuario_con(db, username="emily", role="colaborador_mkt")


@pytest.fixture
def melisa(db, catalogo):
    """Rol base colaborador_mkt + aditivo APROBADOR_EQUIPO: la asignacion
    acordada el 27/07 y la que retrata docs/contratos/auth_me.json."""
    return usuario_con(
        db, username="melisa", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",)
    )


def logueado(username, password=PASSWORD_MKT):
    from fastapi.testclient import TestClient

    from app.main import app

    cliente = TestClient(app)
    cliente.post("/api/auth/login", json={"identificador": username, "password": password})
    return cliente


def romper_tabla_grants(db):
    """Simula un fallo real de base: la tabla de concesiones desaparece.

    Es mas honesto que parchear la funcion: ejercita el `except SQLAlchemyError`
    del motor con el error que de verdad levanta SQLite.
    """
    from sqlalchemy import text

    db.execute(text("DROP TABLE user_role_grants"))
    db.commit()


__all__ = [
    "PASSWORD_MKT",
    "usuario_con",
    "logueado",
    "romper_tabla_grants",
    "UserRoleGrant",
    "security",
]
