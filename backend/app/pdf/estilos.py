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
    "FUENTE_TITULO",
    "FUENTE_CUERPO",
    "FUENTE_MONO",
    "MARGENES",
    "estilos",
]

# Paleta (tokens_marca.md). El naranja es el UNICO acento.
NARANJA_GO = colors.HexColor("#FB670B")
TEXTO = colors.HexColor("#262626")
TEXTO_SECUNDARIO = colors.HexColor("#535353")
LINEA = colors.HexColor("#C5C5C5")
FONDO = colors.HexColor("#FFFFFF")

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
    }
