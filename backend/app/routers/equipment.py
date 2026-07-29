"""Inventario de equipo (contrato §2).

El listado devuelve `tenedor_actual`, `fecha_regreso_esperada`, `atrasado` y
`dias_atraso` **en la misma fila**: el contrato lo pide explicito para que la
pantalla no tenga que pedir un detalle por equipo.

`/dashboard` vive en `routers/equipos_dashboard.py` y se incluye **antes** que
este router en `main.py`. Ademas, todas las rutas por id usan `{equipment_id:int}`,
asi que "dashboard" no puede confundirse con un id ni por accidente. Dos
defensas para el mismo error porque es de los que solo se notan en produccion.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, crud_equipment, disponibilidad, models, schemas_equipment, tz
from ..database import get_db
from ..errores import ErrorEquipos, EquipoOcupado, NoEncontrado
from ..models_equipos import CondicionEquipo, EstadoFisico
from ..rbac import require_perm

router = APIRouter(prefix="/api/equipment", tags=["equipment"])


# ── Serializacion ───────────────────────────────────────────────────────────


def _a_item(equipo, auditoria, abierto, libre) -> schemas_equipment.EquipmentItem:
    tenedor = None
    if abierto is not None:
        tenedor = schemas_equipment.TenedorActual(
            nombre=abierto.responsable_nombre, user_id=abierto.responsable_user_id
        )

    return schemas_equipment.EquipmentItem(
        id=equipo.id,
        codigo=equipo.codigo,
        nombre=equipo.nombre,
        categoria=equipo.categoria,
        marca=equipo.marca,
        modelo=equipo.modelo,
        numero_serie=equipo.numero_serie,
        activo_fijo=equipo.activo_fijo,
        cuenta_gmail=equipo.cuenta_gmail,
        espacio_disponible=equipo.espacio_disponible,
        estado_operativo=equipo.estado_operativo,
        condicion=auditoria.condicion if auditoria else None,
        estado_fisico=auditoria.estado_fisico if auditoria else None,
        comentario_auditoria=auditoria.comentario if auditoria else None,
        fecha_auditoria=auditoria.fecha if auditoria else None,
        accesorios_tipicos=crud_equipment.accesorios_de(equipo),
        disponible=libre,
        tenedor_actual=tenedor,
        fecha_regreso_esperada=abierto.fecha_regreso_esperada if abierto else None,
        atrasado=abierto.atrasado if abierto else False,
        dias_atraso=abierto.dias_atraso if abierto else 0,
    )


def _construir_ficha(db: Session, equipo, abierto, libre) -> schemas_equipment.EquipmentDetail:
    auditorias = crud_equipment.auditorias_de(db, equipo.id)
    ultima = auditorias[0][0] if auditorias else None
    base = _a_item(equipo, ultima, abierto, libre)

    return schemas_equipment.EquipmentDetail(
        **base.model_dump(),
        descripcion=equipo.descripcion,
        fotos_originales_url=equipo.fotos_originales_url,
        auditorias=[
            schemas_equipment.AuditoriaResponse(
                id=fila.id,
                condicion=fila.condicion,
                estado_fisico=fila.estado_fisico,
                espacio_disponible=fila.espacio_disponible,
                comentario=fila.comentario,
                fecha=fila.fecha,
                actor_user_id=fila.actor_user_id,
                actor_nombre=nombre,
                created_at=tz.iso_cdmx(fila.created_at),
            )
            for fila, nombre in auditorias
        ],
        historial=[
            schemas_equipment.HistorialPrestamoItem(
                loan_id=prestamo.id,
                folio=prestamo.folio,
                estado=prestamo.estado,
                responsable=prestamo.responsable_nombre,
                fecha_entrega=prestamo.fecha_entrega,
                fecha_regreso_esperada=prestamo.fecha_regreso_esperada,
                devuelto_at=tz.iso_cdmx(item.devuelto_at),
                decision=item.decision,
            )
            for item, prestamo in crud_equipment.historial_de(db, equipo.id)
        ],
    )


def _obtener_o_404(db: Session, equipment_id: int):
    equipo = crud_equipment.obtener(db, equipment_id)
    if equipo is None:
        # Un equipo dado de baja responde igual que uno inexistente (contrato §0:
        # NO_ENCONTRADO incluye recursos con borrado logico).
        raise NoEncontrado("Equipo no encontrado.")
    return equipo


def _validar_vocabulario(condicion: str | None, estado_fisico: str | None) -> None:
    validas = {c.value for c in CondicionEquipo}
    if condicion is not None and condicion not in validas:
        raise ErrorEquipos(
            422, f"Condicion invalida: '{condicion}'. Validas: {', '.join(sorted(validas))}.",
            "VALOR_INVALIDO",
        )
    fisicos = {e.value for e in EstadoFisico}
    if estado_fisico is not None and estado_fisico not in fisicos:
        raise ErrorEquipos(
            422, f"Estado fisico invalido: '{estado_fisico}'. Validos: {', '.join(sorted(fisicos))}.",
            "VALOR_INVALIDO",
        )


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/", response_model=schemas_equipment.EquipmentListResponse)
def listar_equipos(
    q: Optional[str] = Query(None, description="Busca en nombre, codigo, categoria, marca, modelo, serie"),
    categoria: Optional[str] = Query(None),
    condicion: Optional[str] = Query(None, description="bueno | atencion | danado"),
    disponible: Optional[bool] = Query(None),
    limit: int = Query(crud_equipment.LIMITE_DEFAULT, ge=1, le=crud_equipment.LIMITE_MAXIMO),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "ver")),
):
    filas, total = crud_equipment.listar(
        db,
        q=q,
        categoria=categoria,
        condicion=condicion,
        disponible=disponible,
        limit=limit,
        offset=offset,
    )
    return schemas_equipment.EquipmentListResponse(
        items=[_a_item(*fila) for fila in filas], total=total
    )


@router.get("/{equipment_id:int}", response_model=schemas_equipment.EquipmentDetail)
def ficha_de_equipo(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "ver")),
):
    equipo = _obtener_o_404(db, equipment_id)
    abierto = disponibilidad.mapa_prestamos_abiertos(db, [equipo.id]).get(equipo.id)
    libre = disponibilidad.esta_disponible(equipo, ocupado=abierto is not None)
    return _construir_ficha(db, equipo, abierto, libre)


@router.post("/", response_model=schemas_equipment.EquipmentDetail, status_code=201)
def crear_equipo(
    data: schemas_equipment.EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "crear")),
):
    try:
        equipo = crud_equipment.crear(db, data.model_dump())
    except IntegrityError:
        db.rollback()
        raise ErrorEquipos(409, f"Ya existe un equipo con el codigo '{data.codigo}'.", "DUPLICADO")

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="equipment.create",
        target_type="equipment",
        target_id=equipo.id,
        details=equipo.nombre,
    )
    return ficha_de_equipo(equipo.id, db=db, current_user=current_user)


@router.put("/{equipment_id:int}", response_model=schemas_equipment.EquipmentDetail)
def editar_equipo(
    equipment_id: int,
    data: schemas_equipment.EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "editar")),
):
    equipo = _obtener_o_404(db, equipment_id)
    cambios = data.model_dump(exclude_unset=True)
    if cambios:
        try:
            crud_equipment.actualizar(db, equipo, cambios)
        except IntegrityError:
            db.rollback()
            raise ErrorEquipos(409, "Ya existe un equipo con ese codigo.", "DUPLICADO")

        crud.log_audit(
            db,
            actor_user_id=current_user.id,
            action="equipment.update",
            target_type="equipment",
            target_id=equipo.id,
        )
    return ficha_de_equipo(equipment_id, db=db, current_user=current_user)


@router.post(
    "/{equipment_id:int}/auditoria",
    response_model=schemas_equipment.EquipmentDetail,
    status_code=201,
)
def registrar_auditoria(
    equipment_id: int,
    data: schemas_equipment.AuditoriaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "auditar_condicion")),
):
    equipo = _obtener_o_404(db, equipment_id)
    _validar_vocabulario(data.condicion, data.estado_fisico)

    auditoria = crud_equipment.registrar_auditoria(
        db, equipo, data.model_dump(), actor_user_id=current_user.id
    )
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="equipment.audit",
        target_type="equipment",
        target_id=equipo.id,
        details=f"condicion={auditoria.condicion}",
    )
    return ficha_de_equipo(equipment_id, db=db, current_user=current_user)


@router.post("/{equipment_id:int}/baja", response_model=schemas_equipment.EquipmentDetail)
def dar_de_baja(
    equipment_id: int,
    data: schemas_equipment.BajaRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "dar_de_baja")),
):
    equipo = _obtener_o_404(db, equipment_id)

    # 409 si esta fuera: dar de baja un equipo que alguien tiene en la mano lo
    # sacaria del inventario sin que nadie lo devuelva, y el renglon abierto
    # quedaria apuntando a un equipo que ya no aparece en ningun listado.
    if disponibilidad.item_abierto_de(db, equipo.id) is not None:
        raise EquipoOcupado(
            "El equipo esta en un prestamo abierto. Registra la devolucion antes de darlo de baja."
        )

    crud_equipment.dar_de_baja(db, equipo, current_user.id, data.motivo)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="equipment.baja",
        target_type="equipment",
        target_id=equipo.id,
        details=data.motivo,
    )

    # Se arma la ficha con el objeto ya en memoria: quien acaba de dar la baja
    # tiene derecho a ver el resultado de su accion. A partir del siguiente
    # request el equipo responde 404, como cualquier recurso con borrado logico.
    return _construir_ficha(db, equipo, None, False)
