"""REST endpoints for tickets — carga con validación (R10) y ciclos de presupuesto (R7)."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db, SessionLocal
from ..dependencies import get_current_user, require_role
from ..upload_manager import save_upload, delete_upload

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

VALID_STATUSES = {s.value for s in models.TicketStatus}


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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: '{status}'.")

    if current_user.role == "creador":
        # Se ignora cualquier filtro por nombre de creador: un creador solo ve lo suyo.
        tickets = crud.get_tickets(db, creator_name=None, brand_name=brand_name, status=status)
        tickets = [t for t in tickets if t.creator_id == current_user.creator_id]
    else:
        tickets = crud.get_tickets(db, creator_name=creator_name, brand_name=brand_name, status=status)
    return [_ticket_to_response(t) for t in tickets]


@router.get("/brand-spend", response_model=List[schemas.BrandSpendItem])
def brand_spend_breakdown(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin")),
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

    # Solo superadmin, admin y creador (dueño del ticket) pueden descargar
    # comprobantes. Roles sin acceso a Presupuestos (colaborador_mkt, usuario)
    # reciben 403 (hallazgo #2 auditoría).
    if current_user.role not in ("superadmin", "admin", "creador"):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción.")
    if current_user.role == "creador" and ticket.creator_id != current_user.creator_id:
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
            raise HTTPException(status_code=400, detail="El creador esta inactivo.")

        brand = crud.get_brand(db, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Marca no encontrada.")
        if not brand.is_active:
            raise HTTPException(status_code=400, detail="La marca esta inactiva.")

        # R10: tickets de creador nacen pendientes (no descuentan); admin/superadmin
        # se auto-aprueban de inmediato (flujo actual). Ninguno de los dos valida
        # fondos — los ciclos pueden quedar en negativo a propósito (ver R7 §0.B).
        status = (
            models.TicketStatus.PENDIENTE.value
            if current_user.role == "creador"
            else models.TicketStatus.APROBADO.value
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


@router.post("/{ticket_id}/aprobar", response_model=schemas.TicketResponse)
def aprobar_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin", "superadmin")),
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
    current_user: models.User = Depends(require_role("admin", "superadmin")),
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
    current_user: models.User = Depends(require_role("admin", "superadmin")),
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
