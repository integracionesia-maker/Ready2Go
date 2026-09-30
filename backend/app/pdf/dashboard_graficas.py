"""Graficas del reporte del Dashboard: vectores nativos de reportlab, sin
navegador ni captura de pantalla (a diferencia del viejo pipeline cliente con
ApexCharts + html2canvas).

`VerticalBarChart`/`HorizontalBarChart` de reportlab dibujan series LADO A LADO
(agrupadas) — no existe un modo "stacked" nativo (verificado contra el
`reportlab==5.0.0` instalado: `_attrMap` no tiene esa propiedad). Por eso estas
graficas usan barras agrupadas para series dobles (ej. "Aprobado" vs
"Pendiente por confirmar") en vez de apiladas como en pantalla: es lo idiomatico
de la libreria, y para un reporte impreso dos barras lado a lado se leen igual
de claro.

Colores (2026-09-30): cada grafica recibe sus colores por parametro — el color
fijo del tema para la primera serie y una sombra clara del mismo tema para la
segunda (nunca se mezclan colores de temas distintos). El donut
(`grafica_donut`) usa un Pie con un circulo blanco encima del centro: reportlab
no tiene donut nativo.

Cada funcion recibe datos ya en listas simples (sin SQLAlchemy, mismo criterio
que `plantilla.py`) y devuelve un `Drawing` listo para insertar como flowable.
"""

from __future__ import annotations

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing

from . import estilos as est


def _moneda(v: float) -> str:
    return f"${v:,.0f}"


def _porcentaje(v: float) -> str:
    return f"{v:.0f}%"


def _resolver_colores(series: list, colores: list | None) -> list:
    """Color por serie: el parametro `colores` si viene (tema + sombra clara
    del mismo tema), o el default naranja si no se especifica."""
    if colores is not None:
        return colores
    return [est.NARANJA_GO, est.NARANJA_CLARO] if len(series) > 1 else [est.NARANJA_GO]


def grafica_vertical(
    categorias: list[str],
    series: list[tuple[str, list[float]]],
    ancho: float,
    alto: float,
    formato_valor=_moneda,
    categorias_densas: bool = False,
    colores: list | None = None,
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

    for i, color in enumerate(_resolver_colores(series, colores)):
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
        leyenda.colorNamePairs = [
            (_resolver_colores(series, colores)[i], s[0]) for i, s in enumerate(series)
        ]
        d.add(leyenda)

    return d


def grafica_horizontal(
    categorias: list[str],
    series: list[tuple[str, list[float]]],
    ancho: float,
    alto: float,
    formato_valor=_moneda,
    colores: list | None = None,
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

    for i, color in enumerate(_resolver_colores(series, colores)):
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
        leyenda.colorNamePairs = [
            (_resolver_colores(series, colores)[i], s[0]) for i, s in enumerate(series)
        ]
        d.add(leyenda)

    return d


def grafica_donut(
    segmentos: list[tuple[str, float]],
    colores: list,
    ancho: float,
    alto: float = 150,
    radio_agujero: float = 0.55,
    leyenda_abajo: bool = False,
) -> Drawing:
    """Donut con leyenda ("nombre · $monto"). Sin `leyenda_abajo`: la leyenda
    va a la derecha del pie. Con `leyenda_abajo=True` (modo lado a lado del
    resumen, columnas angostas): el pie va arriba centrado y la leyenda
    apilada abajo, para no desbordar la columna con montos largos. ReportLab
    no tiene donut nativo: se dibuja un circulo blanco encima del centro de un
    Pie. Los valores 0 no dibujan rebanada; el llamador omite la grafica si
    todo es 0."""
    d = Drawing(ancho, alto)
    if leyenda_abajo:
        diametro = alto - 45
        pie_x = (ancho - diametro) / 2
        pie_y = alto - diametro
    else:
        diametro = alto
        pie_x = 0
        pie_y = 0
    pie = Pie()
    pie.x = pie_x
    pie.y = pie_y
    pie.width = diametro
    pie.height = diametro
    pie.data = [v for _, v in segmentos]
    pie.startAngle = 90
    pie.sideLabels = 0
    pie.simpleLabels = 0  # alias retrocompatible
    for i, color in enumerate(colores):
        pie.slices[i].fillColor = color
        pie.slices[i].strokeColor = est.FONDO
        pie.slices[i].strokeWidth = 1.5
    d.add(pie)
    d.add(
        Circle(
            pie_x + diametro / 2,
            pie_y + diametro / 2,
            diametro / 2 * radio_agujero,
            fillColor=est.FONDO,
            strokeColor=None,
        )
    )
    leyenda = Legend()
    if leyenda_abajo:
        # Los items se apilan hacia ABAJO desde y: 3 items ~34pt, dentro del
        # espacio libre bajo el pie.
        leyenda.x = 0
        leyenda.y = alto - diametro - 16
    else:
        leyenda.x = diametro + 12
        leyenda.y = alto - 10
    leyenda.alignment = "right"
    leyenda.fontName = "Helvetica"
    leyenda.fontSize = 8
    leyenda.dx = 6
    leyenda.dy = 6
    # OJO: columnMaximum = items POR columna (nCols = ceil(n/columnMaximum)),
    # asi que para una pila vertical de los N items hay que usar N — con 1
    # la leyenda saldria en fila horizontal (verificado en el source 5.0.0).
    leyenda.columnMaximum = len(segmentos)
    leyenda.colorNamePairs = [
        (colores[i], f"{nombre} · {_moneda(valor)}") for i, (nombre, valor) in enumerate(segmentos)
    ]
    d.add(leyenda)
    return d
