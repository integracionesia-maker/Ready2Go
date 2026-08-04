"""Genera la carta responsiva en PDF y devuelve su sha256.

Unico modulo de `app/pdf/` que conoce la base de datos: reune los datos, se los
pasa a `plantilla.construir()` y escribe el archivo.

Tres reglas duras:

1. **La razon social emisora sale de la tabla `empresa`, jamas hardcode.** La
   maqueta la tenia en una constante del JavaScript, asi que cambiarla exigia
   tocar codigo (§10.21). Si no hay emisora configurada, se falla explicito en
   vez de imprimir un encabezado a medias.
2. **Nunca se sobrescribe un archivo.** Regenerar crea `version + 1`. Un
   documento firmado es evidencia; escribir encima destruye el rastro. Si el
   destino ya existe, es un error, no un caso a resolver pisando.
3. **La condicion del equipo se congela contra la auditoria vigente a la fecha
   de entrega**, no contra la ultima del catalogo. Si no, la version 2 de una
   carta ya firmada diria una condicion distinta de la version 1 sobre los
   mismos hechos.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate
from sqlalchemy.orm import Session

from .. import crud_empresas, tz
from ..models import User
from ..models_equipos import Equipment, EquipmentAudit, KindMedia, Loan, MediaAsset
from . import estilos as est
from . import plantilla

__all__ = ["EmisoraNoConfigurada", "ArchivoYaExiste", "datos_de", "generar_a_disco"]


class EmisoraNoConfigurada(RuntimeError):
    """No hay razon social emisora en la tabla `empresa`.

    Se falla en vez de caer a la constante de la maqueta: un encabezado
    inventado en un documento que alguien firma es peor que no generarlo.
    """


class ArchivoYaExiste(RuntimeError):
    """El destino ya existe. Nunca se pisa: seria destruir evidencia."""


def _condicion_vigente(db: Session, equipment_id: int, fecha_corte) -> EquipmentAudit | None:
    """Auditoria vigente a `fecha_corte`.

    Se toma la mas reciente cuya fecha sea anterior o igual al corte. Las que no
    tienen fecha (equipos dados de alta sin auditar todavia) valen solo si no hay
    ninguna fechada: son un punto de partida, no una revision posterior.

    Limitacion conocida y documentada: no hay columna donde congelar el texto que
    salio impreso en cada version. Mientras nadie retro-feche una auditoria, dos
    versiones del mismo folio dicen lo mismo.
    """
    auditorias = (
        db.query(EquipmentAudit)
        .filter(EquipmentAudit.equipment_id == equipment_id)
        .order_by(EquipmentAudit.id.desc())
        .all()
    )
    if not auditorias:
        return None

    if fecha_corte is not None:
        con_fecha = [a for a in auditorias if a.fecha is not None and a.fecha <= fecha_corte]
        if con_fecha:
            return con_fecha[0]

    return auditorias[0]


def _condiciones_texto(auditoria: EquipmentAudit | None) -> str | None:
    """`estado_fisico — comentario`, omitiendo los vacios."""
    if auditoria is None:
        return None
    partes = [p for p in (auditoria.estado_fisico, auditoria.comentario) if p and p.strip()]
    return " — ".join(partes) if partes else None


def _accesorios_texto(item) -> str:
    partes: list[str] = []
    if item.accesorios_seleccionados:
        try:
            valor = json.loads(item.accesorios_seleccionados)
            if isinstance(valor, list):
                partes.extend(str(x) for x in valor if str(x).strip())
        except (TypeError, ValueError):
            pass
    if item.accesorios_otros and item.accesorios_otros.strip():
        partes.append(item.accesorios_otros.strip())
    return ", ".join(partes) if partes else plantilla.SIN_ACCESORIOS


def _rutas_de_firma(db: Session, loan_id: int) -> dict[str, str | None]:
    """Rutas en disco de las dos firmas del prestamo.

    Se leen de `media_asset` por `loan_id` con `loan_item_id` nulo: las firmas
    son de las personas, no de un equipo.
    """
    salida: dict[str, str | None] = {
        KindMedia.FIRMA_RESPONSABLE.value: None,
        KindMedia.FIRMA_ENTREGA.value: None,
    }
    filas = (
        db.query(MediaAsset)
        .filter(MediaAsset.loan_id == loan_id)
        .filter(MediaAsset.kind.in_(list(salida)))
        .order_by(MediaAsset.id)
        .all()
    )
    for fila in filas:
        if Path(fila.file_path).exists():
            salida[fila.kind] = fila.file_path
    return salida


def datos_de(db: Session, prestamo: Loan, version: int = 1) -> dict:
    """Todo lo que la plantilla necesita, ya resuelto. Sin objetos ORM."""
    emisora = crud_empresas.emisora_por_defecto(db)
    if emisora is None:
        raise EmisoraNoConfigurada(
            "No hay razon social emisora activa con RFC en la tabla `empresa`. "
            "Siembrala antes de generar cartas responsivas (seed_equipos.py)."
        )

    firmas = _rutas_de_firma(db, prestamo.id)

    equipos: list[dict] = []
    for item in prestamo.items:
        equipo = db.get(Equipment, item.equipment_id)
        auditoria = _condicion_vigente(db, item.equipment_id, prestamo.fecha_entrega)
        equipos.append(
            {
                "nombre": equipo.nombre if equipo else plantilla.SIN_NOMBRE,
                "numero_serie": equipo.numero_serie if equipo else None,
                "activo_fijo": equipo.activo_fijo if equipo else None,
                "marca": equipo.marca if equipo else None,
                "modelo": equipo.modelo if equipo else None,
                "cuenta_gmail": equipo.cuenta_gmail if equipo else None,
                "condiciones": _condiciones_texto(auditoria),
                "accesorios": _accesorios_texto(item),
                "cargador_con": item.cargador_con,
            }
        )

    entregado_por = (
        db.get(User, prestamo.entregado_por_user_id)
        if prestamo.entregado_por_user_id
        else None
    )

    return {
        "folio": prestamo.folio,
        "version": version,
        "generado_en": tz.iso_cdmx(tz.ahora_utc_naive()),
        "emisora": {
            "razon_social": emisora.razon_social,
            "direccion": emisora.direccion,
            "ciudad": emisora.ciudad,
            "rfc": emisora.rfc,
        },
        "fecha_texto": plantilla.fecha_larga(prestamo.fecha_entrega),
        "area": prestamo.area,
        "empresa": prestamo.empresa,
        "responsable": prestamo.responsable_nombre,
        "motivo": prestamo.motivo,
        "notas": prestamo.notas_responsiva,
        "equipos": equipos,
        "entregado_por": entregado_por.full_name if entregado_por else None,
        "firma_responsable": firmas[KindMedia.FIRMA_RESPONSABLE.value],
        "firma_entrega": firmas[KindMedia.FIRMA_ENTREGA.value],
    }


def generar_a_disco(db: Session, prestamo: Loan, destino: Path, version: int = 1) -> str:
    """Escribe el PDF y devuelve su sha256.

    La firma la llama `crud_loans.generar_responsiva`, que ya calculo la version
    y la ruta. Aqui no se decide donde va el archivo, solo se escribe.
    """
    destino = Path(destino)
    if destino.exists():
        raise ArchivoYaExiste(
            f"Ya existe {destino}. Una responsiva nunca se sobrescribe: "
            "genera una version nueva."
        )

    datos = datos_de(db, prestamo, version)
    destino.parent.mkdir(parents=True, exist_ok=True)

    documento = SimpleDocTemplate(
        str(destino),
        pagesize=letter,
        leftMargin=est.MARGENES["left"],
        rightMargin=est.MARGENES["right"],
        topMargin=est.MARGENES["top"],
        bottomMargin=est.MARGENES["bottom"],
        title=f"Carta responsiva {prestamo.folio or ''}".strip(),
        author="GOCreate",
        subject="Carta responsiva de equipo",
    )
    ancho_util = documento.width
    documento.build(plantilla.construir(datos, ancho_util))

    return hashlib.sha256(destino.read_bytes()).hexdigest()
