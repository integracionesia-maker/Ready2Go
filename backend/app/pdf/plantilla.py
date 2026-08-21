"""Estructura de la carta responsiva: convierte datos ya resueltos en flowables.

El texto legal parte de la maqueta (plan §6). El área aprobó ajustes puntuales
(ver los comentarios en SITUACIONES_EXTRAORDINARIAS y PARRAFO_RECEPCION); fuera
de esos, no se reescribe: cambiar un parrafo de responsabilidad civil para que
"suene mejor" cambia lo que la persona firma.

Este modulo no toca la base de datos: recibe un diccionario y devuelve flowables.
Asi se puede probar el documento sin sembrar nada, y `responsiva.py` es el unico
que sabe de SQLAlchemy.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from . import estilos as est

__all__ = [
    "MESES",
    "VACIO",
    "SIN_ACCESORIOS",
    "SIN_NOMBRE",
    "TITULO",
    "PARRAFO_RECEPCION",
    "SUBTITULO_LEGAL",
    "SITUACIONES_EXTRAORDINARIAS",
    "PIE_FIRMA_RESPONSABLE",
    "PIE_FIRMA_ENTREGA",
    "ETIQUETAS_EQUIPO",
    "ETIQUETAS_CARGADOR",
    "fecha_larga",
    "construir",
]

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

VACIO = "—"
SIN_ACCESORIOS = "Ninguno registrado"
SIN_NOMBRE = "(equipo)"

TITULO = "CARTA RESPONSIVA DE EQUIPO"

# El empleador es fijo por decisión del área (2026-08-20): antes salía de
# {empresa}. Ese valor —la Marca elegida en el wizard— ahora acompaña al área.
PARRAFO_RECEPCION = (
    "Por medio de la presente, hago constar que recibí el siguiente equipo para uso "
    "del desempeño de mis funciones y actividades asignadas en el área de "
    "<b>{area}</b> de <b>{empresa}</b>, empleado de la empresa "
    # El punto de "S.C." cierra la oración: no se agrega otro (evita "S.C..").
    "<b>SERVICIOS CORPORATIVOS QUANTUM DE OCCIDENTE, S.C.</b>"
)

SUBTITULO_LEGAL = "Situaciones extraordinarias"

# Texto de la maqueta con dos ajustes pedidos por el área (2026-08-20): en la
# "Nota" se quitó "ya sea por cambio o terminación de contrato laboral con la
# empresa", y se eliminó el punto de "opción de compra al término del contrato".
# Fuera de esos cambios acordados, no se resume ni se reordena.
SITUACIONES_EXTRAORDINARIAS = [
    (
        "Daño:",
        "por mal manejo o imprudencia serán mi responsabilidad y asumo las "
        "consecuencias, costos que de esto se deriven.",
    ),
    (
        "Robo:",
        "Se deberá de reportar al área responsable, de forma inmediata y dejar "
        "constancia mediante un acta de hechos, asumiendo las consecuencias que de "
        "ahí se deriven.",
    ),
    (
        "Pérdida:",
        "Se deberá de reportar al área responsable, de forma inmediata y dejar "
        "constancia mediante un acta de hechos y pagar el costo del equipo para su "
        "reposición.",
    ),
    (
        "Nota:",
        "Al momento de entregar el equipo, éste deberá entregarse en óptimas "
        "condiciones físicas y bajo ninguna circunstancia el trabajador podrá "
        "eliminar la copia de seguridad de la información que se genere en el mismo; "
        "de lo contrario se aplicará el uso del pagaré correspondiente para cubrir "
        "los daños generados.",
    ),
]

PIE_FIRMA_RESPONSABLE = "Nombre y firma del responsable"
# Sin articulo y con "Entrega" en mayuscula: asi esta en la maqueta.
PIE_FIRMA_ENTREGA = "Nombre y firma Entrega"

ETIQUETAS_EQUIPO = [
    ("numero_serie", "No. Serie", True),
    ("activo_fijo", "Activo fijo", True),
    ("marca", "Marca", False),
    ("modelo", "Modelo", False),
    ("cuenta_gmail", "Cuenta de Gmail", False),
    ("condiciones", "Condiciones del equipo", False),
    ("accesorios", "Accesorios", False),
]

# El contrato no publica etiquetas legibles para `cargador_con`, y en la carta
# imprimir el token crudo ("responsable") se lee como una palabra suelta. Este
# mapa es propuesta del servidor; los valores desconocidos se imprimen tal cual
# en vez de desaparecer.
ETIQUETAS_CARGADOR = {
    "responsable": "Se lo lleva el responsable",
    "resguardo": "Se queda en resguardo",
    "sin_cargador": "El equipo sale sin cargador",
}


def _t(valor) -> str:
    """Texto seguro para un `Paragraph`.

    `Paragraph` interpreta un subconjunto de XML: un nombre de equipo con `&` o
    `<` rompe el documento entero. Escapar no es cosmetico.
    """
    if valor is None:
        return VACIO
    texto = str(valor).strip()
    return escape(texto) if texto else VACIO


def fecha_larga(fecha) -> str:
    """`25 de julio de 2026`. Dia sin cero a la izquierda, mes en minusculas.

    Sin fecha devuelve la raya larga: la maqueta caia a "hoy", y en un documento
    que alguien firma es peor inventar una fecha que dejarla en blanco.
    """
    if fecha is None:
        return VACIO
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def etiqueta_cargador(valor: str | None) -> str | None:
    if not valor:
        return None
    return ETIQUETAS_CARGADOR.get(valor, valor)


def _tabla_equipo(equipo: dict, e: dict) -> Table:
    filas = []
    for clave, etiqueta, mono in ETIQUETAS_EQUIPO:
        estilo_valor = e["valor_mono"] if mono else e["valor"]
        filas.append(
            [
                Paragraph(etiqueta, e["etiqueta"]),
                Paragraph(_t(equipo.get(clave)), estilo_valor),
            ]
        )

    cargador = etiqueta_cargador(equipo.get("cargador_con"))
    if cargador:
        # El renglon se OMITE si no hay valor; no se imprime la raya larga.
        filas.append(
            [Paragraph("Cargador con", e["etiqueta"]), Paragraph(_t(cargador), e["valor"])]
        )

    tabla = Table(filas, colWidths=[est.ANCHO_ETIQUETA, None], hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, est.LINEA),
            ]
        )
    )
    return tabla


def _bloque_firma(ruta_firma: str | None, nombre: str, pie: str, e: dict, ancho: float) -> list:
    """Imagen de la firma, linea, nombre y leyenda.

    Si falta el archivo se deja el espacio en blanco con su linea: una carta sin
    firma tiene que verse sin firma, no disimularla.
    """
    partes: list = []
    alto_maximo = 14 * mm

    if ruta_firma:
        try:
            imagen = Image(ruta_firma)
            proporcion = imagen.imageWidth / imagen.imageHeight if imagen.imageHeight else 1
            imagen.drawHeight = alto_maximo
            imagen.drawWidth = min(alto_maximo * proporcion, ancho - 6 * mm)
            imagen.hAlign = "CENTER"
            partes.append(imagen)
        except Exception:  # noqa: BLE001 — archivo movido o corrupto: no tumba la carta
            partes.append(Spacer(1, alto_maximo))
    else:
        partes.append(Spacer(1, alto_maximo))

    partes.append(Spacer(1, 2 * mm))
    partes.append(HRFlowable(width="90%", thickness=0.6, color=est.TEXTO, spaceAfter=3))
    partes.append(Paragraph(_t(nombre), e["firma_nombre"]))
    partes.append(Paragraph(escape(pie), e["firma_pie"]))
    return partes


def construir(datos: dict, ancho_util: float) -> list:
    """Flowables del documento completo, en orden."""
    e = est.estilos()
    flujo: list = []

    emisora = datos.get("emisora") or {}

    # Encabezado: folio y lugar/fecha a la derecha.
    flujo.append(Paragraph(f"FOLIO: {_t(datos.get('folio'))}", e["folio"]))
    flujo.append(
        Paragraph(
            f"{_t(emisora.get('ciudad'))}, {escape(datos.get('fecha_texto') or VACIO)}",
            e["fecha"],
        )
    )
    flujo.append(Spacer(1, 6 * mm))

    # Bloque emisor. Los cuatro valores salen de la tabla `empresa`.
    flujo.append(Paragraph(f"<b>{_t(emisora.get('razon_social'))}</b>", e["emisor"]))
    if emisora.get("direccion"):
        flujo.append(Paragraph(_t(emisora.get("direccion")), e["emisor"]))
    if emisora.get("ciudad"):
        flujo.append(Paragraph(f"<b>{_t(emisora.get('ciudad')).upper()}</b>", e["emisor"]))
    if emisora.get("rfc"):
        flujo.append(Paragraph(f"RFC: {_t(emisora.get('rfc'))}", e["emisor"]))

    flujo.append(Paragraph(TITULO, e["titulo"]))

    flujo.append(
        Paragraph(
            PARRAFO_RECEPCION.format(
                area=_t(datos.get("area")) if datos.get("area") else "____",
                empresa=_t(datos.get("empresa")) if datos.get("empresa") else "____",
            ),
            e["cuerpo"],
        )
    )
    flujo.append(
        Paragraph(
            f"<b>Responsable del equipo:</b> {_t(datos.get('responsable'))} &nbsp;·&nbsp; "
            f"<b>Motivo:</b> {_t(datos.get('motivo'))}",
            e["cuerpo"],
        )
    )
    flujo.append(Paragraph("<b>Características del equipo:</b>", e["cuerpo"]))

    for equipo in datos.get("equipos") or []:
        nombre = equipo.get("nombre") or SIN_NOMBRE
        # KeepTogether: partir un equipo entre dos paginas deja media ficha
        # huerfana y hace que dos versiones del mismo folio se lean distinto.
        flujo.append(
            KeepTogether(
                [
                    Paragraph(_t(nombre), e["equipo_nombre"]),
                    _tabla_equipo(equipo, e),
                ]
            )
        )

    flujo.append(Spacer(1, 4 * mm))
    flujo.append(Paragraph(f"<b>Notas:</b> {_t(datos.get('notas'))}", e["cuerpo"]))

    flujo.append(Paragraph(SUBTITULO_LEGAL, e["subtitulo"]))
    for etiqueta, cuerpo in SITUACIONES_EXTRAORDINARIAS:
        texto = f"<b>{escape(etiqueta)}</b> {escape(cuerpo)}" if etiqueta else escape(cuerpo)
        flujo.append(Paragraph(texto, e["legal"]))

    flujo.append(Spacer(1, 7 * mm))

    ancho_columna = ancho_util / 2
    izquierda = _bloque_firma(
        datos.get("firma_responsable"),
        datos.get("responsable"),
        PIE_FIRMA_RESPONSABLE,
        e,
        ancho_columna,
    )
    derecha = _bloque_firma(
        datos.get("firma_entrega"),
        datos.get("entregado_por"),
        PIE_FIRMA_ENTREGA,
        e,
        ancho_columna,
    )
    firmas = Table(
        [[izquierda, derecha]], colWidths=[ancho_columna, ancho_columna], hAlign="CENTER"
    )
    firmas.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    # El bloque de firmas nunca se parte ni queda solo: si no cabe, baja entero.
    flujo.append(KeepTogether(firmas))

    # Pie tecnico. No afirma validez legal —§6 del plan lo prohibe explicito—;
    # solo identifica la version, que hace falta para distinguir dos impresiones
    # del mismo folio.
    flujo.append(
        Paragraph(
            f"Documento generado por GOCreate · Folio {_t(datos.get('folio'))} · "
            f"Versión {datos.get('version', 1)} · {escape(datos.get('generado_en') or '')}",
            e["aviso"],
        )
    )

    return flujo
