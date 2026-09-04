"""Prestamos de equipo (contrato §3).

Orden de las rutas: `/export` y `/by-folio/{folio}` se declaran **antes** que
`/{loan_id:int}`, y la ruta por id lleva el conversor `:int`. Dos defensas para
el mismo error: sin ellas el enrutador se traga "export" como si fuera un id.

Orden de verificacion en cada endpoint de transicion, siempre el mismo:
permiso (403) -> existencia (404) -> visibilidad (403) -> estado (409) ->
payload (422) -> conflicto de equipo (409). Invertirlo filtra la existencia de
prestamos ajenos.
"""

import csv
import io
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import (
    crud,
    crud_loans,
    crud_rbac,
    loan_state,
    media_manager,
    models,
    notificaciones,
    plantillas_correo,
    rbac,
    schemas_loans,
    tz,
)
from ..database import get_db
from ..errores import (
    ErrorEquipos,
    EquipoOcupado,
    NoEncontrado,
    SinPermiso,
    TransicionInvalida,
)
from ..models_equipos import EstadoOperativo, Equipment, KindMedia, LoanItem, MediaAsset
from ..rbac import permisos_del_request, require_cualquiera, require_perm

router = APIRouter(prefix="/api/loans", tags=["loans"])

VER_PROPIOS = ("equipos_prestamos", "ver_propios")
VER_GLOBAL = ("equipos_prestamos", "ver_global")


# ── Autorizacion ────────────────────────────────────────────────────────────


def _ver_global(request: Request, db: Session, user: models.User) -> bool:
    return rbac.tiene_permiso(permisos_del_request(request, db, user), *VER_GLOBAL)


def _prestamo_visible(request: Request, db: Session, user: models.User, loan_id: int):
    """404 si no existe o esta borrado; 403 si existe y no es suyo.

    El 403 confirma que ese id existe. Se acepta a proposito: es la lectura
    literal de la tabla del §3 ("participante o ver_global" es un permiso, y la
    falta de permiso es 403) y el plan §5 lo dice igual. El 404 se reserva para
    lo inexistente y lo borrado, que se responden igual entre si.
    """
    prestamo = crud_loans.obtener(db, loan_id)
    if prestamo is None:
        raise NoEncontrado("Prestamo no encontrado.")
    if not crud_loans.puede_ver(prestamo, user.id, _ver_global(request, db, user)):
        raise SinPermiso()
    return prestamo


def _exigir_estado(prestamo, accion: str, decisiones: list[str] | None = None) -> str:
    try:
        return loan_state.estado_destino(prestamo.estado, accion, decisiones)
    except loan_state.TransicionNoPermitida as exc:
        raise TransicionInvalida(exc.detalle) from exc


def _ficha(db: Session, prestamo) -> dict:
    return crud_loans.serializar_detalle(db, prestamo)


# ── Alta y listado ──────────────────────────────────────────────────────────


@router.post("/", response_model=schemas_loans.LoanDetail, status_code=201)
def crear_prestamo(
    data: schemas_loans.LoanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "solicitar")),
):
    prestamo = crud_loans.crear(db, data.model_dump(exclude_unset=True), current_user)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.create",
        target_type="loan",
        target_id=prestamo.id,
    )
    return _ficha(db, prestamo)


@router.get("/", response_model=schemas_loans.LoanListResponse)
def listar_prestamos(
    request: Request,
    estado: Optional[str] = Query(None),
    mios: bool = Query(False),
    q: Optional[str] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    limit: int = Query(crud_loans.LIMITE_DEFAULT, ge=1, le=crud_loans.LIMITE_MAXIMO),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cualquiera(VER_PROPIOS, VER_GLOBAL)),
):
    # Scoping server-side: sin ver_global solo se ven los propios, mande o no
    # `mios`. Con ver_global, `mios=1` es lo que usa el wizard para recuperar el
    # borrador de uno mismo (Melisa tiene los dos permisos).
    global_ = _ver_global(request, db, current_user)
    solo_de = current_user.id if (mios or not global_) else None

    filas, total = crud_loans.listar(
        db,
        solo_de_user_id=solo_de,
        estado=estado,
        q=q,
        desde=desde,
        hasta=hasta,
        limit=limit,
        offset=offset,
    )
    equipos = crud_loans._equipos_por_prestamo(db, [p.id for p in filas])
    firmas_faltantes = crud_loans._firmas_faltantes_por_prestamo(db, [p.id for p in filas])
    return schemas_loans.LoanListResponse(
        items=[
            crud_loans.serializar_fila(p, equipos.get(p.id, []), firmas_faltantes=firmas_faltantes.get(p.id, frozenset()))
            for p in filas
        ],
        total=total,
    )


@router.get("/export")
def exportar_csv(
    request: Request,
    estado: Optional[str] = Query(None),
    mios: bool = Query(False),
    q: Optional[str] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "exportar")),
):
    """CSV con los mismos filtros y el mismo scoping que el listado.

    Hoy `exportar` solo lo tienen `admin` y `superadmin`, que ya traen
    `ver_global`, pero el scoping se escribe igual: el dia que un paquete aditivo
    conceda `exportar` sin `ver_global`, la exportacion no puede volverse una
    fuga de todos los prestamos.

    Columnas, separador y BOM: el contrato no los define. Ver
    `crud_loans.COLUMNAS_CSV` y el reporte en docs/avances/servidor.md.
    """
    global_ = _ver_global(request, db, current_user)
    solo_de = current_user.id if (mios or not global_) else None

    filas, _ = crud_loans.listar(
        db,
        solo_de_user_id=solo_de,
        estado=estado,
        q=q,
        desde=desde,
        hasta=hasta,
        limit=crud_loans.LIMITE_MAXIMO,
        offset=0,
    )

    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")
    escritor.writerow(crud_loans.COLUMNAS_CSV)
    escritor.writerows(crud_loans.filas_csv(db, filas))

    # BOM para que Excel no destroce los acentos al abrir el archivo.
    contenido = "﻿" + buffer.getvalue()
    nombre = f"control_equipos_go_{tz.hoy().isoformat()}.csv"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/by-folio/{folio}", response_model=schemas_loans.LoanDetail)
def ficha_por_folio(
    folio: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cualquiera(VER_PROPIOS, VER_GLOBAL)),
):
    prestamo = crud_loans.obtener_por_folio(db, folio)
    if prestamo is None:
        raise NoEncontrado("Prestamo no encontrado.")
    if not crud_loans.puede_ver(prestamo, current_user.id, _ver_global(request, db, current_user)):
        raise SinPermiso()
    return _ficha(db, prestamo)


@router.get("/{loan_id:int}", response_model=schemas_loans.LoanDetail)
def ficha_de_prestamo(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cualquiera(VER_PROPIOS, VER_GLOBAL)),
):
    return _ficha(db, _prestamo_visible(request, db, current_user, loan_id))


# ── Renglones ───────────────────────────────────────────────────────────────


@router.post("/{loan_id:int}/items", response_model=schemas_loans.LoanDetail, status_code=201)
def agregar_equipo(
    loan_id: int,
    data: schemas_loans.LoanItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "solicitar")),
):
    prestamo = _prestamo_visible(request, db, current_user, loan_id)
    if not loan_state.acepta_items(prestamo.estado):
        raise TransicionInvalida(
            "Solo se pueden agregar equipos a un borrador. Este prestamo ya tiene carta responsiva."
        )

    equipo = db.get(Equipment, data.equipment_id)
    if equipo is None or equipo.is_deleted:
        raise NoEncontrado("Equipo no encontrado.")

    # El contrato no da codigo para "equipo en revision o baja"; EQUIPO_OCUPADO
    # diria algo falso (no esta en otro prestamo). Se usa un codigo propio y se
    # reporta. La validacion es server-side a proposito: la maqueta solo filtraba
    # al pintar y dejaba pedir un equipo en revision (§10.14).
    if equipo.estado_operativo != EstadoOperativo.ACTIVO.value:
        raise ErrorEquipos(
            409,
            f"El equipo esta en '{equipo.estado_operativo}' y no se puede prestar.",
            "EQUIPO_NO_DISPONIBLE",
        )

    # Pedir dos veces el mismo equipo en la misma solicitud es un error de
    # captura, no una carrera, y merece un mensaje que lo diga. Se comprueba
    # antes porque en la base salta primero el indice unico parcial (el equipo ya
    # tiene renglon abierto: el de este mismo prestamo) y ese error diria
    # "esta en otro prestamo", que es falso.
    if any(item.equipment_id == equipo.id for item in prestamo.items):
        raise ErrorEquipos(409, "Ese equipo ya esta en este prestamo.", "DUPLICADO")

    try:
        crud_loans.agregar_item(db, prestamo, data.model_dump(), current_user, equipo)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # El arbitro de la carrera es el indice unico parcial, no un SELECT
        # previo: entre validar y guardar cabe otra solicitud pidiendo el mismo
        # equipo. Aqui llega la que pierde.
        raise EquipoOcupado() from exc

    db.refresh(prestamo)
    return _ficha(db, prestamo)


@router.delete("/{loan_id:int}/items/{item_id:int}", response_model=schemas_loans.LoanDetail)
def quitar_equipo(
    loan_id: int,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "solicitar")),
):
    prestamo = _prestamo_visible(request, db, current_user, loan_id)
    if not loan_state.acepta_items(prestamo.estado):
        raise TransicionInvalida("Solo se pueden quitar equipos de un borrador.")

    item = db.get(LoanItem, item_id)
    if item is None or item.loan_id != prestamo.id:
        raise NoEncontrado("Renglon no encontrado en este prestamo.")

    crud_loans.quitar_item(db, prestamo, item, current_user)
    db.refresh(prestamo)
    return _ficha(db, prestamo)


# ── Media ───────────────────────────────────────────────────────────────────


@router.get("/titular-firma-equipo", response_model=schemas_loans.TitularFirmaEquipoResponse)
def titular_de_la_firma_del_aprobador(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_cualquiera(("equipos_prestamos", "solicitar"), ("equipos_aprobacion", "autorizar_entrega"))
    ),
):
    """Quien tiene hoy el paquete singleton TITULAR_FIRMA_EQUIPO — el cliente
    lo usa para decidir a quien mostrarle el boton de "Firmar" del aprobador
    (esa firma es identidad, no permiso: ver docstring de `subir_media`)."""
    titular = crud_rbac.titular_firma_equipo(db)
    return schemas_loans.TitularFirmaEquipoResponse(
        user_id=titular.id if titular else None,
        nombre=titular.full_name if titular else None,
        soy_titular=bool(titular and titular.id == current_user.id),
    )


@router.post("/{loan_id:int}/media", response_model=schemas_loans.MediaResponse, status_code=201)
async def subir_media(
    loan_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    kind: str = Form(...),
    loan_item_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    # OR a nivel de endpoint (cualquiera de los dos permisos entra); el
    # permiso EXACTO que aplica depende de `kind` y se resuelve abajo, no aqui
    # — un aprobador puro (paquete APROBADOR_EQUIPO, sin `solicitar`) tiene que
    # poder llegar a este endpoint para subir `firma_entrega`, aunque no pueda
    # subir fotos ni la firma del beneficiario.
    current_user: models.User = Depends(
        require_cualquiera(("equipos_prestamos", "solicitar"), ("equipos_aprobacion", "autorizar_entrega"))
    ),
):
    """Multipart, un archivo por request. Validacion por magic bytes.

    `firma_entrega` es la firma de quien APRUEBA el prestamo — el titular del
    paquete SINGLETON `TITULAR_FIRMA_EQUIPO` (Melisa hoy; ver
    `docs/equipos/firma-pendiente-al-confirmar.md` §Titular), nadie mas. Esto
    es una identidad, no un permiso: se compara `current_user.id` contra
    `crud_rbac.titular_firma_equipo()` directo, **sin pasar por
    `rbac.tiene_permiso()`** — ese motor tiene el bypass de superadmin (`*`
    abre todo), y una firma que "cualquier admin puede poner" deja de ser una
    firma. Ni siquiera `APROBADOR_EQUIPO` sustituye ser el titular: ese
    paquete sigue abriendo autorizar entregas/confirmar devoluciones/cerrar
    incidencias (el resto del flujo de aprobacion), pero no firmar. El resto
    de los kinds (fotos y `firma_responsable`, la del beneficiario) siguen
    pidiendo `equipos_prestamos:solicitar`, igual que siempre.
    """
    prestamo = _prestamo_visible(request, db, current_user, loan_id)

    validos = {k.value for k in KindMedia}
    if kind not in validos:
        raise ErrorEquipos(
            422, f"kind invalido: '{kind}'. Validos: {', '.join(sorted(validos))}.", "VALOR_INVALIDO"
        )

    es_firma_aprobador = kind == KindMedia.FIRMA_ENTREGA.value
    if es_firma_aprobador:
        titular = crud_rbac.titular_firma_equipo(db)
        if titular is None:
            raise SinPermiso(
                "Nadie tiene asignado el paquete TITULAR_FIRMA_EQUIPO todavia. "
                "Asignalo en Administracion del Sistema > Asignaciones antes de firmar."
            )
        if titular.id != current_user.id:
            raise SinPermiso("Solo el titular de la firma del aprobador puede subir esta firma.")
    else:
        permisos = permisos_del_request(request, db, current_user)
        if not rbac.tiene_permiso(permisos, "equipos_prestamos", "solicitar"):
            raise SinPermiso()

    if not loan_state.acepta_media(prestamo.estado, kind):
        raise TransicionInvalida(
            f"No se puede subir '{kind}' con el prestamo en estado '{prestamo.estado}'."
        )

    es_firma = kind in media_manager.KINDS_FIRMA
    if es_firma and loan_item_id is not None:
        raise ErrorEquipos(422, "Una firma no se adjunta a un equipo.", "VALOR_INVALIDO")
    if not es_firma and loan_item_id is None:
        raise ErrorEquipos(422, "Falta loan_item_id para una foto de equipo.", "VALOR_INVALIDO")

    # Completar una firma (ya con folio: `prestado`, `pendiente_confirmacion` o
    # `incompleto` — `acepta_media` ya descarta `borrador`) esta permitido;
    # RE-subir una firma que ya existe no — es evidencia.
    if es_firma:
        ya_existe = (
            db.query(MediaAsset.id)
            .filter(MediaAsset.loan_id == prestamo.id, MediaAsset.kind == kind)
            .first()
            is not None
        )
        if ya_existe:
            raise TransicionInvalida("Esa firma ya fue capturada; no se puede reemplazar.")

    if loan_item_id is not None:
        item = db.get(LoanItem, loan_item_id)
        if item is None or item.loan_id != prestamo.id:
            raise NoEncontrado("Renglon no encontrado en este prestamo.")

    contenido = await file.read()
    # media_manager.reemplazar decodifica con PIL (verificacion de dimensiones)
    # y escribe a disco -- todo sincrono y bloqueante. Corrido directo aqui
    # congelaria el event loop para el resto de requests concurrentes; se
    # manda al threadpool de Starlette igual que la escritura de auditoria.
    fila = await run_in_threadpool(
        media_manager.reemplazar,
        db,
        contenido=contenido,
        kind=kind,
        loan_id=prestamo.id,
        loan_item_id=loan_item_id,
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(fila)

    # Si esto acaba de completar la segunda firma, la responsiva pasa a v2
    # (ya con las dos) y se avisa — no antes: con la primera firma sola no hay
    # nada nuevo que contar por correo.
    if es_firma and crud_loans.firmas_completas(db, prestamo.id):
        crud_loans.completar_firma_faltante(db, prestamo, current_user)
        crud.log_audit(
            db,
            actor_user_id=current_user.id,
            action="loan.signature_completed",
            target_type="loan",
            target_id=prestamo.id,
            details=prestamo.folio,
        )
        notificaciones.encolar(
            db,
            plantillas_correo.TIPO_FIRMA_COMPLETADA,
            prestamo,
            background_tasks,
            con_responsiva=True,
        )
        if prestamo.responsable_email:
            notificaciones.encolar(
                db,
                plantillas_correo.TIPO_FIRMA_COMPLETADA,
                prestamo,
                background_tasks,
                destinatarios=[prestamo.responsable_email],
                con_responsiva=True,
            )

    return schemas_loans.MediaResponse(id=fila.id, kind=fila.kind, sha256=fila.sha256)


# ── Transiciones ────────────────────────────────────────────────────────────


@router.post("/{loan_id:int}/confirmar", response_model=schemas_loans.LoanDetail)
def confirmar_prestamo(
    loan_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "solicitar")),
):
    prestamo = _prestamo_visible(request, db, current_user, loan_id)
    _exigir_estado(prestamo, loan_state.Accion.CONFIRMAR)

    faltas = crud_loans.faltantes_para_confirmar(db, prestamo)
    if faltas:
        raise TransicionInvalida(" ".join(faltas))

    if prestamo.entregado_por_user_id is None:
        prestamo.entregado_por_user_id = current_user.id

    crud_loans.confirmar(db, prestamo, current_user)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.confirm",
        target_type="loan",
        target_id=prestamo.id,
        details=prestamo.folio,
    )

    # Los correos van en BackgroundTasks: un SMTP caido jamas tumba el registro
    # del prestamo. El equipo ya salio por la puerta; que el aviso falle no puede
    # deshacer eso (§10.15).
    notificaciones.encolar(
        db,
        plantillas_correo.TIPO_CONFIRMADO_APROBADOR,
        prestamo,
        background_tasks,
        con_responsiva=True,
    )
    if prestamo.responsable_email:
        notificaciones.encolar(
            db,
            plantillas_correo.TIPO_CONFIRMADO_RESPONSABLE,
            prestamo,
            background_tasks,
            destinatarios=[prestamo.responsable_email],
            con_responsiva=True,
        )
    return _ficha(db, prestamo)


@router.post("/{loan_id:int}/cancelar", response_model=schemas_loans.LoanDetail)
def cancelar_prestamo(
    loan_id: int,
    data: schemas_loans.CancelarRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "cancelar")),
):
    """Solo desde `borrador`: es la unica flecha de cancelacion del diagrama del
    contrato. El plan §5 decia "borrador/prestado sin devolucion"; manda el
    contrato. Reportado, porque sin cancelacion desde `prestado` no hay forma de
    anular un prestamo mal capturado que ya quemo folio.

    **Ojo con el permiso:** `equipos_prestamos:cancelar` no lo concede ningun
    paquete del catalogo congelado — solo el comodin de `superadmin`. Como un
    borrador con renglones ya reserva sus equipos, hoy un borrador abandonado
    solo lo puede liberar el superadmin. Reportado como defecto de contrato.
    """
    prestamo = _prestamo_visible(request, db, current_user, loan_id)
    _exigir_estado(prestamo, loan_state.Accion.CANCELAR)

    crud_loans.cancelar(db, prestamo, current_user, data.motivo)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.cancel",
        target_type="loan",
        target_id=prestamo.id,
        details=data.motivo,
    )
    return _ficha(db, prestamo)


@router.post("/{loan_id:int}/devolucion", response_model=schemas_loans.LoanDetail)
def registrar_devolucion(
    loan_id: int,
    data: schemas_loans.DevolucionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_prestamos", "registrar_devolucion")),
):
    prestamo = _prestamo_visible(request, db, current_user, loan_id)
    _exigir_estado(prestamo, loan_state.Accion.DEVOLUCION)

    ids_validos = {item.id for item in prestamo.items}
    declarados: dict[int, dict] = {}
    for declarado in data.items:
        if declarado.loan_item_id not in ids_validos:
            raise NoEncontrado(
                f"El renglon {declarado.loan_item_id} no pertenece a este prestamo."
            )
        declarados[declarado.loan_item_id] = declarado.model_dump()

    por_item, _ = crud_loans._mapa_media(db, prestamo.id)
    faltas = crud_loans.faltantes_para_devolucion(db, prestamo, por_item, declarados)
    if faltas:
        raise TransicionInvalida(" ".join(faltas))

    crud_loans.registrar_devolucion(db, prestamo, declarados, data.fecha_regreso_real, current_user)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.return",
        target_type="loan",
        target_id=prestamo.id,
    )
    notificaciones.encolar(
        db, plantillas_correo.TIPO_DEVOLUCION_APROBADOR, prestamo, background_tasks
    )
    return _ficha(db, prestamo)


__all__ = ["router", "_ver_global", "_prestamo_visible"]
