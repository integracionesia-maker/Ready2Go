"""Reporte HTML del Dashboard de Presupuestos (reemplaza al PDF de reportlab).

Un solo archivo autocontenido pensado para COMPARTIR: los datos ya resueltos
(mismos schemas que ve la pantalla) se incrustan como JSON dentro de la
plantilla y el JS del propio archivo los pinta — el HTML nunca consulta la API
ni necesita sesión. Lo único externo son las fuentes de Google, con respaldo
de sistema si no hay internet.

Este módulo no toca la base de datos: recibe un diccionario con los datos ya
consultados (lo arma `routers/dashboard.py`) y devuelve el HTML como `str`.
Aquí también viven las alertas y los textos automáticos: reglas simples sobre
esos mismos datos, sin lógica de negocio nueva.

Seguridad: nombres de creadores/marcas y descripciones de gastos son texto
libre. El JSON se serializa con `<`, `>` y `&` escapados (nada puede cerrar el
`<script>` ni abrir un comentario HTML) y la plantilla escapa todo valor antes
de usar `innerHTML`.
"""

from __future__ import annotations

import base64
import calendar
import html
import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

__all__ = ["construir_datos", "generar_html"]

_PLANTILLA = Path(__file__).parent / "reporte_dashboard_plantilla.html"
_ASSETS = Path(__file__).parent / "reporte_assets"

# Marcador de la plantilla -> archivo en `reporte_assets/`. Se incrustan como
# base64 para que el HTML se vea igual en cualquier computadora, sin internet:
# fuentes (Nunito/Inter/JetBrains Mono, los mismos respaldos que usa la app
# mientras llegan Blauer Nue/Conthic). A propósito NO se incrustan imágenes:
# nada que pueda fallar al compartir el archivo por correo/chat/visores.
_RECURSOS = {
    "__F_NUNITO_700__": "nunito-latin-700-normal.woff2",
    "__F_NUNITO_800__": "nunito-latin-800-normal.woff2",
    "__F_INTER_400__": "inter-latin-400-normal.woff2",
    "__F_INTER_600__": "inter-latin-600-normal.woff2",
    "__F_MONO_500__": "jetbrains-mono-latin-500-normal.woff2",
}

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
MESES_ABREV = [m[:3] for m in MESES]

_LABEL_PRIORIDAD = {"alta": "Alta", "media": "Media", "baja": "Baja"}

# Umbrales de las alertas automáticas.
_UMBRAL_GASTO_UNICO = 0.30  # un solo gasto pesa >= 30% de su sección
_UMBRAL_SUBIDA_PCT = 50.0  # una categoría sube >= 50% vs el periodo anterior...
_UMBRAL_SUBIDA_MONTO = 500.0  # ...y la diferencia es de al menos $500
_MAX_ALERTAS_CICLO = 4
_MAX_ALERTAS_SIN_CICLO = 3
_MAX_ALERTAS = 8


def _moneda(v: float) -> str:
    return f"{'−' if v < 0 else ''}${abs(v):,.2f}"


def _fecha_corta(d: date) -> str:
    return f"{d.day} {MESES_ABREV[d.month - 1]} {d.year}"


def _fecha_numerica(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def _periodo_corto(start: Optional[date], end: Optional[date]) -> str:
    if start and end:
        if start == end:
            return _fecha_corta(start)
        if (start.year, start.month) == (end.year, end.month):
            return f"{start.day} – {end.day} {MESES_ABREV[end.month - 1]} {end.year}"
        return f"{_fecha_corta(start)} – {_fecha_corta(end)}"
    if start:
        return f"Desde {_fecha_corta(start)}"
    if end:
        return f"Hasta {_fecha_corta(end)}"
    return "Todo el histórico"


def _periodo_largo(start: Optional[date], end: Optional[date]) -> str:
    if start and end:
        return f"{_fecha_numerica(start)} – {_fecha_numerica(end)}"
    if start:
        return f"desde {_fecha_numerica(start)}"
    if end:
        return f"hasta {_fecha_numerica(end)}"
    return "todo el histórico"


def _titulo(start: Optional[date], periodo_unico) -> str:
    if periodo_unico and start:
        if periodo_unico[0] == "mes":
            return f"Presupuesto de {MESES[start.month - 1]} {start.year}"
        return f"Presupuesto {start.year}"
    return "Reporte de presupuesto"


def _nombres_cortos(nombres: list[str]) -> list[str]:
    """Primer nombre; si dos coinciden, dos palabras; si aún coinciden, completo."""
    def _palabras(n: str, k: int) -> str:
        return " ".join(n.split()[:k]) or n

    for k in (1, 2):
        cortos = [_palabras(n, k) for n in nombres]
        if len(set(cortos)) == len(cortos):
            return cortos
    return list(nombres)


def _delta(actual: float, anterior: float, label: str) -> Optional[dict]:
    """Texto de comparación ya redactado + dirección (para el color del pill)."""
    if anterior > 0:
        pct = (actual - anterior) / anterior * 100
        flecha = "▲" if pct >= 0 else "▼"
        return {
            "txt": f"{flecha} {abs(pct):.1f}% vs {label}",
            "dir": "up" if pct >= 0 else "down",
            "pct": pct,
        }
    if actual > 0:
        return {"txt": f"Nuevo · {label} $0", "dir": "new", "pct": None}
    return None


def _top_item(t) -> dict:
    return {
        "d": t.descripcion,
        "m": t.etiqueta,
        "f": _fecha_corta(t.fecha),
        "g": float(t.monto),
        "t": "gen" if t.tipo == "general" else "ope",
    }


def _frase_reparto(total: float, partes: list[tuple[str, float]], top_item: Optional[dict], top_cat: Optional[str]) -> Optional[str]:
    """"El 58% del gasto fue en gastos operativos, y 44% de eso es un solo pago: …"."""
    if total <= 0:
        return None
    nombre, valor = max(partes, key=lambda p: p[1])
    if valor <= 0:
        return None
    frase = f"El {valor / total * 100:.0f}% del gasto del periodo fue en {nombre.lower()}"
    if top_item and top_cat == nombre and valor > 0 and top_item["g"] / valor >= _UMBRAL_GASTO_UNICO:
        frase += f", y {top_item['g'] / valor * 100:.0f}% de eso es un solo gasto: {top_item['d']} ({_moneda(top_item['g'])})"
    return frase + "."


def construir_datos(datos: dict) -> dict:
    """Arma el diccionario JSON-serializable que consume la plantilla."""
    summary = datos["summary"]
    kpi = datos["kpi"]
    op = datos["operational_dashboard"]
    comparacion = datos["period_comparison"]
    periodo_unico = datos.get("periodo_unico")
    start: Optional[date] = datos.get("start_date")
    end: Optional[date] = datos.get("end_date")
    generado: Optional[datetime] = datos.get("generated_at")

    cre_total = float(summary.total_spent)
    gen_total = float(sum(m.total for m in datos["general_expenses_monthly"]))
    gen_count = int(sum(m.count for m in datos["general_expenses_monthly"]))
    ope_total = float(op.total)
    ope_count = int(op.count)
    total = cre_total + gen_total + ope_total

    # ── Creadores: solo los que tuvieron actividad en el periodo ───────────
    usage = [c for c in datos["creator_usage"] if c.spent > 0 or c.pending > 0]
    usage.sort(key=lambda c: c.spent, reverse=True)
    cortos = _nombres_cortos([c.name for c in usage])
    creadores = [
        {
            "id": c.creator_id,
            "n": c.name,
            "short": cortos[i],
            "g": float(c.spent),
            "ciclo": float(c.initial_budget),
            "p": float(c.pending),
        }
        for i, c in enumerate(usage)
    ]

    marcas_cre = sorted(
        ({"n": b.brand_name, "g": float(b.total_spent), "p": _LABEL_PRIORIDAD.get(b.priority, b.priority)}
         for b in datos["brand_spend"] if b.total_spent > 0),
        key=lambda b: -b["g"],
    )
    gen_marcas = sorted(
        ({"n": b.brand_name, "g": float(b.total_spent), "p": _LABEL_PRIORIDAD.get(b.priority, b.priority)}
         for b in datos["general_expenses_by_brand"] if b.total_spent > 0),
        key=lambda b: -b["g"],
    )
    ope_rubros = sorted(
        ({"n": r.rubro_nombre, "g": float(r.total), "k": int(r.count)} for r in op.por_rubro if r.total > 0),
        key=lambda r: -r["g"],
    )

    top_all = [_top_item(t) for t in datos["top_expenses"]]
    gen_top = [_top_item(t) for t in datos["top_generales"]]
    ope_top = [_top_item(t) for t in datos["top_operativos"]]

    tpd = datos["tickets_per_day"]
    tickets_dia = [{"d": f"{t.day[8:10]}/{t.day[5:7]}", "n": int(t.count)} for t in tpd]
    tickets_total = sum(t["n"] for t in tickets_dia)
    if tickets_dia:
        pico = max(tickets_dia, key=lambda t: t["n"])
        tickets_sub = (
            f"{tickets_total} tickets en {len(tickets_dia)} "
            f"{'día' if len(tickets_dia) == 1 else 'días'} · el día con más actividad fue el "
            f"{pico['d']} ({pico['n']})"
        )
    else:
        tickets_sub = "Sin tickets subidos en el periodo"

    # ── Comparación contra el periodo anterior (solo periodo único) ────────
    comp = None
    comp_parcial = False
    if comparacion.is_single_period and comparacion.anterior is not None and periodo_unico and start:
        tipo, cmp_start, cmp_end = periodo_unico
        label = MESES[cmp_start.month - 1] if tipo == "mes" else str(cmp_start.year)
        ant, act = comparacion.anterior, comparacion.actual
        items = {}
        for clave, a, p in (
            ("cre", act.total_spent, ant.total_spent),
            ("gen", act.general_expenses_total, ant.general_expenses_total),
            ("ope", act.operational_expenses_total, ant.operational_expenses_total),
        ):
            d = _delta(a, p, label)
            items[clave] = {"a": float(a), "p": float(p), "txt": d["txt"] if d else None, "dir": d["dir"] if d else None,
                            "pct": d["pct"] if d else None}
        comp = {"label": label, "tipo": tipo, "items": items}
        if end:
            fin_periodo = (
                date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
                if tipo == "mes" else date(start.year, 12, 31)
            )
            comp_parcial = end < fin_periodo

    # ── Textos automáticos ─────────────────────────────────────────────────
    top_global = top_all[0] if top_all else None
    reparto = _frase_reparto(
        total,
        [("Creadores", cre_total), ("Gastos generales", gen_total), ("Gastos operativos", ope_total)],
        top_global,
        {"gen": "Gastos generales", "ope": "Gastos operativos"}.get(top_global["t"]) if top_global else None,
    )

    alertas = _alertas(
        creadores=creadores,
        cre_total=cre_total,
        gen_total=gen_total, gen_count=gen_count, gen_top=gen_top,
        ope_total=ope_total, ope_count=ope_count, ope_top=ope_top,
        comp=comp,
        pending_total=float(summary.pending_total), pending_count=int(summary.pending_count),
    )

    notas = _notas(
        creadores=creadores, cre_total=cre_total, summary=summary, tickets_total=tickets_total,
        comp=comp, comp_parcial=comp_parcial, end=end,
        generado=generado,
    )

    return {
        "meta": {
            "titulo": _titulo(start, periodo_unico),
            "periodo": _periodo_corto(start, end),
            "periodo_largo": _periodo_largo(start, end),
            "generado": generado.strftime("%d/%m/%Y %H:%M") if generado else "—",
            "generado_por": datos.get("generated_by_name") or "",
        },
        "totales": {
            "cre": cre_total, "gen": gen_total, "ope": ope_total, "total": total,
            "gen_count": gen_count, "ope_count": ope_count,
            "tickets": int(summary.ticket_count),
            "tickets_pendientes": int(summary.pending_count),
            "pendiente_monto": float(summary.pending_total),
            "marcas_activas": int(summary.active_brands),
        },
        "ciclos": {
            "asignado": float(kpi.total_budget),
            "gastado": float(kpi.total_spent),
            "disponible": float(kpi.total_remaining),
            "creadores_activos": int(kpi.active_creators),
        },
        "comparacion": comp,
        "creadores": creadores,
        "marcas_cre": marcas_cre,
        "tickets_dia": tickets_dia,
        "tickets_sub": tickets_sub,
        "gen_marcas": gen_marcas,
        "gen_top": gen_top,
        "ope_rubros": ope_rubros,
        "ope_top": ope_top,
        "top_all": top_all,
        "alertas": alertas,
        "textos": {"reparto": reparto},
        "notas": notas,
    }


def _alertas(
    *, creadores, cre_total, gen_total, gen_count, gen_top, ope_total, ope_count, ope_top, comp,
    pending_total, pending_count,
) -> list[dict]:
    """Reglas simples sobre los mismos datos del reporte. `k`: bad|warn.
    `go`: [pestaña] o [pestaña, id de creador]. Más graves primero."""
    malas: list[dict] = []
    avisos: list[dict] = []

    excedidos = sorted(
        (c for c in creadores if c["ciclo"] > 0 and c["g"] > c["ciclo"]),
        key=lambda c: c["g"] / c["ciclo"], reverse=True,
    )
    for c in excedidos[:_MAX_ALERTAS_CICLO]:
        malas.append({
            "k": "bad", "ico": "▲",
            "t": f"{c['short']} gastó {c['g'] / c['ciclo'] * 100:.0f}% de su ciclo",
            "s": f"{_moneda(c['g'])} contra {_moneda(c['ciclo'])} asignados",
            "go": ["creadores", c["id"]],
        })

    sin_ciclo = sorted((c for c in creadores if c["ciclo"] <= 0 and c["g"] > 0), key=lambda c: -c["g"])
    for c in sin_ciclo[:_MAX_ALERTAS_SIN_CICLO]:
        share = f" Es el {c['g'] / cre_total * 100:.0f}% de todo el gasto de creadores." if cre_total > 0 else ""
        avisos.append({
            "k": "warn", "ico": "!",
            "t": f"{c['short']} gastó {_moneda(c['g'])} sin presupuesto",
            "s": "No tiene ciclo vigente asignado." + share,
            "go": ["creadores", c["id"]],
        })

    if pending_total > 0:
        avisos.append({
            "k": "warn", "ico": "!",
            "t": f"{_moneda(pending_total)} en tickets pendientes por confirmar",
            "s": f"{pending_count} {'ticket' if pending_count == 1 else 'tickets'} que aún no cuentan contra el ciclo",
            "go": ["creadores"],
        })

    for tab, nombre, tot, cnt, top in (
        ("generales", "gastos generales", gen_total, gen_count, gen_top),
        ("operativos", "gastos operativos", ope_total, ope_count, ope_top),
    ):
        if cnt >= 2 and tot > 0 and top and top[0]["g"] / tot >= _UMBRAL_GASTO_UNICO:
            avisos.append({
                "k": "warn", "ico": "!",
                "t": f"{top[0]['d']}: {_moneda(top[0]['g'])} en un solo gasto",
                "s": f"{top[0]['g'] / tot * 100:.0f}% de los {nombre} del periodo",
                "go": [tab],
            })

    if comp:
        nombres = {"cre": ("Creadores", "creadores"), "gen": ("Gastos generales", "generales"),
                   "ope": ("Gastos operativos", "operativos")}
        for clave, (nombre, tab) in nombres.items():
            it = comp["items"][clave]
            if it["p"] > 0 and it["pct"] is not None and it["pct"] >= _UMBRAL_SUBIDA_PCT and it["a"] - it["p"] >= _UMBRAL_SUBIDA_MONTO:
                avisos.append({
                    "k": "warn", "ico": "▲",
                    "t": f"{nombre} subieron {it['pct']:.0f}% vs {comp['label']}",
                    "s": f"{_moneda(it['a'])} contra {_moneda(it['p'])}",
                    "go": [tab],
                })

    return (malas + avisos)[:_MAX_ALERTAS]


def _notas(*, creadores, cre_total, summary, tickets_total, comp, comp_parcial, end, generado) -> list[dict]:
    """"Notas sobre los datos": lo que conviene saber antes de interpretar el
    reporte (rangos mezclados, totales que no cuadran por diseño). `t` va en
    negritas, `s` es la explicación."""
    notas: list[dict] = []

    hoy = _fecha_numerica(generado.date()) if generado else "la fecha de generación"
    notas.append({
        "t": "Presupuesto asignado, gastado y disponible son de hoy, no del periodo.",
        "s": f"Salen del ciclo vigente de cada creador activo al {hoy}, igual que «Ciclo» y «Usado» en cada tarjeta, "
             "y no cambian con el rango de fechas. El gasto de cada creador sí corresponde al periodo.",
    })

    sin_ciclo = [c for c in creadores if c["ciclo"] <= 0 and c["g"] > 0]
    if sin_ciclo:
        suma = sum(c["g"] for c in sin_ciclo)
        notas.append({
            "t": "Sin ciclo asignado no hay porcentaje que calcular.",
            "s": f"{len(sin_ciclo)} {'creador gastó' if len(sin_ciclo) == 1 else 'creadores gastaron'} "
                 f"{_moneda(suma)} sin presupuesto vigente, por eso su «% usado» aparece como — y no como 0%.",
        })

    suma_cre = sum(c["g"] for c in creadores)
    if abs(suma_cre - cre_total) > 0.01:
        notas.append({
            "t": "El total de creadores no coincide con la suma de sus tarjetas.",
            "s": f"El total del periodo ({_moneda(cre_total)}) incluye todos los tickets aprobados; las tarjetas "
                 f"({_moneda(suma_cre)}) solo cubren creadores activos.",
        })

    if tickets_total != int(summary.ticket_count):
        notas.append({
            "t": "Tickets: el resumen y la gráfica por día cuentan cosas distintas.",
            "s": f"El resumen cuenta {int(summary.ticket_count)} tickets aprobados; la gráfica por día suma "
                 f"{tickets_total} porque incluye también los pendientes y rechazados que se subieron ese día.",
        })

    if comp is None:
        notas.append({
            "t": "Sin comparativo con el periodo anterior.",
            "s": "El rango elegido no es un mes ni un año de calendario completo, así que no hay un periodo equivalente con qué comparar.",
        })
    elif comp_parcial and end:
        notas.append({
            "t": "El periodo anterior se comparó con el mismo corte de días.",
            "s": f"Como el periodo sigue en curso (hasta el {_fecha_numerica(end)}), se compara contra los mismos días de {comp['label']}, no contra el periodo completo.",
        })

    notas.append({
        "t": "Cada tipo de gasto usa su propia fecha.",
        "s": "Tickets y gastos generales se ubican por su fecha de subida; los gastos operativos por la fecha de gasto capturada.",
    })
    return notas


def _json_seguro(datos: dict) -> str:
    """JSON apto para incrustar dentro de `<script type="application/json">`:
    ASCII puro (también neutraliza U+2028/2029) y sin `<`, `>` ni `&` literales."""
    crudo = json.dumps(datos, ensure_ascii=True, separators=(",", ":"))
    return crudo.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


@lru_cache(maxsize=None)
def _recurso_b64(nombre: str) -> str:
    """Base64 de un asset. Si el archivo falta no tumba el reporte: queda sin
    esa fuente (la tipografía cae a la siguiente de la pila)."""
    try:
        return base64.b64encode((_ASSETS / nombre).read_bytes()).decode("ascii")
    except OSError:
        return ""


@lru_cache(maxsize=1)
def _plantilla_con_recursos() -> str:
    texto = _PLANTILLA.read_text(encoding="utf-8")
    for marcador, nombre in _RECURSOS.items():
        texto = texto.replace(marcador, _recurso_b64(nombre))
    return texto


def generar_html(datos: dict) -> str:
    """HTML completo del reporte, en memoria (nunca escribe a disco). Los
    datos se sustituyen AL FINAL: así un texto libre que contenga un marcador
    (`__DATOS__`, `__F_INTER_400__`...) jamás se vuelve a interpretar."""
    reporte = construir_datos(datos)
    titulo = f"{reporte['meta']['titulo']} · GOCreate"
    return (
        _plantilla_con_recursos()
        .replace("__TITULO__", html.escape(titulo))
        .replace("__DATOS__", _json_seguro(reporte))
    )
