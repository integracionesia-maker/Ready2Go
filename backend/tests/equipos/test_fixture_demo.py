"""Guardia de contrato del payload: `GET /api/loans/{id}` del prestamo demo
tiene que ser **identico** a `docs/contratos/fixtures/prestamo_demo.json`.

Ese archivo es el criterio de aceptacion del payload —no la tabla SQL— y el
cliente alimenta sus mocks con la misma copia literal. Hay una prueba de igualdad
de cada lado: si las dos comparan contra el mismo archivo, la integracion no
puede sorprender a nadie.

**La fecha va fijada al 2026-07-28.** El fixture dice `atrasado: false` con fecha
de regreso 2026-07-30: sin fijarla, esta guardia se pondria roja sola el 31 de
julio y nadie sabria por que.

Se fija parcheando `tz.hoy` y no con `freeze_time`: freezegun sustituye
`datetime.date` por su propia clase, y con eso FastAPI deja de poder analizar los
parametros de fecha de otras rutas ("Invalid args for response field").
"""

import json
from datetime import date

import pytest

import seed_equipos
import seed_prestamo_demo
from app import security, tz

from .conftest import DIR_FIXTURES, logueado

HOY_FIJO = date(2026, 7, 28)
PASSWORD_DEMO = "ClaveDemoPrueba123!"

# Claves de metadato del fixture: describen el archivo, no el payload. El
# servidor jamas las emite.
METADATOS = ("_nota",)


def _fixture_limpio() -> dict:
    crudo = json.loads((DIR_FIXTURES / "prestamo_demo.json").read_text(encoding="utf-8"))
    return {k: v for k, v in crudo.items() if k not in METADATOS}


@pytest.fixture
def hoy_fijo(monkeypatch):
    monkeypatch.setattr(tz, "hoy", lambda: HOY_FIJO)
    return HOY_FIJO


@pytest.fixture
def demo(db, catalogo):
    """El prestamo del fixture, sembrado tal cual: ids fijos incluidos.

    A los usuarios del demo se les fija una contraseña conocida: el seed genera
    una temporal aleatoria (correcto para produccion) y sin esto no habria forma
    de entrar por HTTP a comprobar el payload de verdad.
    """
    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    prestamo = seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)

    from app.models import User

    for datos in seed_prestamo_demo.USUARIOS_DEMO:
        usuario = db.get(User, datos["id"])
        usuario.password_hash = security.hash_password(PASSWORD_DEMO)
        usuario.must_change_password = False
    db.commit()
    return prestamo


def test_el_payload_es_identico_al_fixture(demo, hoy_fijo):
    """LA prueba de S7: por HTTP, campo por campo, sin excepciones."""
    respuesta = logueado("ana.ruiz", PASSWORD_DEMO).get(f"/api/loans/{demo.id}")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == _fixture_limpio()


def test_la_aprobadora_ve_el_mismo_payload(demo, hoy_fijo):
    """Melisa entra por `ver_global`, no por participacion: el payload no puede
    cambiar segun quien lo pida."""
    respuesta = logueado("melisa", PASSWORD_DEMO).get(f"/api/loans/{demo.id}")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == _fixture_limpio()


def test_by_folio_devuelve_el_mismo_payload(demo, hoy_fijo):
    fixture = _fixture_limpio()
    respuesta = logueado("ana.ruiz", PASSWORD_DEMO).get(f"/api/loans/by-folio/{fixture['folio']}")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == fixture


def test_el_fixture_no_trae_campos_que_el_servidor_no_emita(demo, hoy_fijo):
    """Al reves de la prueba anterior: si el fixture gana un campo, hay que
    implementarlo, no ignorarlo."""
    emitido = set(logueado("ana.ruiz", PASSWORD_DEMO).get(f"/api/loans/{demo.id}").json())
    assert set(_fixture_limpio()) == emitido


def test_el_servidor_no_emite_columnas_internas(demo, hoy_fijo):
    """El fixture es cerrado. `created_by_user_id`, `is_deleted` y compañia
    existen en la tabla y **no** van en el payload: agregarlas rompe la guardia de
    los dos lados a la vez."""
    payload = logueado("ana.ruiz", PASSWORD_DEMO).get(f"/api/loans/{demo.id}").json()

    for prohibido in (
        "created_by_user_id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "deleted_by_user_id",
        "responsable_user_id",
        "entregado_por_user_id",
    ):
        assert prohibido not in payload, prohibido


def test_los_ids_del_fixture_se_reproducen(demo):
    fixture = _fixture_limpio()
    assert demo.id == fixture["id"]
    assert demo.folio == fixture["folio"]
    assert [i.id for i in demo.items] == [i["id"] for i in fixture["items"]]
    assert demo.items[0].equipment_id == fixture["items"][0]["equipment_id"]


def test_los_ids_de_media_del_fixture_se_reproducen(demo, hoy_fijo):
    payload = logueado("ana.ruiz", PASSWORD_DEMO).get(f"/api/loans/{demo.id}").json()
    fixture = _fixture_limpio()

    assert payload["firmas"] == fixture["firmas"]
    assert payload["items"][0]["media"] == fixture["items"][0]["media"]


def test_el_evento_dice_el_texto_congelado(demo):
    fixture = _fixture_limpio()
    assert demo.eventos[0].id == fixture["eventos"][0]["id"]
    assert demo.eventos[0].detalle == fixture["eventos"][0]["detalle"]
    assert demo.eventos[0].tipo == fixture["eventos"][0]["tipo"]


def test_la_fecha_del_evento_sale_con_offset_de_cdmx(demo):
    """`2026-07-25T10:14:00-06:00`. Con `+00:00` o con microsegundos, la
    comparacion literal contra el fixture falla."""
    fixture = _fixture_limpio()
    assert tz.iso_cdmx(demo.eventos[0].created_at) == fixture["eventos"][0]["created_at"]


def test_el_atraso_del_fixture_depende_de_la_fecha_fijada(demo, monkeypatch):
    """Documenta por que esta guardia fija la fecha: el 5 de agosto, el mismo
    prestamo ya esta atrasado y el fixture diria lo contrario."""
    from app import crud_loans

    sesion = _sesion(demo)

    monkeypatch.setattr(tz, "hoy", lambda: HOY_FIJO)
    assert crud_loans.serializar_detalle(sesion, demo)["atrasado"] is False

    monkeypatch.setattr(tz, "hoy", lambda: date(2026, 8, 5))
    vencido = crud_loans.serializar_detalle(sesion, demo)
    assert vencido["atrasado"] is True
    assert vencido["dias_atraso"] == 6


def _sesion(instancia):
    from sqlalchemy import inspect

    return inspect(instancia).session
