"""Meta fija de gasto mensual (Dashboard), en dos categorías independientes:
"caja_grande" (generales + operativos) y "caja_chica" (tickets de creadores).
Un mes futuro acepta estimación (propia o sugerida) y muestra 0 gastado; un mes
en curso o pasado se congela (ya no se puede editar) y muestra lo realmente
gastado de esa categoría."""
from datetime import date

from sqlalchemy import text

from app import crud

from .conftest import make_ticket

PDF = ("comprobante.pdf", b"%PDF-1.4\n% comprobante de prueba\n", "application/pdf")


# ── Helpers ────────────────────────────────────────────────────────────────


def _add_months(year: int, month: int, delta: int):
    total = (year * 12 + (month - 1)) + delta
    return total // 12, total % 12 + 1


def _mes_futuro():
    hoy = date.today()
    return _add_months(hoy.year, hoy.month, 1)


def _mes_pasado():
    hoy = date.today()
    return _add_months(hoy.year, hoy.month, -1)


def _set_upload_date(db, obj, iso_datetime):
    from datetime import datetime as dt

    obj.upload_date = dt.fromisoformat(iso_datetime)
    db.commit()


def _crear_rubro(cli, nombre="IA"):
    r = cli.post("/api/rubros/", json={"nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_gasto_operativo(cli, rubro_id, *, amount=100.0, fecha):
    data = {"rubro_id": str(rubro_id), "amount": str(amount), "description": "op", "fecha_gasto": fecha}
    return cli.post("/api/operational-expenses/", data=data, files={"file": PDF})


def _crear_general(cli, brand_id, *, amount=100.0):
    return cli.post(
        "/api/general-expenses/",
        data={"brand_id": str(brand_id), "amount": str(amount), "description": "general"},
        files={"file": PDF},
    )


def _estimates(cli, year):
    return cli.get("/api/dashboard/monthly-estimates", params={"year": year})


def _por_mes(cli, year, month, categoria):
    items = {(e["month"], e["categoria"]): e for e in _estimates(cli, year).json()}
    return items[(month, categoria)]


def _put(cli, year, month, categoria, amount):
    return cli.put(f"/api/dashboard/monthly-estimates/{year}/{month}/{categoria}", json={"amount": amount})


# ── Comportamiento (genérico, ambas categorías) ─────────────────────────────


def test_get_devuelve_24_items_2_por_mes(logged_in_admin):
    items = _estimates(logged_in_admin, 2026).json()
    assert len(items) == 24
    assert {e["categoria"] for e in items} == {"caja_grande", "caja_chica"}


def test_mes_futuro_es_editable_y_spent_cero(logged_in_admin):
    year, month = _mes_futuro()
    for categoria in ("caja_grande", "caja_chica"):
        item = _por_mes(logged_in_admin, year, month, categoria)
        assert item["is_editable"] is True
        assert item["amount"] is None
        assert item["spent"] == 0.0


def test_mes_actual_no_es_editable(logged_in_admin):
    hoy = date.today()
    for categoria in ("caja_grande", "caja_chica"):
        assert _por_mes(logged_in_admin, hoy.year, hoy.month, categoria)["is_editable"] is False


def test_mes_pasado_no_es_editable(logged_in_admin):
    year, month = _mes_pasado()
    for categoria in ("caja_grande", "caja_chica"):
        assert _por_mes(logged_in_admin, year, month, categoria)["is_editable"] is False


def test_put_en_mes_futuro_crea_estimacion(logged_in_admin):
    year, month = _mes_futuro()
    r = _put(logged_in_admin, year, month, "caja_chica", 15000)
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 15000.0
    assert r.json()["categoria"] == "caja_chica"
    assert _por_mes(logged_in_admin, year, month, "caja_chica")["amount"] == 15000.0
    # La otra categoría del mismo mes no se toca.
    assert _por_mes(logged_in_admin, year, month, "caja_grande")["amount"] is None


def test_put_sobrescribe_valor_existente(logged_in_admin):
    year, month = _mes_futuro()
    _put(logged_in_admin, year, month, "caja_grande", 15000)
    r = _put(logged_in_admin, year, month, "caja_grande", 20000)
    assert r.status_code == 200
    assert r.json()["amount"] == 20000.0


def test_put_en_mes_actual_rechaza_409(logged_in_admin):
    hoy = date.today()
    assert _put(logged_in_admin, hoy.year, hoy.month, "caja_grande", 1000).status_code == 409
    assert _put(logged_in_admin, hoy.year, hoy.month, "caja_chica", 1000).status_code == 409


def test_put_en_mes_pasado_rechaza_409(logged_in_admin):
    year, month = _mes_pasado()
    assert _put(logged_in_admin, year, month, "caja_chica", 1000).status_code == 409


def test_put_monto_invalido_rechaza_422(logged_in_admin):
    year, month = _mes_futuro()
    assert _put(logged_in_admin, year, month, "caja_chica", 0).status_code == 422
    assert _put(logged_in_admin, year, month, "caja_chica", -100).status_code == 422


def test_put_categoria_invalida_rechaza_400(logged_in_admin):
    year, month = _mes_futuro()
    r = _put(logged_in_admin, year, month, "caja_mediana", 1000)
    assert r.status_code == 400


# ── caja_grande: gastos generales + operativos ──────────────────────────────


def test_caja_grande_suma_generales_y_operativos(logged_in_admin, brand_a):
    hoy = date.today()
    _crear_general(logged_in_admin, brand_a.id, amount=500)
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto_operativo(logged_in_admin, rubro_id, amount=250, fecha=f"{hoy.year:04d}-{hoy.month:02d}-10")

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_grande")
    assert item["spent"] == 750.0


def test_caja_grande_ignora_tickets(logged_in_admin, db, creator_a, brand_a):
    hoy = date.today()
    ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=99999, status="aprobado")
    _set_upload_date(db, ticket, f"{hoy.year:04d}-{hoy.month:02d}-05T09:00:00")

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_grande")
    assert item["spent"] == 0.0


def test_caja_grande_excluye_borrados_soft(logged_in_admin, brand_a):
    hoy = date.today()
    ge = _crear_general(logged_in_admin, brand_a.id, amount=9999)
    logged_in_admin.post(f"/api/general-expenses/{ge.json()['id']}/soft-delete")

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_grande")
    assert item["spent"] == 0.0


# ── caja_chica: tickets aprobados de creadores ──────────────────────────────


def test_caja_chica_suma_tickets_aprobados(logged_in_admin, db, creator_a, brand_a):
    hoy = date.today()
    ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    _set_upload_date(db, ticket, f"{hoy.year:04d}-{hoy.month:02d}-05T09:00:00")

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_chica")
    assert item["spent"] == 1000.0


def test_caja_chica_excluye_pendientes_y_rechazados(logged_in_admin, db, creator_a, brand_a):
    hoy = date.today()
    pendiente = make_ticket(db, creator=creator_a, brand=brand_a, amount=999, status="pendiente")
    rechazado = make_ticket(db, creator=creator_a, brand=brand_a, amount=999, status="rechazado")
    for t in (pendiente, rechazado):
        _set_upload_date(db, t, f"{hoy.year:04d}-{hoy.month:02d}-05T09:00:00")

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_chica")
    assert item["spent"] == 0.0


def test_caja_chica_ignora_gastos_generales(logged_in_admin, brand_a):
    hoy = date.today()
    _crear_general(logged_in_admin, brand_a.id, amount=9999)

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_chica")
    assert item["spent"] == 0.0


def test_spent_fuera_de_mes_no_cuenta(logged_in_admin, db, creator_a, brand_a):
    year, month = _mes_futuro()
    hoy = date.today()
    ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    _set_upload_date(db, ticket, f"{hoy.year:04d}-{hoy.month:02d}-05T09:00:00")

    item = _por_mes(logged_in_admin, year, month, "caja_chica")
    assert item["spent"] == 0.0


# ── Reconciliación histórica (actual_override, solo por script) ────────────


def test_set_historical_actual_fija_meta_y_gasto_al_mismo_valor(logged_in_admin, db):
    year, month = _mes_pasado()
    crud.set_historical_actual(db, year=year, month=month, categoria="caja_grande", amount=16415.72)

    item = _por_mes(logged_in_admin, year, month, "caja_grande")
    assert item["amount"] == 16415.72
    assert item["spent"] == 16415.72
    assert item["is_editable"] is False
    assert item["is_suggested"] is False


def test_set_historical_actual_no_afecta_la_otra_categoria(logged_in_admin, db):
    year, month = _mes_pasado()
    crud.set_historical_actual(db, year=year, month=month, categoria="caja_grande", amount=16415.72)

    item = _por_mes(logged_in_admin, year, month, "caja_chica")
    assert item["amount"] is None
    assert item["spent"] == 0.0


def test_set_historical_actual_ignora_tickets_reales_del_mismo_mes(logged_in_admin, db, creator_a, brand_a):
    """El override sustituye por completo el cálculo en vivo — no se suma."""
    year, month = _mes_pasado()
    ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=999999, status="aprobado")
    _set_upload_date(db, ticket, f"{year:04d}-{month:02d}-05T09:00:00")

    crud.set_historical_actual(db, year=year, month=month, categoria="caja_chica", amount=2703.75)

    item = _por_mes(logged_in_admin, year, month, "caja_chica")
    assert item["spent"] == 2703.75


def test_set_historical_actual_es_idempotente(db):
    year, month = _mes_pasado()
    crud.set_historical_actual(db, year=year, month=month, categoria="caja_chica", amount=1000)
    crud.set_historical_actual(db, year=year, month=month, categoria="caja_chica", amount=2000)
    filas = db.execute(
        text("SELECT COUNT(*) FROM monthly_spend_estimates WHERE year=:y AND month=:m AND categoria=:c"),
        {"y": year, "m": month, "c": "caja_chica"},
    ).scalar()
    assert filas == 1


def test_set_historical_actual_no_exige_mes_pasado(db):
    """A propósito no usa mes_es_editable: reconciliar un mes ya cerrado es
    justo el caso de uso; el PUT del router es el único que exige futuro."""
    year, month = _mes_pasado()
    fila = crud.set_historical_actual(db, year=year, month=month, categoria="caja_grande", amount=500)
    assert fila.amount == 500
    assert fila.actual_override == 500


# ── Sugerencia automática (promedio de los 3 meses anteriores, por categoría) ─


def test_sin_historial_no_sugiere_nada(logged_in_admin):
    year, month = _mes_futuro()
    for categoria in ("caja_grande", "caja_chica"):
        item = _por_mes(logged_in_admin, year, month, categoria)
        assert item["amount"] is None
        assert item["is_suggested"] is False


def test_sugiere_promedio_de_los_3_meses_anteriores(logged_in_admin, db):
    year, month = _mes_futuro()
    y1, m1 = _add_months(year, month, -1)
    y2, m2 = _add_months(year, month, -2)
    y3, m3 = _add_months(year, month, -3)
    for y, m, amount in ((y1, m1, 3000), (y2, m2, 6000), (y3, m3, 9000)):
        crud.set_historical_actual(db, year=y, month=m, categoria="caja_chica", amount=amount)

    item = _por_mes(logged_in_admin, year, month, "caja_chica")
    assert item["amount"] == 6000.0
    assert item["is_suggested"] is True
    assert item["is_editable"] is True
    # caja_grande no tiene historial propio -> sigue sin sugerir.
    assert _por_mes(logged_in_admin, year, month, "caja_grande")["amount"] is None


def test_mes_actual_nunca_sugiere_aunque_haya_historial(logged_in_admin, db):
    """La sugerencia solo aplica a meses futuros (editables) — el mes en curso
    ya no admite meta nueva, sugerida o no."""
    hoy = date.today()
    y1, m1 = _mes_pasado()
    crud.set_historical_actual(db, year=y1, month=m1, categoria="caja_grande", amount=9000)

    item = _por_mes(logged_in_admin, hoy.year, hoy.month, "caja_grande")
    assert item["amount"] is None
    assert item["is_suggested"] is False


def test_sugerencia_no_se_guarda_sola_en_la_tabla(logged_in_admin, db):
    """GET repetido da la misma sugerencia sin que nadie la haya confirmado."""
    year, month = _mes_futuro()
    y1, m1 = _add_months(year, month, -1)
    crud.set_historical_actual(db, year=y1, month=m1, categoria="caja_chica", amount=1000)

    _por_mes(logged_in_admin, year, month, "caja_chica")
    _por_mes(logged_in_admin, year, month, "caja_chica")
    filas = db.execute(
        text("SELECT COUNT(*) FROM monthly_spend_estimates WHERE year=:y AND month=:m AND categoria='caja_chica'"),
        {"y": year, "m": month},
    ).scalar()
    assert filas == 0


def test_meta_ya_guardada_nunca_se_marca_como_sugerida(logged_in_admin, db):
    year, month = _mes_futuro()
    y1, m1 = _add_months(year, month, -1)
    crud.set_historical_actual(db, year=y1, month=m1, categoria="caja_grande", amount=5000)
    _put(logged_in_admin, year, month, "caja_grande", 999)

    item = _por_mes(logged_in_admin, year, month, "caja_grande")
    assert item["amount"] == 999.0
    assert item["is_suggested"] is False


# ── Permisos ───────────────────────────────────────────────────────────────


def test_no_autenticado_401(client):
    assert client.get("/api/dashboard/monthly-estimates", params={"year": 2026}).status_code == 401


def test_creador_403(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/monthly-estimates", params={"year": 2026}).status_code == 403


def test_marketing_basico_403(logged_in_marketing_basico):
    r = logged_in_marketing_basico.get("/api/dashboard/monthly-estimates", params={"year": 2026})
    assert r.status_code == 403


def test_marketing_admin_puede_ver_y_editar(logged_in_marketing_admin):
    year, month = _mes_futuro()
    assert _put(logged_in_marketing_admin, year, month, "caja_chica", 5000).status_code == 200


def test_marketing_presupuestos_puede_ver_y_editar(logged_in_marketing_presupuestos):
    year, month = _mes_futuro()
    assert _put(logged_in_marketing_presupuestos, year, month, "caja_grande", 5000).status_code == 200


def test_creador_no_puede_editar_403(logged_in_creador):
    year, month = _mes_futuro()
    assert _put(logged_in_creador, year, month, "caja_chica", 5000).status_code == 403
