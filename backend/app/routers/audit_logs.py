"""Consulta de auditoria (solo superadmin, via permiso `auditoria:ver`).

Nota de diseno: el prompt original pedia `require_role("superadmin")` para
estos endpoints, igual que el resto de rutas de superadmin. Se usa en su
lugar `require_perm("auditoria", "ver")` (el permiso que este mismo cambio
agrega al catalogo) por consistencia con roles.py/user_roles.py/users.py,
que ya migraron de `require_role` a `require_perm` -- practicamente
equivalente hoy (solo superadmin lo tiene, via el comodin `*`), pero deja el
permiso nuevo con un uso real en vez de decorativo.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud_audit, models, schemas_audit
from ..database import get_db
from ..rbac import require_perm

router = APIRouter(prefix="/api/audit-logs", tags=["auditoria"])


@router.get("/", response_model=schemas_audit.AuditLogListResponse)
def listar_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=crud_audit.PAGE_SIZE_MAX),
    actor_user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    http_method: Optional[str] = Query(None),
    endpoint_path: Optional[str] = Query(None),
    response_status: Optional[int] = Query(None),
    target_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("auditoria", "ver")),
):
    filas, total = crud_audit.listar(
        db,
        page=page,
        page_size=page_size,
        actor_user_id=actor_user_id,
        action=action,
        http_method=http_method,
        endpoint_path=endpoint_path,
        response_status=response_status,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return schemas_audit.AuditLogListResponse(
        items=[crud_audit.a_item(db, f) for f in filas],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get("/stats", response_model=schemas_audit.AuditLogStats)
def ver_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("auditoria", "ver")),
):
    return schemas_audit.AuditLogStats(**crud_audit.stats(db))


@router.get("/{log_id}", response_model=schemas_audit.AuditLogItem)
def ver_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("auditoria", "ver")),
):
    fila = crud_audit.obtener(db, log_id)
    if not fila:
        raise HTTPException(status_code=404, detail="Entrada de auditoria no encontrada.")
    return schemas_audit.AuditLogItem(**crud_audit.a_item(db, fila))


__all__ = ["router"]
