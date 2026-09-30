"""Reporte PDF del Dashboard de Presupuestos: convierte datos ya resueltos
(schemas Pydantic, mismos que ya ve la pantalla) en flowables de reportlab.

Reestructurado en 5 paginas tematicas (2026-09-30), cada tema arranca en
pagina nueva y usa UN color fijo: portada naranja (logo + datos de
presentacion), PRESUPUESTOS DE CREADORES en verde, GASTOS GENERALES en azul,
GASTOS OPERATIVOS en morado y RESUMEN GENERAL en naranja (KPIs, donut de
distribucion del gasto, comparacion vs periodo anterior y top 3). Si un tema
rebasa su pagina, se derrama de forma natural a una hoja extra.

Generado siempre en memoria (`generar_pdf` devuelve `bytes`, nunca escribe a
disco) — a diferencia de la carta responsiva (`responsiva.py`), este reporte
no tiene identidad propia que versionar: cada descarga esta atada a un filtro
de fechas que cambia, así que no hay nada que reusar entre requests.

Este módulo no toca la base de datos: recibe un diccionario con los datos ya
consultados (mismo criterio que `plantilla.py`) y devuelve flowables/bytes.

Diseño: portada centrada con fondo de tinte naranja, tarjetas de KPI en
naranja, títulos de sección con marca de color + barra de acento, tablas con
encabezado sombreado y renglón alterno, y pie de página con numeración. Una
gráfica/tabla sin datos se OMITE por completo (no se dibuja un recuadro vacío
ni un aviso individual); solo si una página entera queda sin nada se muestra
un único aviso, para no llenar el reporte de mensajes de "sin datos"
repetidos.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import dashboard_graficas as graf
from . import estilos as est
from .plantilla import MESES

__all__ = ["construir", "generar_pdf"]

MESES_ABREV = [m[:3].capitalize() for m in MESES]

# Color fijo por tema, en el orden en que aparecen las paginas del reporte —
# cada tema tiene su propia identidad y NUNCA se mezclan colores de temas
# distintos dentro de una pagina (2026-09-30).
_COLOR_SECCION_CREADORES = est.VERDE
_COLOR_SECCION_GENERALES = est.CIELO
_COLOR_SECCION_OPERATIVOS = est.VIOLETA
_COLOR_SECCION_RESUMEN = est.NARANJA_GO

_RUTA_ISOTIPO = Path(__file__).parent / "assets" / "isotipo-go-naranja.png"


def _moneda(v: float) -> str:
    return f"${v:,.2f}"


def _texto_comparacion(actual: float, anterior: float, label: str) -> str | None:
    """"+12.3% vs el mes pasado" / "−8.0% vs el año pasado". Sin porcentaje si
    el periodo anterior fue $0 (división por cero) — se muestra el delta en
    monto para no perder la comparación."""
    signo = "+" if actual >= anterior else "−"
    if anterior > 0:
        pct = abs((actual - anterior) / anterior) * 100
        return f"{signo}{pct:.1f}% vs {label}"
    if actual > 0:
        return f"antes $0.00 vs {label}"
    return None


def _entero(v) -> str:
    return f"{v:,.0f}"


def _mes_label(ym: str) -> str:
    """'2026-08' -> 'Ago 2026'."""
    try:
        y, m = ym.split("-")
        return f"{MESES_ABREV[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return ym


def _dia_label(iso: str) -> str:
    """'2026-08-31' -> '31/08'."""
    try:
        _, m, d = iso.split("-")
        return f"{d}/{m}"
    except ValueError:
        return iso


def _fecha_larga(fecha: date) -> str:
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def _fecha_hora_larga(momento: datetime) -> str:
    return f"{_fecha_larga(momento.date())}, {momento.strftime('%H:%M')}"


def _periodo_label(start_date: date | None, end_date: date | None) -> str:
    if start_date and end_date:
        return f"{_fecha_larga(start_date)} — {_fecha_larga(end_date)}"
    return "Todo el histórico"


# ── Piezas visuales reutilizables ───────────────────────────────────────────


def _color_paragraph(e: dict, base_key: str, texto: str, color) -> Paragraph:
    """Clona un ParagraphStyle existente con otro color — evita declarar en
    `estilos.py` una variante estática por cada combinación de sección/color."""
    estilo = ParagraphStyle(f"{base_key}_{id(color)}", parent=e[base_key], textColor=color)
    return Paragraph(texto, estilo)


def _subtitulo_estilo(e: dict, color) -> ParagraphStyle:
    """Estilo de subtitulo clonado con el color del tema — para subtitulos
    dentro de celdas de tabla (resumen lado a lado), donde se necesita el
    estilo y no el flowable."""
    return ParagraphStyle(f"subtitulo_{id(color)}", parent=e["subtitulo"], textColor=color)


def _logo_isotipo(alto_mm: float = 26) -> list:
    """Imagen del isotipo naranja para la portada. Si el archivo falta o está
    corrupto devuelve [] (portada solo-texto): un logo ausente no tumba el
    reporte. La ruta es relativa a __file__, independiente del cwd."""
    if not _RUTA_ISOTIPO.is_file():
        return []
    try:
        reader = ImageReader(str(_RUTA_ISOTIPO))
        iw, ih = reader.getSize()
        alto = alto_mm * mm
        ancho = min(alto * iw / ih, 70 * mm)
        return [Image(str(_RUTA_ISOTIPO), width=ancho, height=alto, hAlign="CENTER")]
    except Exception:
        return []


def _fondo_portada(canvas, documento) -> None:
    """Fondo naranja muy claro SOLO en la página 1 (portada); después el pie
    de página normal. Se registra como onFirstPage."""
    canvas.saveState()
    canvas.setFillColor(est.NARANJA_TINTE)
    canvas.rect(0, 0, documento.pagesize[0], documento.pagesize[1], stroke=0, fill=1)
    canvas.restoreState()
    _pie_pagina(canvas, documento)


def _kpi_tarjeta(
    e: dict,
    etiqueta: str,
    valor: str,
    color_acento,
    tinte,
    ancho: float,
    pendiente_texto: str | None = None,
    comparacion_texto: str | None = None,
) -> Table:
    contenido = [Paragraph(etiqueta, e["kpi_etiqueta"]), Paragraph(valor, e["kpi_valor"])]
    if pendiente_texto:
        contenido.append(Paragraph(pendiente_texto, e["kpi_pendiente"]))
    if comparacion_texto:
        contenido.append(Paragraph(comparacion_texto, e["kpi_comparacion"]))
    tarjeta = Table([[contenido]], colWidths=[ancho])
    tarjeta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), tinte),
                ("LINEABOVE", (0, 0), (-1, 0), 3, color_acento),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tarjeta


def _tabla_kpis(e: dict, datos: dict, ancho_util: float) -> Table:
    kpi = datos["kpi"]
    summary = datos["summary"]
    creator_usage = datos["creator_usage"]
    general_expenses_monthly = datos["general_expenses_monthly"]
    operational_total = datos["operational_dashboard"].total
    comparacion = datos["period_comparison"]

    creadores_activos = sum(1 for c in creator_usage if c.spent > 0 or c.pending > 0)
    gastos_generales_total = sum(m.total for m in general_expenses_monthly)

    # Solo hay comparación (mes/año pasado) en modo periodo único — en un
    # rango de varios meses no hay "el periodo anterior" con el que comparar.
    cmp_gastado = cmp_generales = cmp_operativos = None
    if comparacion.is_single_period and comparacion.anterior:
        label = comparacion.label_comparacion
        cmp_gastado = _texto_comparacion(comparacion.actual.total_spent, comparacion.anterior.total_spent, label)
        cmp_generales = _texto_comparacion(
            comparacion.actual.general_expenses_total, comparacion.anterior.general_expenses_total, label
        )
        cmp_operativos = _texto_comparacion(
            comparacion.actual.operational_expenses_total, comparacion.anterior.operational_expenses_total, label
        )

    ancho_col = ancho_util / 4 - 6
    # Página de resumen: TODAS las tarjetas en naranja (un color por tema).
    colores = [(est.NARANJA_GO, est.NARANJA_TINTE)] * 4

    fila1 = [
        _kpi_tarjeta(e, "PRESUPUESTO TOTAL", _moneda(kpi.total_budget), *colores[0], ancho_col),
        _kpi_tarjeta(e, "TOTAL GASTADO", _moneda(kpi.total_spent), *colores[1], ancho_col),
        _kpi_tarjeta(e, "TOTAL DISPONIBLE", _moneda(kpi.total_remaining), *colores[2], ancho_col),
        _kpi_tarjeta(e, "MARCAS ACTIVAS", _entero(summary.active_brands), *colores[3], ancho_col),
    ]
    fila2 = [
        _kpi_tarjeta(
            e, "GASTADO EN EL PERÍODO", _moneda(summary.total_spent), *colores[0], ancho_col,
            pendiente_texto=f"+{_moneda(summary.pending_total)} pendientes" if summary.pending_total > 0 else None,
            comparacion_texto=cmp_gastado,
        ),
        _kpi_tarjeta(
            e, "TICKETS", _entero(summary.ticket_count), *colores[1], ancho_col,
            pendiente_texto=f"{summary.pending_count} pendientes por confirmar" if summary.pending_count > 0 else None,
        ),
        _kpi_tarjeta(e, "CREADORES ACTIVOS", _entero(creadores_activos), *colores[2], ancho_col),
        _kpi_tarjeta(
            e, "GASTOS GENERALES", _moneda(gastos_generales_total), *colores[3], ancho_col,
            comparacion_texto=cmp_generales,
        ),
    ]
    # Tercera fila: un solo tile (espejo del layout en pantalla, que también
    # deja "Gastos Operativos" solo en su propia fila) — se rellenan las
    # celdas vacías con "" para que la tabla siga teniendo 4 columnas.
    fila3 = [
        _kpi_tarjeta(
            e, "GASTOS OPERATIVOS", _moneda(operational_total), *colores[0], ancho_col,
            comparacion_texto=cmp_operativos,
        ),
        "", "", "",
    ]

    tabla = Table([fila1, fila2, fila3], colWidths=[ancho_util / 4] * 4, hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tabla


def _titulo_seccion(e: dict, texto: str, color) -> list:
    """Título de sección con una marca de color a la izquierda y una barra de
    acento debajo — reemplaza la línea gris plana del primer borrador."""
    marca = Table([[""]], colWidths=[4], rowHeights=[13])
    marca.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
    fila = Table(
        [[marca, Paragraph(texto, e["seccion_titulo"])]],
        colWidths=[10, None],
    )
    fila.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    linea = Table([[""]], colWidths=["100%"], rowHeights=[1.5])
    linea.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
    return [fila, Spacer(1, 3), linea, Spacer(1, 8)]


def _caja_sin_datos(e: dict, texto: str, ancho_util: float) -> Table:
    caja = Table([[Paragraph(texto, e["sin_datos"])]], colWidths=[ancho_util])
    caja.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), est.GRIS_CLARO),
                ("BOX", (0, 0), (-1, -1), 0.5, est.LINEA),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return caja


def _tabla_simple(e: dict, encabezados: list[str], filas: list[list[str]], anchos: list[float]) -> Table:
    cabecera = [Paragraph(h, e["tabla_encabezado"]) for h in encabezados]
    cuerpo = []
    for fila in filas:
        cuerpo.append(
            [Paragraph(fila[0], e["tabla_celda"])]
            + [Paragraph(v, e["tabla_num"]) for v in fila[1:]]
        )
    tabla = Table([cabecera] + cuerpo, colWidths=anchos, hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), est.GRIS_CLARO),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [est.FONDO, est.GRIS_ZEBRA]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, est.TEXTO),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
            ]
        )
    )
    return tabla


_ORDEN_PRIORIDAD = {"alta": 0, "media": 1, "baja": 2}
_LABEL_PRIORIDAD = {"alta": "Alta", "media": "Media", "baja": "Baja"}


# ── Una función por página temática ─────────────────────────────────────────


def _pagina_portada(e: dict, datos: dict, periodo: str, generado_txt: str, ancho_util: float) -> list:
    """Página 1, tema naranja: solo logo + datos de presentación, centrado.
    El fondo de tinte naranja lo pinta `_fondo_portada` (onFirstPage)."""
    flujo: list = [Spacer(1, 24 * mm)]
    flujo.extend(_logo_isotipo())
    flujo.append(Spacer(1, 10 * mm))
    flujo.append(Paragraph("GRUPO ORTIZ", e["portada_org"]))
    flujo.append(Paragraph("GOCreate", e["portada_gocreate"]))
    flujo.append(Spacer(1, 6 * mm))
    barra = Table([[""]], colWidths=[40 * mm], rowHeights=[1.5], hAlign="CENTER")
    barra.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), est.NARANJA_GO)]))
    flujo.append(barra)
    flujo.append(Spacer(1, 6 * mm))
    flujo.append(Paragraph("Control de Presupuestos — Reporte del Dashboard", e["portada_titulo"]))
    flujo.append(Spacer(1, 8 * mm))
    flujo.append(Paragraph(f"Período: {periodo}", e["portada_meta"]))
    generado_por = datos.get("generated_by_name")
    flujo.append(
        Paragraph(
            f"Generado: {generado_txt}" + (f" por {generado_por}" if generado_por else ""),
            e["portada_meta"],
        )
    )
    return flujo


def _pagina_creadores(e: dict, datos: dict, es_periodo_unico: bool, ancho_util: float) -> list:
    """Página 2, tema VERDE: Transacciones por Mes (oculta en periodo único),
    Gastos por Marca (gráfica + tabla), Uso de Presupuesto por Creador
    (gráfica + tabla) y Tickets Subidos por Día (movido aquí desde la vieja
    sección ACTIVIDAD)."""
    flujo: list = [PageBreak()]
    flujo.extend(_titulo_seccion(e, "PRESUPUESTOS DE CREADORES", _COLOR_SECCION_CREADORES))
    hubo = False

    monthly = datos["monthly"]
    if monthly and not es_periodo_unico:
        hubo = True
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Transacciones por Mes", _COLOR_SECCION_CREADORES),
                    graf.grafica_vertical(
                        [_mes_label(m.month) for m in monthly],
                        [
                            ("Aprobado", [m.total for m in monthly]),
                            ("Pendiente por confirmar", [m.pending_total for m in monthly]),
                        ],
                        ancho_util,
                        170,
                        colores=[est.VERDE, est.VERDE_CLARO],
                    ),
                ]
            )
        )

    brand_spend = [b for b in datos["brand_spend"] if b.total_spent > 0]
    brand_spend.sort(key=lambda b: (_ORDEN_PRIORIDAD.get(b.priority, 3), -b.total_spent))
    if brand_spend:
        hubo = True
        flujo.append(Spacer(1, 4 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos por Marca", _COLOR_SECCION_CREADORES),
                    graf.grafica_horizontal(
                        [b.brand_name for b in brand_spend],
                        [("Gasto", [b.total_spent for b in brand_spend])],
                        ancho_util,
                        max(90, 26 * len(brand_spend)),
                        colores=[est.VERDE],
                    ),
                ]
            )
        )
        flujo.append(Spacer(1, 2 * mm))
        # Tabla FUERA del KeepTogether: puede partir entre páginas sin dejar
        # un hueco gigante cuando hay muchas marcas.
        flujo.append(
            _tabla_simple(
                e,
                ["Marca", "Prioridad", "Total gastado"],
                [
                    [b.brand_name, _LABEL_PRIORIDAD.get(b.priority, b.priority), _moneda(b.total_spent)]
                    for b in brand_spend
                ],
                [ancho_util * 0.5, ancho_util * 0.2, ancho_util * 0.3],
            )
        )

    creator_usage = [c for c in datos["creator_usage"] if c.spent > 0 or c.pending > 0]
    creator_usage.sort(key=lambda c: c.spent, reverse=True)
    if creator_usage:
        hubo = True
        flujo.append(Spacer(1, 5 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Uso de Presupuesto por Creador", _COLOR_SECCION_CREADORES),
                    graf.grafica_horizontal(
                        [c.name for c in creator_usage],
                        [
                            ("% Usado", [round(c.percentage, 1) for c in creator_usage]),
                            (
                                "% Pendiente",
                                [
                                    round((c.pending / c.initial_budget) * 100, 1) if c.initial_budget > 0 else 0.0
                                    for c in creator_usage
                                ],
                            ),
                        ],
                        ancho_util,
                        max(90, 26 * len(creator_usage)),
                        formato_valor=graf._porcentaje,
                        colores=[est.VERDE, est.VERDE_CLARO],
                    ),
                ]
            )
        )
        flujo.append(Spacer(1, 2 * mm))
        flujo.append(
            _tabla_simple(
                e,
                ["Creador", "Gastado", "Pendiente", "Ciclo vigente", "% usado"],
                [
                    [
                        c.name, _moneda(c.spent), _moneda(c.pending),
                        _moneda(c.initial_budget), f"{c.percentage:.1f}%",
                    ]
                    for c in creator_usage
                ],
                [ancho_util * 0.28, ancho_util * 0.18, ancho_util * 0.18, ancho_util * 0.18, ancho_util * 0.18],
            )
        )

    tpd = datos["tickets_per_day"]
    if tpd:
        hubo = True
        flujo.append(Spacer(1, 4 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Tickets Subidos por Día", _COLOR_SECCION_CREADORES),
                    graf.grafica_vertical(
                        [_dia_label(t.day) for t in tpd],
                        [("Tickets", [t.count for t in tpd])],
                        ancho_util,
                        160,
                        formato_valor=_entero,
                        categorias_densas=len(tpd) > 15,
                        colores=[est.VERDE],
                    ),
                ]
            )
        )

    if not hubo:
        flujo.append(_caja_sin_datos(e, "Sin actividad de presupuestos de creadores en este período.", ancho_util))
    return flujo


def _pagina_gastos_generales(e: dict, datos: dict, es_periodo_unico: bool, ancho_util: float) -> list:
    """Página 3, tema AZUL: Gastos Generales por Mes (oculta en periodo único),
    Gastos Generales por Marca (solo periodo único) y la tabla de Mayores
    Gastos Generales del período (con su marca)."""
    flujo: list = [PageBreak()]
    flujo.extend(_titulo_seccion(e, "GASTOS GENERALES", _COLOR_SECCION_GENERALES))
    hubo = False

    gem = datos["general_expenses_monthly"]
    if gem and not es_periodo_unico:
        hubo = True
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos Generales por Mes", _COLOR_SECCION_GENERALES),
                    graf.grafica_vertical(
                        [_mes_label(m.month) for m in gem],
                        [("Gasto general", [m.total for m in gem])],
                        ancho_util,
                        150,
                        colores=[est.CIELO],
                    ),
                ]
            )
        )

    if es_periodo_unico:
        gxb = [b for b in datos.get("general_expenses_by_brand", []) if b.total_spent > 0]
        gxb.sort(key=lambda b: (_ORDEN_PRIORIDAD.get(b.priority, 3), -b.total_spent))
        if gxb:
            hubo = True
            flujo.append(
                KeepTogether(
                    [
                        _color_paragraph(e, "subtitulo", "Gastos Generales por Marca", _COLOR_SECCION_GENERALES),
                        graf.grafica_horizontal(
                            [b.brand_name for b in gxb],
                            [("Gasto", [b.total_spent for b in gxb])],
                            ancho_util,
                            max(90, 26 * len(gxb)),
                            colores=[est.CIELO],
                        ),
                    ]
                )
            )
            flujo.append(Spacer(1, 2 * mm))
            flujo.append(
                _tabla_simple(
                    e,
                    ["Marca", "Prioridad", "Total gastado"],
                    [
                        [b.brand_name, _LABEL_PRIORIDAD.get(b.priority, b.priority), _moneda(b.total_spent)]
                        for b in gxb
                    ],
                    [ancho_util * 0.5, ancho_util * 0.2, ancho_util * 0.3],
                )
            )

    # Dato específico de esta página (además de las gráficas generales): los
    # gastos generales individuales más grandes del período, con su marca.
    top_g = datos.get("top_generales") or []
    if top_g:
        hubo = True
        flujo.append(Spacer(1, 5 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Mayores Gastos Generales", _COLOR_SECCION_GENERALES),
                    _tabla_simple(
                        e,
                        ["Rank", "Descripción", "Marca", "Fecha", "Monto"],
                        [
                            [
                                str(i + 1),
                                t.descripcion,
                                t.etiqueta,
                                _fecha_larga(t.fecha),
                                _moneda(t.monto),
                            ]
                            for i, t in enumerate(top_g)
                        ],
                        [ancho_util * 0.08, ancho_util * 0.42, ancho_util * 0.18, ancho_util * 0.16, ancho_util * 0.16],
                    ),
                ]
            )
        )

    if not hubo:
        flujo.append(_caja_sin_datos(e, "Sin gastos generales en este período.", ancho_util))
    return flujo


def _pagina_operativos(e: dict, datos: dict, es_periodo_unico: bool, ancho_util: float) -> list:
    """Página 4, tema MORADO: Gastos Operativos por Mes (oculta en periodo
    único), Gastos Operativos por Rubro (gráfica + tabla de totales) y la
    tabla de Mayores Gastos Operativos del período (con su rubro)."""
    flujo: list = [PageBreak()]
    flujo.extend(_titulo_seccion(e, "GASTOS OPERATIVOS", _COLOR_SECCION_OPERATIVOS))
    hubo = False

    op = datos["operational_dashboard"]
    if op.mensual and not es_periodo_unico:
        hubo = True
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos Operativos por Mes", _COLOR_SECCION_OPERATIVOS),
                    graf.grafica_vertical(
                        [_mes_label(m.month) for m in op.mensual],
                        [("Gasto operativo", [m.total for m in op.mensual])],
                        ancho_util,
                        150,
                        colores=[est.VIOLETA],
                    ),
                ]
            )
        )

    rubros = [r for r in op.por_rubro if r.total > 0]
    if rubros:
        hubo = True
        flujo.append(Spacer(1, 4 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos Operativos por Rubro", _COLOR_SECCION_OPERATIVOS),
                    graf.grafica_horizontal(
                        [r.rubro_nombre for r in rubros],
                        [("Gasto", [r.total for r in rubros])],
                        ancho_util,
                        max(90, 26 * len(rubros)),
                        colores=[est.VIOLETA],
                    ),
                ]
            )
        )
        flujo.append(Spacer(1, 2 * mm))
        # Tabla con los totales exactos por rubro (la gráfica no da la cifra).
        flujo.append(
            _tabla_simple(
                e,
                ["Rubro", "Gastos", "Total"],
                [[r.rubro_nombre, _entero(r.count), _moneda(r.total)] for r in rubros],
                [ancho_util * 0.5, ancho_util * 0.2, ancho_util * 0.3],
            )
        )

    # Dato específico de esta página (además de las gráficas generales): los
    # gastos operativos individuales más grandes del período, con su rubro.
    top_o = datos.get("top_operativos") or []
    if top_o:
        hubo = True
        flujo.append(Spacer(1, 5 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Mayores Gastos Operativos", _COLOR_SECCION_OPERATIVOS),
                    _tabla_simple(
                        e,
                        ["Rank", "Descripción", "Rubro", "Fecha", "Monto"],
                        [
                            [
                                str(i + 1),
                                t.descripcion,
                                t.etiqueta,
                                _fecha_larga(t.fecha),
                                _moneda(t.monto),
                            ]
                            for i, t in enumerate(top_o)
                        ],
                        [ancho_util * 0.08, ancho_util * 0.42, ancho_util * 0.18, ancho_util * 0.16, ancho_util * 0.16],
                    ),
                ]
            )
        )

    if not hubo:
        flujo.append(_caja_sin_datos(e, "Sin gastos operativos en este período.", ancho_util))
    return flujo


def _pagina_resumen(e: dict, datos: dict, es_periodo_unico: bool, ancho_util: float) -> list:
    """Página 5, tema NARANJA: grilla de KPIs (toda naranja), donut de
    distribución del gasto, comparación vs periodo anterior (solo periodo
    único) y Top 3 de gastos individuales. Sin caja "sin datos": los KPIs
    siempre se dibujan."""
    flujo: list = [PageBreak()]
    flujo.extend(_titulo_seccion(e, "RESUMEN GENERAL", _COLOR_SECCION_RESUMEN))
    flujo.append(_tabla_kpis(e, datos, ancho_util))

    # Donut: cada rebanada es un tema, así que usa el color de su tema (verde
    # creadores, azul generales, morado operativos) — calculado aquí mismo
    # con los datos que ya trae el diccionario, sin lógica de negocio nueva.
    valores_donut = [
        ("Creadores", datos["summary"].total_spent),
        ("Gastos Generales", sum(m.total for m in datos["general_expenses_monthly"])),
        ("Gastos Operativos", datos["operational_dashboard"].total),
    ]
    hay_donut = any(v > 0 for _, v in valores_donut)
    comparacion = datos["period_comparison"]
    hay_comparacion = es_periodo_unico and comparacion.anterior is not None

    # En periodo único ambas gráficas son chicas (3 categorías cada una): van
    # LADO A LADO para que el resumen quepa en una página. Si solo hay una,
    # ocupa el ancho completo.
    if hay_donut or hay_comparacion:
        ancho_col = ancho_util / 2 if (hay_donut and hay_comparacion) else ancho_util
        columnas = []
        if hay_donut:
            columnas.append(
                [
                    Paragraph("Distribución del Gasto del Período", _subtitulo_estilo(e, _COLOR_SECCION_RESUMEN)),
                    graf.grafica_donut(
                        valores_donut, [est.VERDE, est.CIELO, est.VIOLETA], ancho_col,
                        alto=150 if ancho_col == ancho_util else 120,
                    ),
                ]
            )
        if hay_comparacion:
            columnas.append(
                [
                    Paragraph("Este Período vs Anterior", _subtitulo_estilo(e, _COLOR_SECCION_RESUMEN)),
                    graf.grafica_vertical(
                        ["Creadores", "Gastos Generales", "Gastos Operativos"],
                        [
                            (
                                "Este período",
                                [
                                    comparacion.actual.total_spent,
                                    comparacion.actual.general_expenses_total,
                                    comparacion.actual.operational_expenses_total,
                                ],
                            ),
                            (
                                "Anterior",
                                [
                                    comparacion.anterior.total_spent,
                                    comparacion.anterior.general_expenses_total,
                                    comparacion.anterior.operational_expenses_total,
                                ],
                            ),
                        ],
                        ancho_col,
                        150,
                        colores=[est.NARANJA_GO, est.NARANJA_CLARO],
                    ),
                ]
            )
        flujo.append(Spacer(1, 5 * mm))
        if len(columnas) > 1:
            flujo.append(
                KeepTogether([Table(columnas, colWidths=[ancho_col] * len(columnas), hAlign="CENTER")])
            )
        else:
            flujo.append(KeepTogether(columnas[0]))

    top = datos.get("top_expenses") or []
    if top:
        flujo.append(Spacer(1, 5 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Mayores Gastos Individuales del Período", _COLOR_SECCION_RESUMEN),
                    _tabla_simple(
                        e,
                        ["Rank", "Tipo", "Descripción", "Fecha", "Monto"],
                        [
                            [
                                str(i + 1),
                                "General" if t.tipo == "general" else "Operativo",
                                t.descripcion,
                                _fecha_larga(t.fecha),
                                _moneda(t.monto),
                            ]
                            for i, t in enumerate(top)
                        ],
                        [ancho_util * 0.08, ancho_util * 0.16, ancho_util * 0.42, ancho_util * 0.18, ancho_util * 0.16],
                    ),
                ]
            )
        )
    return flujo


def construir(datos: dict, ancho_util: float) -> list:
    """Flowables del reporte completo, en orden: una página por tema, cada
    tema abre con PageBreak (nunca un PageBreak final — crearía una página en
    blanco)."""
    e = est.estilos()
    flujo: list = []

    generado = datos.get("generated_at")
    periodo = _periodo_label(datos.get("start_date"), datos.get("end_date"))
    generado_txt = _fecha_hora_larga(generado) if generado else "—"
    # Modo periodo único (un solo mes o año de calendario, ver
    # crud.detectar_periodo_unico): las gráficas "por mes" degeneran a una
    # sola barra ahí, así que se ocultan a favor de los desgloses por
    # categoría que ya existen (por marca/rubro/creador) — mismo criterio
    # que en pantalla (Dashboard.jsx), nunca decidido dos veces.
    es_periodo_unico = datos["period_comparison"].is_single_period

    flujo.extend(_pagina_portada(e, datos, periodo, generado_txt, ancho_util))
    flujo.extend(_pagina_creadores(e, datos, es_periodo_unico, ancho_util))
    flujo.extend(_pagina_gastos_generales(e, datos, es_periodo_unico, ancho_util))
    flujo.extend(_pagina_operativos(e, datos, es_periodo_unico, ancho_util))
    flujo.extend(_pagina_resumen(e, datos, es_periodo_unico, ancho_util))
    return flujo


def _pie_pagina(canvas, documento) -> None:
    """Footer en cada página: línea + numeración. `onFirstPage`/`onLaterPages`
    reciben `(canvas, doc)`; se registra igual para ambos casos."""
    e = est.estilos()
    canvas.saveState()
    y = est.MARGENES["bottom"] - 2 * mm
    ancho_pagina = documento.pagesize[0]
    canvas.setStrokeColor(est.LINEA)
    canvas.setLineWidth(0.5)
    canvas.line(est.MARGENES["left"], y + 12, ancho_pagina - est.MARGENES["right"], y + 12)
    texto = f"GOCreate · Grupo Ortiz · Página {canvas.getPageNumber()}"
    p = Paragraph(texto, e["pie_pagina"])
    ancho_util = ancho_pagina - est.MARGENES["left"] - est.MARGENES["right"]
    p.wrapOn(canvas, ancho_util, 20)
    p.drawOn(canvas, est.MARGENES["left"], y)
    canvas.restoreState()


def generar_pdf(datos: dict) -> bytes:
    """Arma el PDF completo en memoria y devuelve sus bytes. Nunca escribe a
    disco — este reporte no tiene identidad que versionar (ver docstring del
    módulo)."""
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=est.MARGENES["left"],
        rightMargin=est.MARGENES["right"],
        topMargin=est.MARGENES["top"],
        bottomMargin=est.MARGENES["bottom"],
        title="Reporte de Presupuesto — GOCreate",
        author="GOCreate",
        subject="Reporte de presupuesto de creadores de contenido",
    )
    documento.build(
        construir(datos, documento.width),
        onFirstPage=_fondo_portada,
        onLaterPages=_pie_pagina,
    )
    return buffer.getvalue()
