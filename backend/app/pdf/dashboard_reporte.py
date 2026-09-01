"""Reporte PDF del Dashboard de Presupuestos: convierte datos ya resueltos
(schemas Pydantic, mismos que ya ve la pantalla) en flowables de reportlab.

Generado siempre en memoria (`generar_pdf` devuelve `bytes`, nunca escribe a
disco) — a diferencia de la carta responsiva (`responsiva.py`), este reporte
no tiene identidad propia que versionar: cada descarga esta atada a un filtro
de fechas que cambia, así que no hay nada que reusar entre requests.

Este módulo no toca la base de datos: recibe un diccionario con los datos ya
consultados (mismo criterio que `plantilla.py`) y devuelve flowables/bytes.

Diseño: banner de encabezado (fondo oscuro), tarjetas de KPI con acento de
color rotando entre los 4 acentos que ya se ven en pantalla (naranja/turquesa/
cielo/violeta — `Dashboard.jsx` `ACCENTS`), títulos de sección con marca de
color + barra de acento, tablas con encabezado sombreado y renglón alterno, y
pie de página con numeración. Una gráfica/tabla sin datos se OMITE por
completo (no se dibuja un recuadro vacío ni un aviso individual); solo si una
sección entera queda sin nada se muestra un único aviso, para no llenar el
reporte de mensajes de "sin datos" repetidos.
"""

from __future__ import annotations

import io
from datetime import date, datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
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

# Colores de sección, en el orden en que aparecen en el reporte — cada bloque
# tiene su propia identidad en vez de repetir siempre naranja.
_COLOR_SECCION_CREADORES = est.NARANJA_GO
_COLOR_SECCION_GASTOS = est.TURQUESA
_COLOR_SECCION_ACTIVIDAD = est.VIOLETA


def _moneda(v: float) -> str:
    return f"${v:,.2f}"


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


def _banner_encabezado(e: dict, periodo: str, generado_txt: str, generado_por: str | None, ancho_util: float) -> Table:
    izquierda = [
        Paragraph("GRUPO ORTIZ", e["banner_titulo"]),
        Paragraph("Control de Presupuestos — Reporte del Dashboard", e["banner_subtitulo"]),
    ]
    derecha = [
        Paragraph(f"Período: {periodo}", e["banner_meta_der"]),
        Paragraph(
            f"Generado: {generado_txt}" + (f" por {generado_por}" if generado_por else ""),
            e["banner_meta_der"],
        ),
    ]
    banner = Table([[izquierda, derecha]], colWidths=[ancho_util * 0.6, ancho_util * 0.4])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), est.TEXTO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (0, -1), 14),
                ("RIGHTPADDING", (-1, 0), (-1, -1), 14),
                ("LINEBELOW", (0, 0), (-1, -1), 3, est.NARANJA_GO),
            ]
        )
    )
    return banner


def _kpi_tarjeta(e: dict, etiqueta: str, valor: str, color_acento, tinte, ancho: float, pendiente_texto: str | None = None) -> Table:
    contenido = [Paragraph(etiqueta, e["kpi_etiqueta"]), Paragraph(valor, e["kpi_valor"])]
    if pendiente_texto:
        contenido.append(Paragraph(pendiente_texto, e["kpi_pendiente"]))
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

    creadores_activos = sum(1 for c in creator_usage if c.spent > 0 or c.pending > 0)
    gastos_generales_total = sum(m.total for m in general_expenses_monthly)

    ancho_col = ancho_util / 4 - 6
    colores = est.TINTES  # [(acento, tinte), ...] x4, mismo orden en ambas filas

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
        ),
        _kpi_tarjeta(
            e, "TICKETS", _entero(summary.ticket_count), *colores[1], ancho_col,
            pendiente_texto=f"{summary.pending_count} pendientes por confirmar" if summary.pending_count > 0 else None,
        ),
        _kpi_tarjeta(e, "CREADORES ACTIVOS", _entero(creadores_activos), *colores[2], ancho_col),
        _kpi_tarjeta(e, "GASTOS GENERALES", _moneda(gastos_generales_total), *colores[3], ancho_col),
    ]

    tabla = Table([fila1, fila2], colWidths=[ancho_util / 4] * 4, hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
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


def construir(datos: dict, ancho_util: float) -> list:
    """Flowables del reporte completo, en orden."""
    e = est.estilos()
    flujo: list = []

    generado = datos.get("generated_at")
    periodo = _periodo_label(datos.get("start_date"), datos.get("end_date"))
    generado_txt = _fecha_hora_larga(generado) if generado else "—"

    # ── Encabezado ───────────────────────────────────────────────────────
    flujo.append(_banner_encabezado(e, periodo, generado_txt, datos.get("generated_by_name"), ancho_util))
    flujo.append(Spacer(1, 5 * mm))
    flujo.append(_tabla_kpis(e, datos, ancho_util))
    flujo.append(Spacer(1, 5 * mm))

    # ── Sección: Presupuestos de Creadores ──────────────────────────────
    flujo.extend(_titulo_seccion(e, "PRESUPUESTOS DE CREADORES", _COLOR_SECCION_CREADORES))
    hubo_contenido_creadores = False

    monthly = datos["monthly"]
    if monthly:
        hubo_contenido_creadores = True
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
                    ),
                ]
            )
        )

    brand_spend = [b for b in datos["brand_spend"] if b.total_spent > 0]
    brand_spend.sort(key=lambda b: (_ORDEN_PRIORIDAD.get(b.priority, 3), -b.total_spent))
    if brand_spend:
        hubo_contenido_creadores = True
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
                        color_principal=_COLOR_SECCION_CREADORES,
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
                    for b in brand_spend
                ],
                [ancho_util * 0.5, ancho_util * 0.2, ancho_util * 0.3],
            )
        )

    creator_usage = [c for c in datos["creator_usage"] if c.spent > 0 or c.pending > 0]
    creator_usage.sort(key=lambda c: c.spent, reverse=True)
    if creator_usage:
        hubo_contenido_creadores = True
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

    if not hubo_contenido_creadores:
        flujo.append(_caja_sin_datos(e, "Sin actividad de presupuestos de creadores en este período.", ancho_util))

    # ── Sección: Gastos Generales y Operativos (unificados, misma UI) ───
    flujo.append(Spacer(1, 7 * mm))
    flujo.extend(_titulo_seccion(e, "GASTOS GENERALES Y OPERATIVOS", _COLOR_SECCION_GASTOS))
    hubo_contenido_gastos = False

    gem = datos["general_expenses_monthly"]
    if gem:
        hubo_contenido_gastos = True
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos Generales por Mes", _COLOR_SECCION_GASTOS),
                    graf.grafica_vertical(
                        [_mes_label(m.month) for m in gem],
                        [("Gasto general", [m.total for m in gem])],
                        ancho_util,
                        150,
                        color_principal=est.CIELO,
                    ),
                ]
            )
        )

    op = datos["operational_dashboard"]
    if op.mensual:
        hubo_contenido_gastos = True
        flujo.append(Spacer(1, 4 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos Operativos por Mes", _COLOR_SECCION_GASTOS),
                    graf.grafica_vertical(
                        [_mes_label(m.month) for m in op.mensual],
                        [("Gasto operativo", [m.total for m in op.mensual])],
                        ancho_util,
                        150,
                        color_principal=est.VIOLETA,
                    ),
                ]
            )
        )
    rubros = [r for r in op.por_rubro if r.total > 0]
    if rubros:
        hubo_contenido_gastos = True
        flujo.append(Spacer(1, 4 * mm))
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Gastos Operativos por Rubro", _COLOR_SECCION_GASTOS),
                    graf.grafica_horizontal(
                        [r.rubro_nombre for r in rubros],
                        [("Gasto", [r.total for r in rubros])],
                        ancho_util,
                        max(90, 26 * len(rubros)),
                        color_principal=est.TURQUESA,
                    ),
                ]
            )
        )

    if not hubo_contenido_gastos:
        flujo.append(_caja_sin_datos(e, "Sin gastos generales ni operativos en este período.", ancho_util))

    # ── Sección: Actividad ───────────────────────────────────────────────
    flujo.append(Spacer(1, 7 * mm))
    flujo.extend(_titulo_seccion(e, "ACTIVIDAD", _COLOR_SECCION_ACTIVIDAD))

    tpd = datos["tickets_per_day"]
    if tpd:
        flujo.append(
            KeepTogether(
                [
                    _color_paragraph(e, "subtitulo", "Tickets Subidos por Día", _COLOR_SECCION_ACTIVIDAD),
                    graf.grafica_vertical(
                        [_dia_label(t.day) for t in tpd],
                        [("Tickets", [t.count for t in tpd])],
                        ancho_util,
                        160,
                        formato_valor=_entero,
                        categorias_densas=len(tpd) > 15,
                        color_principal=_COLOR_SECCION_ACTIVIDAD,
                    ),
                ]
            )
        )
    else:
        flujo.append(_caja_sin_datos(e, "Sin tickets subidos en este período.", ancho_util))

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
        onFirstPage=_pie_pagina,
        onLaterPages=_pie_pagina,
    )
    return buffer.getvalue()
