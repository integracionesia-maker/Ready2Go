"""Top 3 de gastos individuales del período (dashboard): mezcla gastos
generales (filtra por upload_date) y operativos (filtra por fecha_gasto,
nunca upload_date), sin sumatorias por marca/rubro. Cada fila del top es un
registro único de su tabla, ordenado por monto desc."""
from datetime import date, timedelta

PDF = ("comprobante.pdf", b"%PDF-1.4\n% comprobante de prueba\n", "application/pdf")


# ── Helpers ────────────────────────────────────────────────────────────────


def _crear_rubro(cli, nombre="IA"):
    r = cli.post("/api/rubros/", json={"nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_gasto(cli, rubro_id, *, amount=100.0, fecha="2026-08-15", descripcion="gasto x"):
    data = {"rubro_id": str(rubro_id), "amount": str(amount), "description": descripcion, "fecha_gasto": fecha}
    return cli.post("/api/operational-expenses/", data=data, files={"file": PDF})


def _crear_general(cli, brand_id, *, amount=100.0, description="gasto general x"):
    return cli.post(
        "/api/general-expenses/",
        data={"brand_id": str(brand_id), "amount": str(amount), "description": description},
        files={"file": PDF},
    )


def _top(cli, start=None, end=None):
    params = {}
    if start:
        params["start_date"] = start
    if end:
        params["end_date"] = end
    return cli.get("/api/dashboard/top-expenses", params=params)


# ── Comportamiento ─────────────────────────────────────────────────────────


def test_vacio_devuelve_lista_vacia(logged_in_admin):
    assert _top(logged_in_admin).status_code == 200
    assert _top(logged_in_admin).json() == []


def test_uno_y_dos_gastos_devuelven_todos(logged_in_admin, brand_a):
    _crear_general(logged_in_admin, brand_a.id, amount=400, description="unico")
    r = _top(logged_in_admin)
    assert len(r.json()) == 1
    assert r.json()[0]["descripcion"] == "unico"

    _crear_general(logged_in_admin, brand_a.id, amount=200, description="segundo")
    top = _top(logged_in_admin).json()
    assert len(top) == 2
    assert [t["monto"] for t in top] == [400.0, 200.0]


def test_ordena_por_monto_desc_y_limita_a_3(logged_in_admin, brand_a):
    for monto, desc in [(100, "a"), (400, "b"), (300, "c"), (200, "d")]:
        _crear_general(logged_in_admin, brand_a.id, amount=monto, description=desc)
    top = _top(logged_in_admin).json()
    assert [t["monto"] for t in top] == [400.0, 300.0, 200.0]
    assert [t["descripcion"] for t in top] == ["b", "c", "d"]


def test_mezcla_general_y_operativo(logged_in_admin, brand_a):
    """El ejemplo del usuario: operativo 5k + generales 4k y 2k -> top mixto."""
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=5000, descripcion="gasto por rubro top")
    _crear_general(logged_in_admin, brand_a.id, amount=4000, description="general 4k")
    _crear_general(logged_in_admin, brand_a.id, amount=2000, description="general 2k")
    top = _top(logged_in_admin).json()
    assert [t["tipo"] for t in top] == ["operativo", "general", "general"]
    assert [t["monto"] for t in top] == [5000.0, 4000.0, 2000.0]


def test_etiquetas_brand_y_rubro(logged_in_admin, brand_a):
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=5000, descripcion="op")
    _crear_general(logged_in_admin, brand_a.id, amount=4000, description="ge")
    por_tipo = {t["tipo"]: t for t in _top(logged_in_admin).json()}
    assert por_tipo["general"]["etiqueta"] == "Marca A"
    assert por_tipo["operativo"]["etiqueta"] == "IA"


def test_fecha_normalizada_a_date(logged_in_admin, brand_a):
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=5000, fecha="2026-08-15", descripcion="op")
    _crear_general(logged_in_admin, brand_a.id, amount=4000, description="ge")
    por_tipo = {t["tipo"]: t for t in _top(logged_in_admin).json()}
    assert por_tipo["operativo"]["fecha"] == "2026-08-15"
    assert por_tipo["general"]["fecha"] == date.today().isoformat()


def test_general_se_filtra_por_upload_date(logged_in_admin, brand_a):
    _crear_general(logged_in_admin, brand_a.id, amount=400, description="hoy")
    hoy = date.today().isoformat()
    assert len(_top(logged_in_admin, start=hoy, end=hoy).json()) == 1
    futuro = (date.today() + timedelta(days=2)).isoformat()
    assert _top(logged_in_admin, start=futuro, end=futuro).json() == []


def test_operativo_se_filtra_por_fecha_gasto_no_upload(logged_in_admin):
    """Clava la regla de campos: el gasto subido HOY cuenta en el mes de su
    fecha_gasto (enero), no en el de subida (agosto)."""
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=9000, fecha="2026-01-05", descripcion="enero")
    assert len(_top(logged_in_admin, start="2026-01-01", end="2026-01-31").json()) == 1
    assert _top(logged_in_admin, start="2026-08-01", end="2026-08-31").json() == []


def test_excluye_borrados_soft(logged_in_admin, brand_a):
    rubro_id = _crear_rubro(logged_in_admin)
    ge = _crear_general(logged_in_admin, brand_a.id, amount=9999, description="ge borrado")
    op = _crear_gasto(logged_in_admin, rubro_id, amount=8888, descripcion="op borrado")
    assert logged_in_admin.post(f"/api/general-expenses/{ge.json()['id']}/soft-delete").status_code == 200
    assert logged_in_admin.post(f"/api/operational-expenses/{op.json()['id']}/soft-delete").status_code == 200
    top = _top(logged_in_admin).json()
    assert all(t["id"] not in (ge.json()["id"], op.json()["id"]) for t in top)


def test_empates_de_monto_son_deterministas(logged_in_admin, brand_a):
    _crear_general(logged_in_admin, brand_a.id, amount=500, description="empate a")
    _crear_general(logged_in_admin, brand_a.id, amount=500, description="empate b")
    top = _top(logged_in_admin).json()
    assert [t["monto"] for t in top] == [500.0, 500.0]
    assert {t["descripcion"] for t in top} == {"empate a", "empate b"}


# ── Permisos ───────────────────────────────────────────────────────────────


def test_no_autenticado_401(client):
    assert client.get("/api/dashboard/top-expenses").status_code == 401


def test_creador_403(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/top-expenses").status_code == 403


def test_marketing_basico_403(logged_in_marketing_basico):
    assert logged_in_marketing_basico.get("/api/dashboard/top-expenses").status_code == 403


def test_marketing_admin_200(logged_in_marketing_admin):
    assert logged_in_marketing_admin.get("/api/dashboard/top-expenses").status_code == 200


def test_marketing_presupuestos_200(logged_in_marketing_presupuestos):
    assert logged_in_marketing_presupuestos.get("/api/dashboard/top-expenses").status_code == 200
