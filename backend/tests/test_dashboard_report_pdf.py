"""GET /api/dashboard/report.pdf: reporte generado en backend con reportlab
(vectores nativos, sin captura de pantalla) — mismo estilo de aserciones que
`tests/equipos/test_responsiva_pdf.py` (pypdf para contenido, HTTP directo
para status/headers/permisos)."""

import io

from pypdf import PdfReader

from .conftest import make_ticket


def _texto(contenido: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)


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
    # Rango sin nada: el PDF se genera igual, con un aviso por sección (no una
    # gráfica vacía por cada tipo de dato) — ver dashboard_reporte.py.
    resp = logged_in_admin.get("/api/dashboard/report.pdf?start_date=2020-01-01&end_date=2020-01-31")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
    texto = _texto(resp.content)
    assert "Sin actividad de presupuestos de creadores en este período." in texto
    assert "Sin gastos generales ni operativos en este período." in texto
    assert "Sin tickets subidos en este período." in texto


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
