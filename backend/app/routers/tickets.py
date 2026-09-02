"""REST endpoints for tickets — carga con validación (R10) y ciclos de presupuesto (R7)."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db, SessionLocal
from ..dependencies import get_current_user, require_role
from ..rbac import require_rol_o_paquete, tiene_paquete
from ..upload_manager import save_upload, delete_upload

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

VALID_STATUSES = {s.value for s in models.TicketStatus}

# Roles que pueden LISTAR tickets y DESCARGAR comprobantes. Roles sin acceso a
# Presupuestos (colaborador_mkt, usuario, paquetes solo-equipos) reciben 403:
# sin esto el listado global (montos, notas, rutas de disco) quedaba abierto a
# cualquier sesión autenticada (hallazgo de la auditoría de seguridad
# 2026-08-18). El scoping fino (creador ve lo suyo, marketing_basico lo que
# subió) se aplica aparte, igual que en download_file.
ROLES_CON_TICKETS = (
    "superadmin", "admin", "marketing_presupuestos", "marketing_admin",
    "creador", "marketing_basico",
)

PAQUETE_APROBADOR = "APROBADOR_PRESUPUESTOS"


def _puede_ver_tickets(current_user: models.User, db: Session) -> bool:
    """`ROLES_CON_TICKETS` + la excepcion puntual del paquete aditivo: sin esto,
    alguien con rol base fuera de esa lista (p. ej. `usuario`) que recibe
    APROBADOR_PRESUPUESTOS puede aprobar/rechazar via API pero nunca ve la cola
    de Validacion, porque list_tickets/download_file lo rechazarian antes."""
    return current_user.role in ROLES_CON_TICKETS or tiene_paquete(db, current_user, PAQUETE_APROBADOR)


def _ticket_to_response(t: models.Ticket) -> schemas.TicketResponse:
    cycle = t.budget_cycle
    return schemas.TicketResponse(
        id=t.id,
        creator_id=t.creator_id,
        brand_id=t.brand_id,
        budget_cycle_id=t.budget_cycle_id,
        amount=t.amount,
        status=t.status,
        rejection_reason=t.rejection_reason,
        reviewed_by_user_id=t.reviewed_by_user_id,
        reviewed_at=t.reviewed_at,
        file_name=t.file_name,
        file_path=t.file_path,
        mime_type=t.mime_type,
        upload_date=t.upload_date,
        notes=t.notes,
        creator_name=t.creator.name if t.creator else None,
        brand_name=t.brand.name if t.brand else None,
        brand_priority=t.brand.priority if t.brand else None,
        cycle_amount=cycle.amount if cycle else None,
        cycle_spent=cycle.spent if cycle else None,
        is_deleted=t.is_deleted,
        deleted_at=t.deleted_at,
    )


@router.get("/", response_model=List[schemas.TicketResponse])
def list_tickets(
    creator_name: Optional[str] = None,
    brand_name: Optional[str] = None,
    status: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: '{status}'.")

    if not _puede_ver_tickets(current_user, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")

    # `limit`/`offset` opcionales (sin cambio de contrato: sin ellos se
    # comporta exactamente igual que antes). El filtro por creador/usuario
    # ahora se aplica en SQL, no trayendo todo y filtrando en Python despues
    # -- si no, limit/offset paginarian sobre el total de la tabla, no sobre
    # lo que el rol puede ver, y un creador podria perder tickets propios.
    if current_user.role == "creador":
        # Se ignora cualquier filtro por nombre de creador: un creador solo ve lo suyo.
        tickets = crud.get_tickets(
            db, brand_name=brand_name, status=status,
            creator_id=current_user.creator_id, limit=limit, offset=offset,
        )
    elif current_user.role == "marketing_basico":
        # "ver_propio" para este rol es lo que EL subio, no un creator_id propio
        # (no son creadores de contenido). Ver organigrama de accesos jul-2026.
        tickets = crud.get_tickets(
            db, creator_name=creator_name, brand_name=brand_name, status=status,
            uploaded_by_user_id=current_user.id, limit=limit, offset=offset,
        )
    else:
        tickets = crud.get_tickets(
            db, creator_name=creator_name, brand_name=brand_name, status=status,
            limit=limit, offset=offset,
        )
    return [_ticket_to_response(t) for t in tickets]


@router.get("/brand-spend", response_model=List[schemas.BrandSpendItem])
def brand_spend_breakdown(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin", "marketing_presupuestos", "marketing_admin")),
):
    return crud.get_brand_spend_breakdown(db, start_date=start_date, end_date=end_date)


@router.get("/file/{ticket_id}")
def download_file(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.is_deleted:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")

    # Solo superadmin, admin, marketing_presupuestos/marketing_admin (Presupuestos
    # completo), creador (dueño del ticket) y marketing_basico (solo lo que el
    # mismo subio) pueden descargar comprobantes. Roles sin acceso a Presupuestos
    # (colaborador_mkt, usuario) reciben 403 (hallazgo #2 auditoría).
    if not _puede_ver_tickets(current_user, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")
    if current_user.role == "creador" and ticket.creator_id != current_user.creator_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")
    if current_user.role == "marketing_basico" and ticket.uploaded_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")
    return FileResponse(path=ticket.file_path, media_type=ticket.mime_type, filename=ticket.file_name)


@router.post("/", response_model=schemas.TicketResponse, status_code=201)
def create_ticket(
    creator_id: int = Form(...),
    brand_id: int = Form(...),
    amount: float = Form(..., gt=0),
    notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "creador" and creator_id != current_user.creator_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")

    db: Session = SessionLocal()
    file_path_on_disk: Optional[str] = None

    try:
        creator = crud.get_creator(db, creator_id)
        if not creator:
            raise HTTPException(status_code=404, detail="Creador no encontrado.")
        if not creator.is_active:
            raise HTTPException(status_code=400, detail="El creador está inactivo.")

        brand = crud.get_brand(db, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Marca no encontrada.")
        if not brand.is_active:
            raise HTTPException(status_code=400, detail="La marca esta inactiva.")

        # R10: tickets de creador nacen pendientes (no descuentan); admin/superadmin
        # se auto-aprueban de inmediato (flujo actual). TODO rol nuevo (marketing_*,
        # colaborador_mkt, usuario) también nace pendiente y pasa por validación:
        # antes, "cualquiera que no fuera creador" se auto-aprobaba y descontaba
        # presupuesto de cualquier creador sin revisión (auditoría 2026-08-18).
        # Ningún flujo valida fondos — los ciclos pueden quedar en negativo a
        # propósito (ver R7 §0.B).
        auto_aprobado = current_user.role in ("admin", "superadmin")
        status = (
            models.TicketStatus.APROBADO.value
            if auto_aprobado
            else models.TicketStatus.PENDIENTE.value
        )

        file_name, file_path_on_disk, mime_type = save_upload(file)

        ticket = crud.create_ticket(
            db=db,
            creator=creator,
            brand=brand,
            amount=amount,
            file_name=file_name,
            file_path=file_path_on_disk,
            mime_type=mime_type,
            notes=notes,
            status=status,
            actor_user_id=current_user.id,
        )
        crud.log_audit(
            db,
            actor_user_id=current_user.id,
            action="ticket.create",
            target_type="ticket",
            target_id=ticket.id,
            details=f"status={status}",
        )

        return _ticket_to_response(ticket)

    except HTTPException:
        db.rollback()
        if file_path_on_disk:
            delete_upload(file_path_on_disk)
        raise
    except Exception as exc:
        db.rollback()
        if file_path_on_disk:
            delete_upload(file_path_on_disk)
        raise HTTPException(status_code=500, detail=f"Error inesperado al crear el ticket: {exc}")
    finally:
        db.close()


# aprobar/rechazar/soft-delete se quedan en require_role("admin","superadmin")
# a pelo (no en require_perm), con require_rol_o_paquete sumando la excepcion
# puntual de APROBADOR_PRESUPUESTOS por encima. Ojo: rbac_catalog.py ya lista
# "validar_ticket"/"borrar_ticket" para marketing_presupuestos/marketing_admin,
# pero como esta ruta nunca consulto ese catalogo, esos roles NO pueden aprobar
# ni borrar tickets hoy pese a lo que dice el catalogo — es una discrepancia
# preexistente, no algo que este cambio corrija (decision explicita: hacerlo
# extendería el permiso a roles base ya existentes, no solo a la excepcion
# puntual pedida).
@router.post("/{ticket_id}/aprobar", response_model=schemas.TicketResponse)
def aprobar_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_rol_o_paquete("admin", "superadmin", paquete=PAQUETE_APROBADOR)
    ),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.is_deleted:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")
    if ticket.status != models.TicketStatus.PENDIENTE.value:
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar tickets pendientes.")

    ticket = crud.approve_ticket(db, ticket, actor_user_id=current_user.id)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="ticket.approve",
        target_type="ticket",
        target_id=ticket.id,
    )
    return _ticket_to_response(ticket)


@router.post("/{ticket_id}/rechazar", response_model=schemas.TicketResponse)
def rechazar_ticket(
    ticket_id: int,
    data: schemas.TicketRejectRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_rol_o_paquete("admin", "superadmin", paquete=PAQUETE_APROBADOR)
    ),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.is_deleted:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")
    if ticket.status != models.TicketStatus.PENDIENTE.value:
        raise HTTPException(status_code=400, detail="Solo se pueden rechazar tickets pendientes.")

    ticket = crud.reject_ticket(db, ticket, reason=data.reason, actor_user_id=current_user.id)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="ticket.reject",
        target_type="ticket",
        target_id=ticket.id,
        details=data.reason,
    )
    return _ticket_to_response(ticket)


@router.post("/{ticket_id}/soft-delete", response_model=schemas.TicketResponse)
def soft_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_rol_o_paquete("admin", "superadmin", paquete=PAQUETE_APROBADOR)
    ),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket or ticket.is_deleted:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")

    ticket = crud.soft_delete_ticket(db, ticket, actor_user_id=current_user.id)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="ticket.soft-delete",
        target_type="ticket",
        target_id=ticket.id,
    )
    return _ticket_to_response(ticket)


@router.delete("/{ticket_id}/permanent", response_model=schemas.MessageResponse)
def hard_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    # A proposito NO acepta el paquete aditivo APROBADOR_PRESUPUESTOS: el borrado
    # fisico borra el archivo y la fila sin dejar rastro (irreversible, a
    # diferencia de soft-delete). Se queda exclusivo de admin/superadmin.
    current_user: models.User = Depends(require_role("admin", "superadmin")),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado.")

    ticket_id_for_log = ticket.id
    crud.hard_delete_ticket(db, ticket)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="ticket.hard-delete",
        target_type="ticket",
        target_id=ticket_id_for_log,
    )
    return schemas.MessageResponse(message="Ticket eliminado permanentemente.")
