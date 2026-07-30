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
DIR_FIXTURES = RAIZ_REPO / "docs" / "equipos" / "contratos" / "fixtures"

PASSWORD_MKT = "MarketingClave123!"

# Congelado a proposito en toda prueba que mire atraso: el fixture del contrato
# dice `atrasado: false` con fecha de regreso 2026-07-30. Sin congelar, la
# guardia se pondria roja sola el 31 de julio y nadie sabria por que.
HOY_CONGELADO = date(2026, 7, 28)


@pytest.fixture(autouse=True)
def _uploads_aislados(tmp_path, monkeypatch):
    """Las pruebas escriben media y PDFs en un temporal, nunca en `uploads/`.

    No es solo higiene. `uploads/` vive dentro del repo, que a su vez esta en una
    carpeta sincronizada con Drive: cada archivo que una prueba escribia ahi
    disparaba una sincronizacion. Con 348 archivos acumulados, la suite de
    aprobacion paso de segundos a **dos horas y media**. Ademas dejaba basura en
    el arbol de trabajo entre corridas.
    """
    import seed_prestamo_demo
    from app import crud_loans, media_manager

    monkeypatch.setattr(media_manager, "DIRECTORIO", tmp_path / "equipos")
    monkeypatch.setattr(crud_loans, "DIRECTORIO_RESPONSIVAS", tmp_path / "responsivas")
    monkeypatch.setattr(seed_prestamo_demo, "DIRECTORIO_MEDIA", tmp_path / "seed_equipos")
    monkeypatch.setattr(
        seed_prestamo_demo, "DIRECTORIO_RESPONSIVAS", tmp_path / "seed_responsivas"
    )
    yield


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


def png_bytes(ancho: int = 40, alto: int = 30, color=(200, 200, 200)) -> bytes:
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (ancho, alto), color).save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes(ancho: int = 40, alto: int = 30, color=(180, 180, 180)) -> bytes:
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (ancho, alto), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def subir(cliente, loan_id: int, kind: str, loan_item_id: int | None = None, contenido=None):
    """POST multipart a /api/loans/{id}/media, como lo hace el wizard."""
    datos = {"kind": kind}
    if loan_item_id is not None:
        datos["loan_item_id"] = str(loan_item_id)
    return cliente.post(
        f"/api/loans/{loan_id}/media",
        data=datos,
        files={"file": ("foto.png", contenido if contenido is not None else png_bytes(), "image/png")},
    )


def crear_empresa(db, *, razon_social="EMPRESA DE PRUEBA SA DE CV", **extra) -> Empresa:
    empresa = Empresa(razon_social=razon_social, **extra)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa
