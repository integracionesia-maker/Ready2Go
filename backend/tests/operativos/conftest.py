"""Fixtures del módulo Gastos Operativos. Reusa las fixtures del conftest raíz
(`db`, `logged_in_admin`, `logged_in_superadmin`, `logged_in_marketing_admin`,
etc.) y agrega el rol nuevo `operativo`, que el raíz no conoce.
"""

import pytest
from fastapi.testclient import TestClient

from app import models, security
from app.main import app

PASSWORD_OPERATIVO = "OperativoClaveTest123!"


@pytest.fixture
def operativo_user(db):
    user = models.User(
        username="op.user",
        email="op.user@test.com",
        password_hash=security.hash_password(PASSWORD_OPERATIVO),
        full_name="Usuario Operativo",
        role="operativo",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def cli_operativo(operativo_user):
    """Cliente independiente (cookie jar propio) logueado como `operativo`."""
    c = TestClient(app)
    c.post("/api/auth/login", json={"identificador": "op.user", "password": PASSWORD_OPERATIVO})
    return c
