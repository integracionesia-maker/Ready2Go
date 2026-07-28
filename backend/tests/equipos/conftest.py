"""Fixtures del modulo Control de Equipos.

Hereda del conftest raiz: DB de prueba aislada y `_clean_state` autouse que hace
drop_all + create_all antes de cada prueba, asi que las tablas de Equipos
existen vacias.
"""

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from app import crud_rbac
from app.models_equipos import (
    Empresa,
    EstadoOperativo,
    EstadoPrestamo,
    Equipment,
    Loan,
    LoanItem,
)

from ..conftest import make_user

RAIZ_REPO = Path(__file__).resolve().parents[3]
DIR_FIXTURES = RAIZ_REPO / "docs" / "contratos" / "fixtures"

PASSWORD_MKT = "MarketingClave123!"

# Congelado a proposito en toda prueba que mire atraso: el fixture del contrato
# dice `atrasado: false` con fecha de regreso 2026-07-30. Sin congelar, la
# guardia se pondria roja sola el 31 de julio y nadie sabria por que.
HOY_CONGELADO = date(2026, 7, 28)


@pytest.fixture
def fixture_equipos() -> dict:
    return json.loads((DIR_FIXTURES / "equipos.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture_prestamo_demo() -> dict:
    return json.loads((DIR_FIXTURES / "prestamo_demo.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture_empresas() -> list:
    return json.loads((DIR_FIXTURES / "empresas.json").read_text(encoding="utf-8"))


@pytest.fixture
def catalogo(db):
    crud_rbac.sembrar_catalogo(db)
    return db


def usuario_con(db, *, username, role="colaborador_mkt", aditivos=()):
    user = make_user(db, username=username, password=PASSWORD_MKT, role=role)
    for nombre in aditivos:
        crud_rbac.conceder(db, user.id, nombre, granted_by=None)
    return user


def logueado(username, password=PASSWORD_MKT):
    from fastapi.testclient import TestClient

    from app.main import app

    cliente = TestClient(app)
    cliente.post("/api/auth/login", json={"identificador": username, "password": password})
    return cliente


def crear_equipo(
    db,
    *,
    nombre="Equipo de prueba",
    codigo=None,
    categoria="Categoria de prueba",
    estado_operativo=EstadoOperativo.ACTIVO.value,
    accesorios=None,
    **extra,
) -> Equipment:
    equipo = Equipment(
        nombre=nombre,
        codigo=codigo,
        categoria=categoria,
        estado_operativo=estado_operativo,
        accesorios_tipicos=json.dumps(accesorios or [], ensure_ascii=False),
        **extra,
    )
    db.add(equipo)
    db.commit()
    db.refresh(equipo)
    return equipo


def crear_prestamo(
    db,
    *,
    estado=EstadoPrestamo.PRESTADO.value,
    responsable=None,
    folio=None,
    fecha_regreso_esperada=None,
    **extra,
) -> Loan:
    prestamo = Loan(
        folio=folio,
        responsable_user_id=responsable.id if responsable else None,
        responsable_nombre=responsable.full_name if responsable else "Responsable Prueba",
        responsable_email=responsable.email if responsable else None,
        estado=estado,
        fecha_entrega=date(2026, 7, 25),
        fecha_regreso_esperada=fecha_regreso_esperada,
        **extra,
    )
    db.add(prestamo)
    db.commit()
    db.refresh(prestamo)
    return prestamo


def agregar_item(db, prestamo: Loan, equipo: Equipment, *, devuelto_at: datetime | None = None) -> LoanItem:
    item = LoanItem(loan_id=prestamo.id, equipment_id=equipo.id, devuelto_at=devuelto_at)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def crear_empresa(db, *, razon_social="EMPRESA DE PRUEBA SA DE CV", **extra) -> Empresa:
    empresa = Empresa(razon_social=razon_social, **extra)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa
