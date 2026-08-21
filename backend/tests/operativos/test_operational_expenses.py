"""Pruebas del módulo Gastos Operativos: rubros, gastos, dashboard, export,
permisos, aislamiento de marketing, borrado lógico y bucketing por fecha_gasto.
"""

PDF = ("comprobante.pdf", b"%PDF-1.4\n% comprobante de prueba\n", "application/pdf")


# ── Helpers ────────────────────────────────────────────────────────────────


def _crear_rubro(cli, nombre="IA"):
    r = cli.post("/api/rubros/", json={"nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_gasto(cli, rubro_id, *, amount=100.0, fecha="2026-08-15", descripcion="gasto x", con_archivo=True):
    data = {"rubro_id": str(rubro_id), "amount": str(amount), "description": descripcion, "fecha_gasto": fecha}
    files = {"file": PDF} if con_archivo else None
    return cli.post("/api/operational-expenses/", data=data, files=files)


# ── Rubros (catálogo) ────────────────────────────────────────────────────────


def test_admin_y_operativo_crean_rubro(logged_in_admin, cli_operativo):
    assert logged_in_admin.post("/api/rubros/", json={"nombre": "E-commerce"}).status_code == 201
    assert cli_operativo.post("/api/rubros/", json={"nombre": "Campañas"}).status_code == 201


def test_rubro_nombre_duplicado_da_409(logged_in_admin):
    assert logged_in_admin.post("/api/rubros/", json={"nombre": "IA"}).status_code == 201
    assert logged_in_admin.post("/api/rubros/", json={"nombre": "IA"}).status_code == 409


def test_marketing_admin_si_accede(logged_in_marketing_admin):
    # marketing_admin tiene acceso completo al módulo (igual que admin).
    assert logged_in_marketing_admin.get("/api/rubros/").status_code == 200
    assert logged_in_marketing_admin.post("/api/rubros/", json={"nombre": "X"}).status_code == 201


def test_marketing_basico_no_accede(logged_in_marketing_basico):
    # Los demás roles de marketing siguen fuera del módulo.
    assert logged_in_marketing_basico.get("/api/rubros/").status_code == 403
    assert logged_in_marketing_basico.get("/api/operational-expenses/").status_code == 403


def test_active_only_oculta_desactivados_pero_conserva_historial(logged_in_admin):
    rid = _crear_rubro(logged_in_admin, "Aplicaciones")
    assert _crear_gasto(logged_in_admin, rid).status_code == 201
    # Desactivar
    assert logged_in_admin.put(f"/api/rubros/{rid}", json={"is_active": False}).status_code == 200
    activos = logged_in_admin.get("/api/rubros/?active_only=true").json()
    assert rid not in [r["id"] for r in activos]
    # El gasto histórico sigue existiendo
    gastos = logged_in_admin.get("/api/operational-expenses/").json()
    assert any(g["rubro_id"] == rid for g in gastos)


# ── Alta de gastos ───────────────────────────────────────────────────────────


def test_alta_valida_cuenta_de_inmediato(cli_operativo):
    rid = _crear_rubro(cli_operativo)
    r = _crear_gasto(cli_operativo, rid, amount=250.0)
    assert r.status_code == 201, r.text
    assert r.json()["amount"] == 250.0
    assert r.json()["rubro_nombre"] == "IA"


def test_comprobante_obligatorio(cli_operativo):
    rid = _crear_rubro(cli_operativo)
    # Sin archivo → 422 (File(...) requerido por FastAPI)
    assert _crear_gasto(cli_operativo, rid, con_archivo=False).status_code == 422


def test_monto_debe_ser_positivo(cli_operativo):
    rid = _crear_rubro(cli_operativo)
    assert _crear_gasto(cli_operativo, rid, amount=0).status_code == 422


def test_rubro_inexistente_o_inactivo(cli_operativo, logged_in_admin):
    assert _crear_gasto(cli_operativo, 99999).status_code == 404
    rid = _crear_rubro(logged_in_admin, "Activaciones")
    logged_in_admin.put(f"/api/rubros/{rid}", json={"is_active": False})
    assert _crear_gasto(cli_operativo, rid).status_code == 400


# ── El mes lo define fecha_gasto, no la subida ───────────────────────────────


def test_bucketing_por_fecha_gasto(cli_operativo):
    rid = _crear_rubro(cli_operativo)
    _crear_gasto(cli_operativo, rid, amount=100, fecha="2026-06-30", descripcion="junio")
    _crear_gasto(cli_operativo, rid, amount=200, fecha="2026-08-04", descripcion="agosto")

    # Export de junio: solo el gasto de junio, aunque ambos se "subieron" hoy.
    exp = cli_operativo.get("/api/operational-expenses/export?months=2026-06").json()
    assert exp["total"] == 100
    assert len(exp["items"]) == 1 and exp["items"][0]["description"] == "junio"

    # Dashboard: dos meses distintos.
    dash = cli_operativo.get("/api/operational-expenses/dashboard").json()
    meses = {m["month"]: m["total"] for m in dash["mensual"]}
    assert meses.get("2026-06") == 100 and meses.get("2026-08") == 200
    assert dash["total"] == 300


def test_filtros_por_rubro_y_rango(cli_operativo):
    r1 = _crear_rubro(cli_operativo, "IA")
    r2 = _crear_rubro(cli_operativo, "E-commerce")
    _crear_gasto(cli_operativo, r1, amount=100, fecha="2026-08-10")
    _crear_gasto(cli_operativo, r2, amount=300, fecha="2026-08-20")
    solo_r1 = cli_operativo.get(f"/api/operational-expenses/?rubro_id={r1}").json()
    assert [g["rubro_id"] for g in solo_r1] == [r1]
    rango = cli_operativo.get("/api/operational-expenses/?start_date=2026-08-15&end_date=2026-08-31").json()
    assert len(rango) == 1 and rango[0]["amount"] == 300


# ── Borrado lógico (no físico) ───────────────────────────────────────────────


def test_borrado_logico_saca_del_total(cli_operativo):
    rid = _crear_rubro(cli_operativo)
    gid = _crear_gasto(cli_operativo, rid, amount=500).json()["id"]
    assert cli_operativo.post(f"/api/operational-expenses/{gid}/soft-delete").status_code == 200
    assert cli_operativo.get("/api/operational-expenses/").json() == []
    assert cli_operativo.get("/api/operational-expenses/dashboard").json()["total"] == 0


def test_no_existe_borrado_fisico(cli_operativo):
    rid = _crear_rubro(cli_operativo)
    gid = _crear_gasto(cli_operativo, rid).json()["id"]
    r = cli_operativo.delete(f"/api/operational-expenses/{gid}/permanent")
    assert r.status_code in (404, 405)


# ── Descarga del comprobante ─────────────────────────────────────────────────


def test_descarga_comprobante_permisos(cli_operativo, logged_in_creador, client):
    rid = _crear_rubro(cli_operativo)
    gid = _crear_gasto(cli_operativo, rid).json()["id"]
    assert cli_operativo.get(f"/api/operational-expenses/{gid}/file").status_code == 200
    # Un rol sin el módulo (creador) no puede descargar el comprobante.
    assert logged_in_creador.get(f"/api/operational-expenses/{gid}/file").status_code == 403
    assert client.get(f"/api/operational-expenses/{gid}/file").status_code == 401  # sin sesión


# ── Permisos y aislamiento ───────────────────────────────────────────────────


def test_roles_sin_el_modulo_no_lo_ven(logged_in_marketing_basico, logged_in_creador):
    # marketing_admin SÍ accede (ver test_marketing_admin_si_accede); estos no.
    for cli in (logged_in_marketing_basico, logged_in_creador):
        assert cli.get("/api/operational-expenses/").status_code == 403
        assert cli.get("/api/operational-expenses/dashboard").status_code == 403


def test_operativo_no_accede_a_presupuestos(cli_operativo):
    # El rol operativo está amurallado: nada de Presupuestos ni Equipos.
    assert cli_operativo.get("/api/dashboard/summary").status_code == 403
    assert cli_operativo.get("/api/general-expenses/").status_code == 403


def test_aislamiento_no_toca_gastos_generales(cli_operativo, logged_in_admin, brand_a):
    # Crear un gasto operativo no debe aparecer en gastos generales de marketing.
    rid = _crear_rubro(cli_operativo)
    _crear_gasto(cli_operativo, rid, amount=999)
    generales = logged_in_admin.get("/api/general-expenses/").json()
    assert generales == []  # los gastos operativos viven en otra tabla
