"""Tokens de marca y estilos del PDF.

Fuente de los valores: `docs/contratos/tokens_marca.md`. El PDF va en tema claro
siempre y **sin un solo emoji**.

Sobre las fuentes: Blauer Nue y Conthic son las de marca, pero viven en
`context_desing_go` y son dependencia de WP7 (§14.7 del plan) — no estan en este
repo. Se usan los respaldos que el propio documento de tokens autoriza:
Helvetica para titulos y cuerpo, Courier para folios y numeros de serie. Queda
escrito aqui y no elegido en silencio: el dia que lleguen los woff2/ttf, se
registran en `_registrar_fuentes()` y nada mas cambia.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm

__all__ = [
    "NARANJA_GO",
    "TEXTO",
    "TEXTO_SECUNDARIO",
    "LINEA",
    "FONDO",
    "TURQUESA",
    "AMBAR",
    "CIELO",
    "VIOLETA",
    "GRIS_CLARO",
    "GRIS_ZEBRA",
    "TINTES",
    "FUENTE_TITULO",
    "FUENTE_CUERPO",
    "FUENTE_MONO",
    "MARGENES",
    "estilos",
]

# Paleta (tokens_marca.md). El naranja es el UNICO acento para documentos de
# tipo carta (ej. la responsiva). El reporte del Dashboard es un documento de
# DATOS con varias secciones y series por grafica — reusa la paleta completa
# de 4 acentos que ya se ve en pantalla (`Dashboard.jsx`: ACCENTS
# orange/turquoise/sky/violet) para que el PDF no se sienta mas plano que lo
# que el usuario ya ve en el navegador, y para que cada seccion/tarjeta tenga
# su propia identidad visual en vez de repetir un solo color en todo el
# documento.
NARANJA_GO = colors.HexColor("#FB670B")
TEXTO = colors.HexColor("#262626")
TEXTO_SECUNDARIO = colors.HexColor("#535353")
LINEA = colors.HexColor("#C5C5C5")
FONDO = colors.HexColor("#FFFFFF")
TURQUESA = colors.HexColor("#14B8A6")  # aprobado / serie principal
AMBAR = colors.HexColor("#F59E0B")  # pendiente por confirmar / segunda serie
CIELO = colors.HexColor("#38BDF8")
VIOLETA = colors.HexColor("#A78BFA")
GRIS_CLARO = colors.HexColor("#F5F4EF")  # fondo de encabezados de tabla
GRIS_ZEBRA = colors.HexColor("#FAFAF7")  # renglon alterno de tabla

# Tintes (fondo muy claro de cada acento, mismo criterio que --go-orange-tint
# en el frontend) para las tarjetas de KPI — rotan en ese orden.
_NARANJA_TINTE = colors.HexColor("#FDEEE3")
_TURQUESA_TINTE = colors.HexColor("#E1F5F2")
_CIELO_TINTE = colors.HexColor("#E5F6FE")
_VIOLETA_TINTE = colors.HexColor("#F1EDFC")
TINTES = [
    (NARANJA_GO, _NARANJA_TINTE),
    (TURQUESA, _TURQUESA_TINTE),
    (CIELO, _CIELO_TINTE),
    (VIOLETA, _VIOLETA_TINTE),
]

FUENTE_TITULO = "Helvetica-Bold"   # respaldo autorizado de Blauer Nue
FUENTE_CUERPO = "Helvetica"        # respaldo autorizado de Conthic
FUENTE_CUERPO_NEGRITA = "Helvetica-Bold"
FUENTE_MONO = "Courier-Bold"       # respaldo autorizado de JetBrains Mono

# Margenes ajustados para que el caso comun —un prestamo de un equipo— quepa en
# UNA hoja con sus firmas. Con margenes de 22/18 mm el bloque de firmas se caia
# solo a la pagina 2, que es la peor forma de imprimir una carta responsiva:
# nadie sabe si la hoja 2 pertenece a esa hoja 1.
MARGENES = {
    "left": 20 * mm,
    "right": 20 * mm,
    "top": 14 * mm,
    "bottom": 14 * mm,
}

ANCHO_ETIQUETA = 42 * mm


def estilos() -> dict[str, ParagraphStyle]:
    """Estilos de parrafo del documento. Se construyen en cada llamada para que
    dos generaciones no compartan objetos mutables."""
    base = ParagraphStyle(
        "cuerpo",
        fontName=FUENTE_CUERPO,
        fontSize=9.5,
        leading=13.5,
        textColor=TEXTO,
        alignment=TA_JUSTIFY,
        spaceAfter=5,
    )

    return {
        "cuerpo": base,
        "folio": ParagraphStyle(
            "folio",
            parent=base,
            fontName=FUENTE_MONO,
            fontSize=10.5,
            leading=14,
            alignment=TA_RIGHT,
            textColor=TEXTO,
            spaceAfter=0,
        ),
        "fecha": ParagraphStyle(
            "fecha",
            parent=base,
            fontSize=9,
            alignment=TA_RIGHT,
            textColor=TEXTO_SECUNDARIO,
            spaceAfter=0,
        ),
        "emisor": ParagraphStyle(
            "emisor",
            parent=base,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "titulo": ParagraphStyle(
            "titulo",
            parent=base,
            fontName=FUENTE_TITULO,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=TEXTO,
            spaceBefore=8,
            spaceAfter=10,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            parent=base,
            fontName=FUENTE_TITULO,
            fontSize=10.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=NARANJA_GO,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "equipo_nombre": ParagraphStyle(
            "equipo_nombre",
            parent=base,
            fontName=FUENTE_TITULO,
            fontSize=10,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta",
            parent=base,
            fontSize=8.5,
            leading=11.5,
            textColor=TEXTO_SECUNDARIO,
            alignment=TA_JUSTIFY,
            spaceAfter=0,
        ),
        "valor": ParagraphStyle(
            "valor",
            parent=base,
            fontSize=8.5,
            leading=11.5,
            alignment=TA_JUSTIFY,
            spaceAfter=0,
        ),
        "valor_mono": ParagraphStyle(
            "valor_mono",
            parent=base,
            fontName="Courier",
            fontSize=8.5,
            leading=11.5,
            alignment=TA_JUSTIFY,
            spaceAfter=0,
        ),
        "legal": ParagraphStyle(
            "legal",
            parent=base,
            fontSize=8.5,
            leading=11.5,
            spaceAfter=4,
        ),
        "firma_nombre": ParagraphStyle(
            "firma_nombre",
            parent=base,
            fontName=FUENTE_CUERPO_NEGRITA,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "firma_pie": ParagraphStyle(
            "firma_pie",
            parent=base,
            fontSize=8,
            leading=10.5,
            alignment=TA_CENTER,
            textColor=TEXTO_SECUNDARIO,
            spaceAfter=0,
        ),
        "aviso": ParagraphStyle(
            "aviso",
            parent=base,
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=TEXTO_SECUNDARIO,
            spaceBefore=8,
        ),
        # ── Reporte del Dashboard (backend/app/pdf/dashboard_reporte.py) ────
        "banner_titulo": ParagraphStyle(
            "banner_titulo",
            parent=base,
            fontName=FUENTE_TITULO,
            fontSize=17,
            leading=20,
            textColor=colors.white,
            alignment=TA_JUSTIFY,
            spaceAfter=2,
        ),
        "banner_subtitulo": ParagraphStyle(
            "banner_subtitulo",
            parent=base,
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#FFE3CE"),
            alignment=TA_JUSTIFY,
            spaceAfter=0,
        ),
        "banner_meta": ParagraphStyle(
            "banner_meta",
            parent=base,
            fontSize=8,
            leading=11,
            textColor=colors.white,
            alignment=TA_JUSTIFY,
            spaceAfter=0,
        ),
        "banner_meta_der": ParagraphStyle(
            "banner_meta_der",
            parent=base,
            fontSize=8,
            leading=11,
            textColor=colors.white,
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "seccion_titulo": ParagraphStyle(
            "seccion_titulo",
            parent=base,
            fontName=FUENTE_TITULO,
            fontSize=11.5,
            leading=14,
            textColor=TEXTO,
            spaceBefore=2,
            spaceAfter=0,
        ),
        "pie_pagina": ParagraphStyle(
            "pie_pagina",
            parent=base,
            fontSize=7.5,
            leading=10,
            textColor=TEXTO_SECUNDARIO,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "kpi_etiqueta": ParagraphStyle(
            "kpi_etiqueta",
            parent=base,
            fontSize=7.5,
            leading=10,
            textColor=TEXTO_SECUNDARIO,
            spaceAfter=1,
        ),
        "kpi_valor": ParagraphStyle(
            "kpi_valor",
            parent=base,
            fontName=FUENTE_TITULO,
            fontSize=13,
            leading=16,
            textColor=TEXTO,
            spaceAfter=1,
        ),
        "kpi_pendiente": ParagraphStyle(
            "kpi_pendiente",
            parent=base,
            fontSize=7.5,
            leading=10,
            textColor=AMBAR,
            spaceAfter=0,
        ),
        "tabla_encabezado": ParagraphStyle(
            "tabla_encabezado",
            parent=base,
            fontName=FUENTE_CUERPO_NEGRITA,
            fontSize=8.5,
            leading=11,
            textColor=TEXTO,
            spaceAfter=0,
        ),
        "tabla_celda": ParagraphStyle(
            "tabla_celda",
            parent=base,
            fontSize=8.5,
            leading=11,
            textColor=TEXTO,
            alignment=TA_JUSTIFY,
            spaceAfter=0,
        ),
        "tabla_num": ParagraphStyle(
            "tabla_num",
            parent=base,
            fontName=FUENTE_MONO,
            fontSize=8.5,
            leading=11,
            textColor=TEXTO,
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "sin_datos": ParagraphStyle(
            "sin_datos",
            parent=base,
            fontSize=9,
            leading=13,
            textColor=TEXTO_SECUNDARIO,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=6,
        ),
    }
