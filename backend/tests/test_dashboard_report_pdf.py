"""GET /api/dashboard/report.pdf: reporte generado en backend con reportlab
(vectores nativos, sin captura de pantalla) — mismo estilo de aserciones que
`tests/equipos/test_responsiva_pdf.py` (pypdf para contenido, HTTP directo
para status/headers/permisos).

Desde 2026-09-30 el reporte se organiza en 5 paginas tematicas (portada,
creadores, generales, operativos, resumen), cada tema en pagina nueva."""

import io

from pypdf import PdfReader

from .conftest import make_ticket


def _texto(contenido: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)


def _paginas(contenido: bytes) -> list[str]:
    """Texto extraido pagina por pagina, para aserciones estructurales."""
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages]


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


def test_genera_un_pdf_de_verdad(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_content_disposition_attachment_con_nombre(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2026-08-01&end_date=2026-08-31")
    disposition = resp.headers["content-disposition"]
    assert "attachment" in disposition
    assert "reporte-presupuesto_2026-08-01_a_2026-08-31.pdf" in disposition


def test_sin_filtro_de_fechas_usa_nombre_historico_actual(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    assert "reporte-presupuesto_historico_a_actual.pdf" in resp.headers["content-disposition"]


def test_contenido_refleja_los_datos_reales(logged_in_admin, db, creator_a, brand_a):
    make_ticket(db, creator=creator_a, brand=brand_a, amount=1234, status="aprobado")

    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    texto = _texto(resp.content)

    assert "GRUPO ORTIZ" in texto
    assert "PRESUPUESTO TOTAL" in texto
    assert creator_a.name in texto
    assert brand_a.name in texto


def test_ticket_pendiente_aparece_como_pendiente_no_como_gastado(logged_in_admin, db, creator_a, brand_a):
    make_ticket(db, creator=creator_a, brand=brand_a, amount=5000, status="pendiente")

    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    texto = _texto(resp.content)

    assert "pendientes por confirmar" in texto
    assert "$5,000.00" in texto


def test_sin_datos_no_revienta(logged_in_admin):
    # Rango sin nada: el PDF se genera igual, con un aviso por página temática
    # (no una gráfica vacía por cada tipo de dato) — ver dashboard_reporte.py.
    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2020-01-01&end_date=2020-01-31")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
    texto = _texto(resp.content)
    assert "Sin actividad de presupuestos de creadores en este período." in texto
    assert "Sin gastos generales en este período." in texto
    assert "Sin gastos operativos en este período." in texto
    assert "Distribución del Gasto del Período" not in texto


def test_top3_aparece_en_el_pdf(logged_in_admin, brand_a):
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=5000, descripcion="Gasto operativo top")
    _crear_general(logged_in_admin, brand_a.id, amount=4000, description="Gasto general top")
    _crear_general(logged_in_admin, brand_a.id, amount=1500, description="Gasto general menor")

    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    assert resp.status_code == 200
    texto = _texto(resp.content)

    assert "Mayores Gastos Individuales del Período" in texto
    assert "$5,000.00" in texto
    assert "$4,000.00" in texto
    assert "Gasto operativo top" in texto
    assert "Gasto general top" in texto
    assert "Operativo" in texto
    assert "IA" in texto


def test_pdf_sin_gastos_omite_el_top3(logged_in_admin):
    # Rango vacío: el Top 3 se omite y las cajas únicas de "sin gastos" por
    # página (generales y operativos) se conservan — ver dashboard_reporte.py.
    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2020-01-01&end_date=2020-01-31")
    texto = _texto(resp.content)
    assert "Mayores Gastos Individuales del Período" not in texto
    assert "Sin gastos generales en este período." in texto
    assert "Sin gastos operativos en este período." in texto


# ── Estructura de 5 páginas temáticas (2026-09-30) ────────────────────────


def test_rango_vacio_genera_exactamente_5_paginas(logged_in_admin):
    # La reestructura arranca cada tema en página nueva y NUNCA deja un
    # PageBreak final: un rango sin datos produce exactamente 5 páginas
    # (portada, creadores, generales, operativos, resumen).
    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2020-01-01&end_date=2020-01-31")
    assert resp.status_code == 200
    reader = PdfReader(io.BytesIO(resp.content))
    assert len(reader.pages) == 5


def test_cada_pagina_tiene_su_tema_en_rango_vacio(logged_in_admin):
    # Rango vacío (determinístico): cada página lleva su título y su caja de
    # "sin datos" o su grilla de KPIs — solo asserts positivos.
    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2020-01-01&end_date=2020-01-31")
    paginas = _paginas(resp.content)

    assert "GRUPO ORTIZ" in paginas[0]
    assert "GOCreate" in paginas[0]
    assert "Control de Presupuestos" in paginas[0]
    assert "Período:" in paginas[0]

    assert "PRESUPUESTOS DE CREADORES" in paginas[1]
    assert "Sin actividad de presupuestos de creadores en este período." in paginas[1]

    assert "GASTOS GENERALES" in paginas[2]
    assert "Sin gastos generales en este período." in paginas[2]

    assert "GASTOS OPERATIVOS" in paginas[3]
    assert "Sin gastos operativos en este período." in paginas[3]

    assert "RESUMEN GENERAL" in paginas[4]
    assert "PRESUPUESTO TOTAL" in paginas[4]


def test_el_logo_aparece_en_la_portada(logged_in_admin):
    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    reader = PdfReader(io.BytesIO(resp.content))
    # El isotipo es la única imagen del reporte; las gráficas son vectores.
    # (`page.images` en pypdf 4.x es un generador, no una lista.)
    assert len(list(reader.pages[0].images)) >= 1
    assert list(reader.pages[1].images) == []


def test_donut_aparece_cuando_hay_datos(logged_in_admin, db, creator_a, brand_a):
    make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    _crear_general(logged_in_admin, brand_a.id, amount=500, description="Gasto general donut")
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=300, descripcion="Gasto operativo donut")

    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    assert resp.status_code == 200
    texto = _texto(resp.content)

    assert "Distribución del Gasto del Período" in texto
    # Etiquetas de la leyenda del donut ("nombre · $monto") — específicas del
    # donut, no de las tarjetas KPI ni de los títulos de sección.
    assert "Creadores ·" in texto
    assert "Gastos Generales ·" in texto
    assert "Gastos Operativos ·" in texto


def test_paginas_de_gastos_tienen_sus_propios_tops(logged_in_admin, brand_a):
    # Página 3 y 4 llevan su propia tabla de mayores gastos (top 5 por tipo)
    # además de las gráficas generales — cada una solo con gastos de su tipo.
    rubro_id = _crear_rubro(logged_in_admin)
    _crear_gasto(logged_in_admin, rubro_id, amount=5000, descripcion="Gasto operativo top pagina")
    _crear_gasto(logged_in_admin, rubro_id, amount=3000, descripcion="Gasto operativo menor")
    _crear_general(logged_in_admin, brand_a.id, amount=4000, description="Gasto general top pagina")
    _crear_general(logged_in_admin, brand_a.id, amount=1500, description="Gasto general menor")

    resp = logged_in_admin.get("/api/dashboard/report.pdf")
    assert resp.status_code == 200
    paginas = _paginas(resp.content)

    # Página 3 (generales): su top propio, sin gastos operativos dentro.
    assert "Mayores Gastos Generales" in paginas[2]
    assert "Gasto general top pagina" in paginas[2]
    assert "Gasto operativo top pagina" not in paginas[2]
    assert brand_a.name in paginas[2]  # etiqueta = marca

    # Página 4 (operativos): tabla de totales por rubro + su top propio.
    assert "Mayores Gastos Operativos" in paginas[3]
    assert "Gasto operativo top pagina" in paginas[3]
    assert "Gasto general top pagina" not in paginas[3]
    assert "IA" in paginas[3]  # etiqueta = rubro


def test_comparacion_este_periodo_vs_anterior_solo_en_periodo_unico(logged_in_admin, db, creator_a, brand_a):
    from datetime import datetime as dt

    ticket_agosto = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    ticket_agosto.upload_date = dt.fromisoformat("2026-08-10T09:00:00")
    ticket_julio = make_ticket(db, creator=creator_a, brand=brand_a, amount=500, status="aprobado")
    ticket_julio.upload_date = dt.fromisoformat("2026-07-10T09:00:00")
    db.commit()

    unico = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2026-08-01&end_date=2026-08-31")
    assert "Este Período vs Anterior" in _texto(unico.content)

    multi = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2026-06-01&end_date=2026-08-31")
    assert "Este Período vs Anterior" not in _texto(multi.content)


# ── Modo periodo único (I11): un solo mes/año oculta las gráficas "por mes" ─


def test_mes_cerrado_oculta_graficas_por_mes_y_muestra_por_marca(logged_in_admin, brand_a, creator_a, db):
    from datetime import datetime as dt
    from app import models

    ge_id = _crear_general(logged_in_admin, brand_a.id, amount=500).json()["id"]
    db.query(models.GeneralExpense).filter(models.GeneralExpense.id == ge_id).update(
        {"upload_date": dt.fromisoformat("2026-08-10T09:00:00")}
    )
    ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    ticket.upload_date = dt.fromisoformat("2026-08-10T09:00:00")
    db.commit()

    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2026-08-01&end_date=2026-08-31")
    assert resp.status_code == 200
    texto = _texto(resp.content)
    assert "Transacciones por Mes" not in texto
    assert "Gastos Generales por Mes" not in texto
    assert "Gastos Operativos por Mes" not in texto
    assert "Gastos Generales por Marca" in texto
    assert "Gastos por Marca" in texto  # de tickets, sigue igual


def test_rango_multimes_conserva_graficas_por_mes(logged_in_admin, brand_a, creator_a, db):
    ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    from datetime import datetime as dt
    ticket.upload_date = dt.fromisoformat("2026-08-10T09:00:00")
    db.commit()

    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2026-06-01&end_date=2026-08-31")
    assert resp.status_code == 200
    texto = _texto(resp.content)
    assert "Transacciones por Mes" in texto
    assert "Gastos Generales por Marca" not in texto


def test_mes_cerrado_muestra_comparacion_vs_mes_pasado(logged_in_admin, brand_a, creator_a, db):
    from datetime import datetime as dt

    ticket_agosto = make_ticket(db, creator=creator_a, brand=brand_a, amount=1000, status="aprobado")
    ticket_agosto.upload_date = dt.fromisoformat("2026-08-10T09:00:00")
    ticket_julio = make_ticket(db, creator=creator_a, brand=brand_a, amount=500, status="aprobado")
    ticket_julio.upload_date = dt.fromisoformat("2026-07-10T09:00:00")
    db.commit()

    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2026-08-01&end_date=2026-08-31")
    texto = _texto(resp.content)
    assert "vs el mes pasado" in texto


def test_forbidden_para_creador(logged_in_creador):
    assert logged_in_creador.get("/api/dashboard/report.pdf").status_code == 403


def test_forbidden_para_marketing_basico(logged_in_marketing_basico):
    assert logged_in_marketing_basico.get("/api/dashboard/report.pdf").status_code == 403


def test_permitido_para_marketing_presupuestos(logged_in_marketing_presupuestos):
    assert logged_in_marketing_presupuestos.get("/api/dashboard/report.pdf").status_code == 200


def test_permitido_para_marketing_admin(logged_in_marketing_admin):
    assert logged_in_marketing_admin.get("/api/dashboard/report.pdf").status_code == 200


def test_no_autenticado_da_401(client):
    assert client.get("/api/dashboard/report.pdf").status_code == 401
