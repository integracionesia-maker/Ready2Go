"""GET /api/dashboard/report.html: reporte del dashboard como HTML autocontenido
para compartir (reemplazó al PDF de reportlab). Los datos viajan incrustados en
un <script type="application/json"> — las aserciones los leen de ahí (no hay
navegador en pytest) y verifican headers, permisos, alertas/textos automáticos
y que el texto libre nunca pueda romper el archivo."""

import json
import re

from .conftest import make_ticket

PDF = ("comprobante.pdf", b"%PDF-1.4\n% comprobante de prueba\n", "application/pdf")


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


def _datos(resp) -> dict:
    """JSON incrustado en el HTML, tal como lo leería el JS de la plantilla."""
    m = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', resp.text, re.S)
    assert m, "el HTML no trae el bloque de datos"
    return json.loads(m.group(1))


def test_genera_un_html_de_verdad(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.html")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert resp.text.lstrip().lower().startswith("<!doctype html>")
    assert "__DATOS__" not in resp.text and "__TITULO__" not in resp.text


def test_content_disposition_attachment_con_nombre(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.html?start_date=2026-08-01&end_date=2026-08-31")
    disposition = resp.headers["content-disposition"]
    assert "attachment" in disposition
    assert "reporte-presupuesto_2026-08-01_a_2026-08-31.html" in disposition


def test_sin_filtro_de_fechas_usa_nombre_historico_actual(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.html")
    assert "reporte-presupuesto_historico_a_actual.html" in resp.headers["content-disposition"]


def test_ya_no_existe_el_endpoint_pdf(logged_in_admin):
    # El fallback del SPA puede contestar 200 con el index; lo que importa es que no sea un PDF.
    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    assert resp.headers.get("content-type", "") != "application/pdf"
    assert not resp.content.startswith(b"%PDF")


def test_no_depende_de_la_api_ni_de_la_sesion(logged_in_admin):
    # Pensado para compartir: el archivo no debe consultar nada por su cuenta.
    texto = logged_in_admin.get("/api/dashboard/report.html").text
    assert "fetch(" not in texto
    assert "XMLHttpRequest" not in texto
    assert "/api/" not in texto


def test_es_autocontenido_sin_imagenes_ni_recursos_externos(logged_in_admin):
    # Pensado para compartir: nada de recursos externos (ni siquiera fuentes de Google)
    # y ningún marcador de la plantilla sin resolver.
    texto = logged_in_admin.get("/api/dashboard/report.html").text
    assert "__F_" not in texto and "__LOGO_" not in texto
    sin_xmlns = texto.replace("http://www.w3.org/2000/svg", "")  # espacio de nombres SVG, no es una petición
    assert "googleapis" not in texto
    assert "http://" not in sin_xmlns and "https://" not in sin_xmlns
    assert texto.count("font/woff2;base64,") == 5
    # Sin imágenes: nada que pueda no verse al compartir el archivo.
    assert "<img" not in texto and "data:image/png" not in texto and "data:image/jpeg" not in texto


def test_contenido_refleja_los_datos_reales(logged_in_admin, db, creator_a, brand_a):
    make_ticket(db, creator=creator_a, brand=brand_a, amount=1234, status="aprobado")

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    assert d["totales"]["cre"] == 1234.0
    assert d["totales"]["tickets"] == 1
    assert [c["n"] for c in d["creadores"]] == [creator_a.name]
    assert [m["n"] for m in d["marcas_cre"]] == [brand_a.name]
    assert d["meta"]["generado_por"]


def test_ticket_pendiente_va_aparte_no_como_gastado(logged_in_admin, db, creator_a, brand_a):
    make_ticket(db, creator=creator_a, brand=brand_a, amount=5000, status="pendiente")

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    assert d["totales"]["cre"] == 0
    assert d["totales"]["pendiente_monto"] == 5000.0
    assert any("pendientes por confirmar" in a["t"] for a in d["alertas"])


def test_sin_datos_no_revienta(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.html?start_date=2020-01-01&end_date=2020-01-31")
    assert resp.status_code == 200
    d = _datos(resp)
    assert d["totales"]["total"] == 0
    assert d["creadores"] == [] and d["top_all"] == [] and d["alertas"] == []
    assert d["textos"]["reparto"] is None


def test_top5_global_y_por_seccion(logged_in_admin, brand_a):
    rubro_id = _crear_rubro(logged_in_admin)
    for i in range(6):
        _crear_gasto(logged_in_admin, rubro_id, amount=1000 + i, descripcion=f"op {i}")
        _crear_general(logged_in_admin, brand_a.id, amount=2000 + i, description=f"gen {i}")

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    assert len(d["top_all"]) == 5
    assert [t["g"] for t in d["top_all"]] == [2005.0, 2004.0, 2003.0, 2002.0, 2001.0]
    assert len(d["gen_top"]) == 5 and len(d["ope_top"]) == 5
    assert {t["t"] for t in d["top_all"]} == {"gen"}
    assert d["ope_rubros"][0]["n"] == "IA" and d["ope_rubros"][0]["k"] == 6
    assert d["gen_marcas"][0]["n"] == brand_a.name


def test_el_dashboard_normal_sigue_con_top3(logged_in_admin, brand_a):
    for i in range(5):
        _crear_general(logged_in_admin, brand_a.id, amount=100 + i)
    assert len(logged_in_admin.get("/api/dashboard/top-expenses").json()) == 3


# ── Texto libre: nunca debe romper ni inyectar nada en el archivo ───────────


def test_texto_libre_no_puede_cerrar_el_script_ni_inyectar_html(logged_in_admin, brand_a):
    malicioso = '</script><img src=x onerror=alert(1)> & "comillas"'
    _crear_general(logged_in_admin, brand_a.id, amount=300, description=malicioso)

    resp = logged_in_admin.get("/api/dashboard/report.html")

    assert resp.status_code == 200
    # Los datos siguen siendo JSON válido y conservan el texto tal cual...
    assert _datos(resp)["gen_top"][0]["d"] == malicioso
    # ...pero en el HTML nunca aparece crudo.
    assert "<img src=x" not in resp.text
    assert resp.text.count("</script>") == 2  # el de datos y el del código, nada más


def test_la_plantilla_escapa_antes_de_usar_innerhtml(logged_in_admin):
    texto = logged_in_admin.get("/api/dashboard/report.html").text
    assert "const esc =" in texto


# ── Periodo, comparación y textos automáticos ──────────────────────────────


def test_mes_completo_activa_titulo_y_comparacion(logged_in_admin, brand_a):
    d = _datos(logged_in_admin.get("/api/dashboard/report.html?start_date=2026-08-01&end_date=2026-08-31"))
    assert d["meta"]["titulo"] == "Presupuesto de agosto 2026"
    assert d["meta"]["periodo"] == "1 – 31 ago 2026"
    assert d["comparacion"]["label"] == "julio"
    assert set(d["comparacion"]["items"]) == {"cre", "gen", "ope"}


def test_rango_multimes_no_trae_comparacion_y_lo_explica(logged_in_admin):
    d = _datos(logged_in_admin.get("/api/dashboard/report.html?start_date=2026-06-01&end_date=2026-08-31"))
    assert d["comparacion"] is None
    assert d["meta"]["titulo"] == "Reporte de presupuesto"
    assert any("Sin comparativo" in n["t"] for n in d["notas"])


def test_una_sola_fecha_no_se_etiqueta_como_todo_el_historico(logged_in_admin):
    d = _datos(logged_in_admin.get("/api/dashboard/report.html?start_date=2026-08-01"))
    assert d["meta"]["periodo"] == "Desde 1 ago 2026"
    assert d["meta"]["periodo_largo"] == "desde 01/08/2026"


def test_sin_fechas_es_todo_el_historico(logged_in_admin):
    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))
    assert d["meta"]["periodo"] == "Todo el histórico"


def test_alerta_creador_que_excedio_su_ciclo(logged_in_admin, db, creator_a, brand_a):
    creator_a.cycle_budget_amount = 100.0
    db.commit()
    make_ticket(db, creator=creator_a, brand=brand_a, amount=250, status="aprobado")

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    c = d["creadores"][0]
    assert c["ciclo"] == 100.0 and c["g"] == 250.0
    alerta = next(a for a in d["alertas"] if a["k"] == "bad")
    assert "250% de su ciclo" in alerta["t"]
    assert alerta["go"] == ["creadores", c["id"]]


def test_alerta_creador_sin_ciclo_asignado(logged_in_admin, db, creator_a, brand_a):
    creator_a.cycle_budget_amount = 0.0
    db.commit()
    make_ticket(db, creator=creator_a, brand=brand_a, amount=400, status="aprobado")

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    assert d["creadores"][0]["ciclo"] == 0.0
    assert any(a["k"] == "warn" and "sin presupuesto" in a["t"] for a in d["alertas"])
    assert any("Sin ciclo asignado" in n["t"] for n in d["notas"])


def test_alerta_gasto_unico_que_domina_su_seccion(logged_in_admin, brand_a):
    _crear_general(logged_in_admin, brand_a.id, amount=900, description="Kermés")
    _crear_general(logged_in_admin, brand_a.id, amount=100, description="Chico")

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    alerta = next(a for a in d["alertas"] if a["go"] == ["generales"])
    assert "Kermés" in alerta["t"] and "90%" in alerta["s"]


def test_sin_alerta_de_gasto_unico_si_solo_hay_un_gasto(logged_in_admin, brand_a):
    _crear_general(logged_in_admin, brand_a.id, amount=900, description="Solo uno")
    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))
    assert not any(a["go"] == ["generales"] for a in d["alertas"])


def test_frase_de_reparto(logged_in_admin, brand_a):
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=800, descripcion="Canva")
    _crear_general(logged_in_admin, brand_a.id, amount=200)

    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))

    assert d["textos"]["reparto"].startswith("El 80% del gasto del periodo fue en gastos operativos")


def test_nota_de_ciclo_vigente_siempre_presente(logged_in_admin):
    d = _datos(logged_in_admin.get("/api/dashboard/report.html"))
    assert any("son de hoy" in n["t"] for n in d["notas"])


# ── Permisos ───────────────────────────────────────────────────────────────


def test_creador_no_puede_descargar_el_reporte(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/report.html").status_code == 403


def test_marketing_basico_no_puede_descargar_el_reporte(logged_in_marketing_basico):
    assert logged_in_marketing_basico.get("/api/dashboard/report.html").status_code == 403


def test_marketing_presupuestos_si_puede(logged_in_marketing_presupuestos):
    assert logged_in_marketing_presupuestos.get("/api/dashboard/report.html").status_code == 200


def test_marketing_admin_si_puede(logged_in_marketing_admin):
    assert logged_in_marketing_admin.get("/api/dashboard/report.html").status_code == 200


def test_sin_sesion_responde_401(client):
    assert client.get("/api/dashboard/report.html").status_code == 401
