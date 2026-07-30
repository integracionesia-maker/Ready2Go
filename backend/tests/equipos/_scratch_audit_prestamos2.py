"""Prueba temporal de auditoria (2) -- se borra al terminar."""

import pytest

import seed_equipos
from datetime import date

from .conftest import logueado, usuario_con


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


@pytest.fixture
def ana(inventario, db):
    return usuario_con(db, username="ana.ruiz")


def test_borrador_con_fecha_esperada_pasada_se_marca_atrasado(inventario, ana):
    """HIPOTESIS: un borrador (todavia sin confirmar, sin folio, sin equipo
    fisicamente entregado) con `fecha_regreso_esperada` en el pasado se marca
    `atrasado=true` igual que un prestamo activo, porque `calcular_atraso` no
    distingue `borrador` de `prestado` en su primera rama (usa `hoy()` siempre
    que no haya `fecha_regreso_real` y el estado no sea terminal).
    """
    cliente = logueado("ana.ruiz")
    resp = cliente.post(
        "/api/loans/",
        json={"fecha_regreso_esperada": "2020-01-01"},  # muy en el pasado
    )
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    print("borrador recien creado:", cuerpo["estado"], "atrasado=", cuerpo["atrasado"], "dias_atraso=", cuerpo["dias_atraso"])
    assert cuerpo["estado"] == "borrador"
    assert cuerpo["atrasado"] is True
    assert cuerpo["dias_atraso"] > 0


def test_no_hay_validacion_de_orden_entre_fechas(inventario, ana):
    """HIPOTESIS: no hay validacion de que fecha_regreso_esperada sea >=
    fecha_entrega (ni >= hoy) al crear/actualizar un prestamo."""
    cliente = logueado("ana.ruiz")
    resp = cliente.post(
        "/api/loans/",
        json={"fecha_entrega": "2026-08-15", "fecha_regreso_esperada": "2026-08-01"},
    )
    print("crear con regreso ANTES de entrega ->", resp.status_code, resp.json())
    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["fecha_entrega"] == "2026-08-15"
    assert cuerpo["fecha_regreso_esperada"] == "2026-08-01"
