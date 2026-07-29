"""Aprobacion de entregas y devoluciones (contrato §4).

Router propio bajo el mismo prefijo `/api/loans` que `loans.py`: FastAPI lo
acepta y asi el carril de aprobacion no obliga a tocar el archivo de prestamos.

Las tres rutas llevan segmentos en español (`/autorizar-entrega`,
`/confirmar-devolucion`, `/cerrar-incidencia`) aunque el §0 diga "rutas en
ingles, sin excepcion". Mandan las cadenas literales del §4: hay cliente
codificando contra ellas. Se reporta la inconsistencia, no se traduce.

Quien autoriza y quien confirma se toman **de la sesion**, nunca del cuerpo. En
la maqueta cualquiera elegia "Melisa" en un `<select>` y aprobaba en su nombre
(§10.4, CRITICO).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from .. import (
    crud,
    crud_loans,
    loan_state,
    models,
    notificaciones,
    plantillas_correo,
    schemas_loans,
)
from ..database import get_db
from ..errores import ErrorEquipos, NoEncontrado, TransicionInvalida
from ..models_equipos import DecisionDevolucion
from ..rbac import require_perm
from .loans import _prestamo_visible

router = APIRouter(prefix="/api/loans", tags=["approvals"])

DETALLE_SIN_AUTORIZAR = (
    "La entrega de este prestamo no esta autorizada. "
    "Autoriza la entrega antes de cerrar el prestamo."
)


def _exigir_autorizacion(prestamo, destino: str) -> None:
    """La guarda se evalua contra el estado DESTINO, no contra el actual.

    Con alguna decision distinta de `ok` el destino es `incompleto` y la
    operacion procede aunque nadie haya autorizado: si tambien se bloqueara ahi,
    un prestamo con incidencia y sin autorizar no tendria a donde ir.

    Se rechaza ANTES de escribir nada. Guardar las decisiones y quedarse en
    `pendiente_confirmacion` con un 200 seria un exito falso: el cliente pinta
    "confirmado" y el prestamo no cerro. Degradarlo a `incompleto` seria peor:
    dispara "requiere atencion" y el correo de incidencias cuando no hubo
    ninguna, y su unica salida esta bloqueada por esta misma guarda.
    """
    if loan_state.exige_autorizacion_de_entrega(destino) and not prestamo.entrega_autorizada:
        raise TransicionInvalida(DETALLE_SIN_AUTORIZAR)


@router.post("/{loan_id:int}/autorizar-entrega", response_model=schemas_loans.LoanDetail)
def autorizar_entrega(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_aprobacion", "autorizar_entrega")),
):
    """Ortogonal al estado: no lo cambia. Idempotente: reintentar no reescribe
    quien autorizo ni cuando.

    Se acepta desde `prestado`, `pendiente_confirmacion` e `incompleto`. Que
    `incompleto` entre es lo menos obvio y lo mas importante: sin eso, un
    prestamo que llego a incompleto sin autorizacion no se podria cerrar nunca.
    """
    prestamo = _prestamo_visible(request, db, current_user, loan_id)

    if not loan_state.acepta_autorizacion(prestamo.estado):
        raise TransicionInvalida(
            f"No se puede autorizar la entrega de un prestamo en estado '{prestamo.estado}'."
        )

    crud_loans.autorizar_entrega(db, prestamo, current_user)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.authorize",
        target_type="loan",
        target_id=prestamo.id,
        details=prestamo.folio,
    )
    return crud_loans.serializar_detalle(db, prestamo)


@router.post("/{loan_id:int}/confirmar-devolucion", response_model=schemas_loans.LoanDetail)
def confirmar_devolucion(
    loan_id: int,
    data: schemas_loans.ConfirmarDevolucionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_aprobacion", "confirmar_devolucion")),
):
    prestamo = _prestamo_visible(request, db, current_user, loan_id)

    validas = {d.value for d in DecisionDevolucion}
    ids_validos = {item.id for item in prestamo.items}
    decisiones: dict[int, dict] = {}

    for entrada in data.decisiones:
        if entrada.decision not in validas:
            raise ErrorEquipos(
                422,
                f"Decision invalida: '{entrada.decision}'. Validas: {', '.join(sorted(validas))}.",
                "VALOR_INVALIDO",
            )
        if entrada.loan_item_id not in ids_validos:
            raise NoEncontrado(
                f"El renglon {entrada.loan_item_id} no pertenece a este prestamo."
            )
        if entrada.loan_item_id in decisiones:
            raise ErrorEquipos(
                422, f"El renglon {entrada.loan_item_id} viene dos veces.", "VALOR_INVALIDO"
            )
        # Nota obligatoria si la decision no es 'ok' (§4). Sin ella, "danado"
        # queda sin explicacion y el cierre de incidencia no tiene contra que.
        if entrada.decision != DecisionDevolucion.OK.value and not (entrada.nota or "").strip():
            raise ErrorEquipos(
                422,
                f"Agrega una nota para el renglon {entrada.loan_item_id}: la decision no es 'ok'.",
                "VALOR_INVALIDO",
            )
        decisiones[entrada.loan_item_id] = entrada.model_dump()

    sin_decidir = sorted(ids_validos - set(decisiones))
    if sin_decidir:
        raise TransicionInvalida(
            f"Faltan las decisiones de {len(sin_decidir)} equipo. Se decide sobre todos o sobre ninguno."
        )

    destino = _validar_transicion(
        prestamo, [d["decision"] for d in decisiones.values()]
    )
    _exigir_autorizacion(prestamo, destino)

    crud_loans.confirmar_devolucion(db, prestamo, decisiones, destino, current_user)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.confirm_return",
        target_type="loan",
        target_id=prestamo.id,
        details=destino,
    )
    if prestamo.responsable_email:
        notificaciones.encolar(
            db,
            plantillas_correo.TIPO_DEVOLUCION_CONFIRMADA,
            prestamo,
            background_tasks,
            destinatarios=[prestamo.responsable_email],
        )
    return crud_loans.serializar_detalle(db, prestamo)


def _validar_transicion(prestamo, decisiones: list[str]) -> str:
    try:
        return loan_state.estado_destino(
            prestamo.estado, loan_state.Accion.CONFIRMAR_DEVOLUCION, decisiones
        )
    except loan_state.TransicionNoPermitida as exc:
        raise TransicionInvalida(exc.detalle) from exc


@router.post("/{loan_id:int}/cerrar-incidencia", response_model=schemas_loans.LoanDetail)
def cerrar_incidencia(
    loan_id: int,
    data: schemas_loans.CerrarIncidenciaRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_aprobacion", "cerrar_incidencia")),
):
    """`incompleto -> completado`, con nota obligatoria.

    En la maqueta `incompleto` era terminal: un equipo danado quedaba en revision
    para siempre (§10.12). Esta es su salida.
    """
    prestamo = _prestamo_visible(request, db, current_user, loan_id)

    try:
        destino = loan_state.estado_destino(
            prestamo.estado, loan_state.Accion.CERRAR_INCIDENCIA
        )
    except loan_state.TransicionNoPermitida as exc:
        raise TransicionInvalida(exc.detalle) from exc

    _exigir_autorizacion(prestamo, destino)

    crud_loans.cerrar_incidencia(db, prestamo, data.nota.strip(), current_user)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="loan.close_incident",
        target_type="loan",
        target_id=prestamo.id,
    )
    return crud_loans.serializar_detalle(db, prestamo)
