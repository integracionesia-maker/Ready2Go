"""Gastos operativos: rubros, alta, dashboard, export, borrado lógico y
bucketing por fecha_gasto. Fusionado en la UI con Gastos Generales
(Presupuestos) — misma puerta de acceso (`require_role`) que
`test_general_expenses.py`, ya no el módulo RBAC aditivo `gastos_operativos`
(retirado del catálogo junto con el rol `operativo`).
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


def test_admin_crea_rubro(logged_in_admin):
    assert logged_in_admin.post("/api/rubros/", json={"nombre": "E-commerce"}).status_code == 201


def test_rubro_nombre_duplicado_da_409(logged_in_admin):
    assert logged_in_admin.post("/api/rubros/", json={"nombre": "IA"}).status_code == 201
    assert logged_in_admin.post("/api/rubros/", json={"nombre": "IA"}).status_code == 409


def test_marketing_admin_si_accede(logged_in_marketing_admin):
    assert logged_in_marketing_admin.get("/api/rubros/").status_code == 200
    assert logged_in_marketing_admin.post("/api/rubros/", json={"nombre": "X"}).status_code == 201


def test_marketing_presupuestos_si_accede(logged_in_marketing_presupuestos):
    # Misma puerta que general-expenses: marketing_presupuestos también entra.
    assert logged_in_marketing_presupuestos.get("/api/rubros/").status_code == 200
    rid = _crear_rubro(logged_in_marketing_presupuestos, "Suscripciones")
    assert _crear_gasto(logged_in_marketing_presupuestos, rid).status_code == 201


def test_marketing_basico_no_accede(logged_in_marketing_basico):
    assert logged_in_marketing_basico.get("/api/rubros/").status_code == 403
    assert logged_in_marketing_basico.get("/api/operational-expenses/").status_code == 403


def test_creador_no_accede(logged_in_creador):
    assert logged_in_creador.get("/api/operational-expenses/").status_code == 403
    assert logged_in_creador.get("/api/operational-expenses/dashboard").status_code == 403


def test_no_autenticado_da_401(client):
    assert client.get("/api/operational-expenses/").status_code == 401


def test_active_only_oculta_desactivados_pero_conserva_historial(logged_in_admin):
    rid = _crear_rubro(logged_in_admin, "Aplicaciones")
    assert _crear_gasto(logged_in_admin, rid).status_code == 201
    assert logged_in_admin.put(f"/api/rubros/{rid}", json={"is_active": False}).status_code == 200
    activos = logged_in_admin.get("/api/rubros/?active_only=true").json()
    assert rid not in [r["id"] for r in activos]
    gastos = logged_in_admin.get("/api/operational-expenses/").json()
    assert any(g["rubro_id"] == rid for g in gastos)


# ── Alta de gastos ───────────────────────────────────────────────────────────


def test_alta_valida_cuenta_de_inmediato(logged_in_admin):
    rid = _crear_rubro(logged_in_admin)
    r = _crear_gasto(logged_in_admin, rid, amount=250.0)
    assert r.status_code == 201, r.text
    assert r.json()["amount"] == 250.0
    assert r.json()["rubro_nombre"] == "IA"


def test_comprobante_obligatorio(logged_in_admin):
    rid = _crear_rubro(logged_in_admin)
    assert _crear_gasto(logged_in_admin, rid, con_archivo=False).status_code == 422


def test_monto_debe_ser_positivo(logged_in_admin):
    rid = _crear_rubro(logged_in_admin)
    assert _crear_gasto(logged_in_admin, rid, amount=0).status_code == 422


def test_rubro_inexistente_o_inactivo(logged_in_admin):
    assert _crear_gasto(logged_in_admin, 99999).status_code == 404
    rid = _crear_rubro(logged_in_admin, "Activaciones")
    logged_in_admin.put(f"/api/rubros/{rid}", json={"is_active": False})
    assert _crear_gasto(logged_in_admin, rid).status_code == 400


# ── El mes lo define fecha_gasto, no la subida ───────────────────────────────


def test_bucketing_por_fecha_gasto(logged_in_admin):
    rid = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rid, amount=100, fecha="2026-06-30", descripcion="junio")
    _crear_gasto(logged_in_admin, rid, amount=200, fecha="2026-08-04", descripcion="agosto")

    exp = logged_in_admin.get("/api/operational-expenses/export?months=2026-06").json()
    assert exp["total"] == 100
    assert len(exp["items"]) == 1 and exp["items"][0]["description"] == "junio"

    dash = logged_in_admin.get("/api/operational-expenses/dashboard").json()
    meses = {m["month"]: m["total"] for m in dash["mensual"]}
    assert meses.get("2026-06") == 100 and meses.get("2026-08") == 200
    assert dash["total"] == 300


def test_filtros_por_rubro_y_rango(logged_in_admin):
    r1 = _crear_rubro(logged_in_admin, "IA")
    r2 = _crear_rubro(logged_in_admin, "E-commerce")
    _crear_gasto(logged_in_admin, r1, amount=100, fecha="2026-08-10")
    _crear_gasto(logged_in_admin, r2, amount=300, fecha="2026-08-20")
    solo_r1 = logged_in_admin.get(f"/api/operational-expenses/?rubro_id={r1}").json()
    assert [g["rubro_id"] for g in solo_r1] == [r1]
    rango = logged_in_admin.get("/api/operational-expenses/?start_date=2026-08-15&end_date=2026-08-31").json()
    assert len(rango) == 1 and rango[0]["amount"] == 300


# ── Borrado lógico (no físico) ───────────────────────────────────────────────


def test_borrado_logico_saca_del_total(logged_in_admin):
    rid = _crear_rubro(logged_in_admin)
    gid = _crear_gasto(logged_in_admin, rid, amount=500).json()["id"]
    assert logged_in_admin.post(f"/api/operational-expenses/{gid}/soft-delete").status_code == 200
    assert logged_in_admin.get("/api/operational-expenses/").json() == []
    assert logged_in_admin.get("/api/operational-expenses/dashboard").json()["total"] == 0


def test_no_existe_borrado_fisico(logged_in_admin):
    rid = _crear_rubro(logged_in_admin)
    gid = _crear_gasto(logged_in_admin, rid).json()["id"]
    r = logged_in_admin.delete(f"/api/operational-expenses/{gid}/permanent")
    assert r.status_code in (404, 405)


# ── Descarga del comprobante ─────────────────────────────────────────────────


def test_descarga_comprobante_permisos(logged_in_admin, logged_in_creador, client):
    rid = _crear_rubro(logged_in_admin)
    gid = _crear_gasto(logged_in_admin, rid).json()["id"]
    assert logged_in_admin.get(f"/api/operational-expenses/{gid}/file").status_code == 200
    assert logged_in_creador.get(f"/api/operational-expenses/{gid}/file").status_code == 403
    assert client.get(f"/api/operational-expenses/{gid}/file").status_code == 401


# ── Ya NO está aislado de Presupuestos (fusión) ─────────────────────────────


def test_admin_ve_ambos_modulos(logged_in_admin, brand_a):
    # A diferencia del viejo rol `operativo` (amurallado), quien crea un gasto
    # operativo hoy tiene acceso completo a Presupuestos: misma puerta.
    assert logged_in_admin.get("/api/dashboard/summary").status_code == 200
    assert logged_in_admin.get("/api/general-expenses/").status_code == 200


def test_gasto_operativo_no_aparece_en_gastos_generales(logged_in_admin):
    # Siguen siendo tablas separadas: crear un gasto operativo no lo mete en
    # el listado de gastos generales (la fusión es de UI, no de esquema).
    rid = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rid, amount=999)
    generales = logged_in_admin.get("/api/general-expenses/").json()
    assert generales == []
