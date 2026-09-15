"""Modo "periodo único" del Dashboard: detección de cuándo un rango de fechas
es exactamente un mes o un año de calendario (`crud.detectar_periodo_unico`),
el endpoint que arma la comparación contra el periodo anterior equivalente
(`/api/dashboard/period-comparison`), y el desglose de gastos generales por
marca (`/api/dashboard/general-expenses-by-brand`) que reemplaza a "por mes"
en ese modo."""
from datetime import date

from app import crud

from .conftest import make_ticket, make_brand

PDF = ("comprobante.pdf", b"%PDF-1.4\n% comprobante de prueba\n", "application/pdf")


# ── Helpers ────────────────────────────────────────────────────────────────


def _crear_general(cli, brand_id, *, amount=100.0):
    return cli.post(
        "/api/general-expenses/",
        data={"brand_id": str(brand_id), "amount": str(amount), "description": "general"},
        files={"file": PDF},
    )


def _set_upload_date(db, obj, iso_datetime):
    from datetime import datetime as dt

    obj.upload_date = dt.fromisoformat(iso_datetime)
    db.commit()


# ── detectar_periodo_unico (unitario, sin DB) ───────────────────────────────


def test_este_mes_hasta_hoy_es_tipo_mes():
    # Marzo (31 días) parcial hasta el día 30 -> compara contra febrero (28
    # días en 2026, no bisiesto): clava el clamp de "día no existe".
    r = crud.detectar_periodo_unico(date(2026, 3, 1), date(2026, 3, 30))
    assert r == ("mes", date(2026, 2, 1), date(2026, 2, 28))


def test_mes_cerrado_compara_contra_mes_completo():
    r = crud.detectar_periodo_unico(date(2026, 8, 1), date(2026, 8, 31))
    assert r == ("mes", date(2026, 7, 1), date(2026, 7, 31))


def test_enero_no_necesita_clamp():
    r = crud.detectar_periodo_unico(date(2026, 1, 1), date(2026, 1, 15))
    assert r == ("mes", date(2025, 12, 1), date(2025, 12, 15))


def test_anio_a_medio_ano_compara_mismo_corte_ano_pasado():
    r = crud.detectar_periodo_unico(date(2026, 1, 1), date(2026, 6, 15))
    assert r == ("anio", date(2025, 1, 1), date(2025, 6, 15))


def test_anio_completo_compara_ano_completo():
    r = crud.detectar_periodo_unico(date(2026, 1, 1), date(2026, 12, 31))
    assert r == ("anio", date(2025, 1, 1), date(2025, 12, 31))


def test_29_febrero_bisiesto_cae_a_28_en_ano_no_bisiesto():
    r = crud.detectar_periodo_unico(date(2028, 1, 1), date(2028, 2, 29))
    assert r == ("anio", date(2027, 1, 1), date(2027, 2, 28))


def test_ultimos_3_meses_no_es_periodo_unico():
    r = crud.detectar_periodo_unico(date(2026, 6, 15), date(2026, 9, 15))
    assert r is None


def test_rango_multi_mes_arbitrario_no_es_periodo_unico():
    r = crud.detectar_periodo_unico(date(2026, 3, 1), date(2026, 5, 31))
    assert r is None


def test_todo_sin_fechas_no_es_periodo_unico():
    assert crud.detectar_periodo_unico(None, None) is None


# ── /api/dashboard/period-comparison ────────────────────────────────────────


def test_rango_multimes_da_is_single_period_false(logged_in_admin):
    r = logged_in_admin.get(
        "/api/dashboard/period-comparison",
        params={"start_date": "2026-03-01", "end_date": "2026-05-31"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_single_period"] is False
    assert body["anterior"] is None


def test_mes_cerrado_da_comparacion_correcta(logged_in_admin, db, creator_a, brand_a):
    ticket_agosto = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    _set_upload_date(db, ticket_agosto, "2026-08-10T09:00:00")
    ticket_julio = make_ticket(db, creator=creator_a, brand=brand_a, amount=400, status="aprobado")
    _set_upload_date(db, ticket_julio, "2026-07-10T09:00:00")

    r = logged_in_admin.get(
        "/api/dashboard/period-comparison",
        params={"start_date": "2026-08-01", "end_date": "2026-08-31"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_single_period"] is True
    assert body["tipo"] == "mes"
    assert body["label_comparacion"] == "el mes pasado"
    assert body["actual"]["total_spent"] == 1000.0
    assert body["anterior"]["total_spent"] == 400.0


def test_sin_periodo_anterior_anterior_es_none_cuando_no_aplica(logged_in_admin):
    r = logged_in_admin.get("/api/dashboard/period-comparison")
    assert r.status_code == 200
    assert r.json()["is_single_period"] is False


def test_no_autenticado_401(client):
    assert client.get("/api/dashboard/period-comparison").status_code == 401


def test_creador_403(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/period-comparison").status_code == 403


def test_marketing_admin_200(logged_in_marketing_admin):
    assert logged_in_marketing_admin.get("/api/dashboard/period-comparison").status_code == 200


# ── /api/dashboard/general-expenses-by-brand ────────────────────────────────


def test_suma_por_marca(logged_in_admin, brand_a, db):
    brand_b = make_brand(db, name="Marca B")
    _crear_general(logged_in_admin, brand_a.id, amount=500)
    _crear_general(logged_in_admin, brand_a.id, amount=300)
    _crear_general(logged_in_admin, brand_b.id, amount=200)

    r = logged_in_admin.get("/api/dashboard/general-expenses-by-brand")
    assert r.status_code == 200
    por_marca = {b["brand_name"]: b["total_spent"] for b in r.json()}
    assert por_marca[brand_a.name] == 800.0
    assert por_marca["Marca B"] == 200.0


def test_marca_sin_gasto_aparece_en_cero(logged_in_admin, brand_a):
    r = logged_in_admin.get("/api/dashboard/general-expenses-by-brand")
    assert r.status_code == 200
    por_marca = {b["brand_name"]: b["total_spent"] for b in r.json()}
    assert por_marca[brand_a.name] == 0.0


def test_excluye_borrados_soft(logged_in_admin, brand_a):
    ge = _crear_general(logged_in_admin, brand_a.id, amount=9999)
    logged_in_admin.post(f"/api/general-expenses/{ge.json()['id']}/soft-delete")

    r = logged_in_admin.get("/api/dashboard/general-expenses-by-brand")
    por_marca = {b["brand_name"]: b["total_spent"] for b in r.json()}
    assert por_marca[brand_a.name] == 0.0


def test_filtra_por_rango_de_fechas(logged_in_admin, brand_a):
    _crear_general(logged_in_admin, brand_a.id, amount=500)
    hoy = date.today().isoformat()
    r_dentro = logged_in_admin.get(
        "/api/dashboard/general-expenses-by-brand", params={"start_date": hoy, "end_date": hoy}
    )
    por_marca = {b["brand_name"]: b["total_spent"] for b in r_dentro.json()}
    assert por_marca[brand_a.name] == 500.0

    r_fuera = logged_in_admin.get(
        "/api/dashboard/general-expenses-by-brand",
        params={"start_date": "2020-01-01", "end_date": "2020-01-31"},
    )
    por_marca_fuera = {b["brand_name"]: b["total_spent"] for b in r_fuera.json()}
    assert por_marca_fuera[brand_a.name] == 0.0


def test_no_autenticado_401_brand(client):
    assert client.get("/api/dashboard/general-expenses-by-brand").status_code == 401


def test_creador_403_brand(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/general-expenses-by-brand").status_code == 403
