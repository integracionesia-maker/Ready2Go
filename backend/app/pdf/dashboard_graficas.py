"""Graficas del reporte del Dashboard: vectores nativos de reportlab, sin
navegador ni captura de pantalla (a diferencia del viejo pipeline cliente con
ApexCharts + html2canvas).

`VerticalBarChart`/`HorizontalBarChart` de reportlab dibujan series LADO A LADO
(agrupadas) — no existe un modo "stacked" nativo (verificado contra el
`reportlab==5.0.0` instalado: `_attrMap` no tiene esa propiedad). Por eso estas
graficas usan barras agrupadas para "Aprobado" vs "Pendiente por confirmar" en
vez de apiladas como en pantalla: es lo idiomatico de la libreria, y para un
reporte impreso dos barras lado a lado se leen igual de claro.

Cada funcion recibe datos ya en listas simples (sin SQLAlchemy, mismo criterio
que `plantilla.py`) y devuelve un `Drawing` listo para insertar como flowable.
"""

from __future__ import annotations

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing

from . import estilos as est

# Paleta de series, en orden de uso (serie 1, serie 2, ...). La serie de
# "pendiente" SIEMPRE es la segunda posicion cuando `con_pendiente=True`.
_COLOR_SERIE_1 = est.TURQUESA
_COLOR_SERIE_2 = est.AMBAR
_COLOR_UNA_SOLA = est.NARANJA_GO


def _moneda(v: float) -> str:
    return f"${v:,.0f}"


def _porcentaje(v: float) -> str:
    return f"{v:.0f}%"


def grafica_vertical(
    categorias: list[str],
    series: list[tuple[str, list[float]]],
    ancho: float,
    alto: float,
    formato_valor=_moneda,
    categorias_densas: bool = False,
    color_principal=None,
) -> Drawing:
    """Barras verticales, una o dos series (agrupadas si son dos).

    `categorias_densas=True` (ej. Tickets por Dia con muchas fechas): rota las
    etiquetas y reduce su tamano en vez de omitir barras.
    """
    d = Drawing(ancho, alto)
    chart = VerticalBarChart()
    margen_inferior = 34 if not categorias_densas else 40
    margen_izquierdo = 42
    margen_superior = 14 if len(series) < 2 else 26  # deja espacio a la leyenda
    chart.x = margen_izquierdo
    chart.y = margen_inferior
    chart.width = ancho - margen_izquierdo - 10
    chart.height = alto - margen_inferior - margen_superior

    chart.data = [s[1] for s in series]
    chart.categoryAxis.categoryNames = categorias
    chart.categoryAxis.labels.fontSize = 6 if categorias_densas else 7.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fillColor = est.TEXTO_SECUNDARIO
    if categorias_densas:
        chart.categoryAxis.labels.angle = 90
        chart.categoryAxis.labels.dy = -12
        chart.categoryAxis.labels.dx = 2

    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = est.TEXTO_SECUNDARIO
    chart.valueAxis.labelTextFormat = formato_valor
    chart.valueAxis.valueMin = 0
    chart.valueAxis.gridStrokeColor = est.LINEA
    chart.valueAxis.visibleGrid = True

    colores = [_COLOR_SERIE_1, _COLOR_SERIE_2] if len(series) > 1 else [color_principal or _COLOR_UNA_SOLA]
    for i, color in enumerate(colores):
        chart.bars[i].fillColor = color
        chart.bars[i].strokeColor = None
    chart.barSpacing = 2
    chart.groupSpacing = 8

    d.add(chart)

    if len(series) > 1:
        leyenda = Legend()
        leyenda.x = margen_izquierdo
        leyenda.y = alto - 8
        leyenda.alignment = "right"
        leyenda.fontName = "Helvetica"
        leyenda.fontSize = 7.5
        leyenda.dx = 6
        leyenda.dy = 6
        leyenda.deltax = 0
        leyenda.columnMaximum = 1
        leyenda.colorNamePairs = [(colores[i], s[0]) for i, s in enumerate(series)]
        d.add(leyenda)

    return d


def grafica_horizontal(
    categorias: list[str],
    series: list[tuple[str, list[float]]],
    ancho: float,
    alto: float,
    formato_valor=_moneda,
    color_principal=None,
) -> Drawing:
    """Barras horizontales, una o dos series (agrupadas si son dos) —
    Gastos por Marca / por Rubro (una serie) o Uso por Creador (dos: %
    usado + % pendiente)."""
    d = Drawing(ancho, alto)
    chart = HorizontalBarChart()
    margen_izquierdo = 85
    margen_superior = 14 if len(series) < 2 else 26
    chart.x = margen_izquierdo
    chart.y = 8
    chart.width = ancho - margen_izquierdo - 30
    chart.height = alto - margen_superior - 8

    chart.data = [s[1] for s in series]
    chart.categoryAxis.categoryNames = categorias
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fillColor = est.TEXTO

    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = est.TEXTO_SECUNDARIO
    chart.valueAxis.labelTextFormat = formato_valor
    chart.valueAxis.valueMin = 0
    chart.valueAxis.gridStrokeColor = est.LINEA
    chart.valueAxis.visibleGrid = True

    colores = [_COLOR_SERIE_1, _COLOR_SERIE_2] if len(series) > 1 else [color_principal or _COLOR_UNA_SOLA]
    for i, color in enumerate(colores):
        chart.bars[i].fillColor = color
        chart.bars[i].strokeColor = None
    chart.barSpacing = 2
    chart.groupSpacing = 6

    d.add(chart)

    if len(series) > 1:
        leyenda = Legend()
        leyenda.x = margen_izquierdo
        leyenda.y = alto - 8
        leyenda.alignment = "right"
        leyenda.fontName = "Helvetica"
        leyenda.fontSize = 7.5
        leyenda.dx = 6
        leyenda.dy = 6
        leyenda.columnMaximum = 1
        leyenda.colorNamePairs = [(colores[i], s[0]) for i, s in enumerate(series)]
        d.add(leyenda)

    return d
