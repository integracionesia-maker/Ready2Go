"""Consultas de la vista de auditoria (solo superadmin)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models

PAGE_SIZE_MAX = 200

COLUMNAS_ORDENABLES = {
    "created_at": models.AuditLog.created_at,
    "action": models.AuditLog.action,
    "http_method": models.AuditLog.http_method,
    "endpoint_path": models.AuditLog.endpoint_path,
    "response_status": models.AuditLog.response_status,
    "duration_ms": models.AuditLog.duration_ms,
}


def _query_filtrada(
    db: Session,
    *,
    actor_user_id: Optional[int] = None,
    action: Optional[str] = None,
    http_method: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    response_status: Optional[int] = None,
    target_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    query = db.query(models.AuditLog)

    if actor_user_id is not None:
        query = query.filter(models.AuditLog.actor_user_id == actor_user_id)
    if action:
        query = query.filter(models.AuditLog.action.like(f"%{action}%"))
    if http_method:
        query = query.filter(models.AuditLog.http_method == http_method.upper())
    if endpoint_path:
        query = query.filter(models.AuditLog.endpoint_path.like(f"%{endpoint_path}%"))
    if response_status is not None:
        query = query.filter(models.AuditLog.response_status == response_status)
    if target_type:
        query = query.filter(models.AuditLog.target_type == target_type)
    if start_date is not None:
        query = query.filter(
            models.AuditLog.created_at >= datetime.combine(start_date, time.min)
        )
    if end_date is not None:
        query = query.filter(
            models.AuditLog.created_at <= datetime.combine(end_date, time.max)
        )
    if search:
        patron = f"%{search}%"
        query = query.filter(
            (models.AuditLog.details.like(patron))
            | (models.AuditLog.action.like(patron))
            | (models.AuditLog.endpoint_path.like(patron))
        )
    return query


def listar(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    **filtros,
) -> tuple[list, int]:
    page = max(1, page)
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))

    query = _query_filtrada(db, **filtros)
    total = query.count()

    columna = COLUMNAS_ORDENABLES.get(sort_by, models.AuditLog.created_at)
    columna = columna.desc() if sort_dir == "desc" else columna.asc()

    filas = (
        query.order_by(columna)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return filas, total


def obtener(db: Session, log_id: int) -> Optional[models.AuditLog]:
    return db.query(models.AuditLog).filter(models.AuditLog.id == log_id).first()


def _actor_info(db: Session, fila: models.AuditLog) -> dict:
    if fila.actor_user_id is None:
        return {"actor_username": None, "actor_full_name": None}
    usuario = db.query(models.User).filter(models.User.id == fila.actor_user_id).first()
    if not usuario:
        return {"actor_username": None, "actor_full_name": None}
    return {"actor_username": usuario.username, "actor_full_name": usuario.full_name}


def a_item(db: Session, fila: models.AuditLog) -> dict:
    """`AuditLogItem` necesita actor_username/actor_full_name via JOIN a
    `users`; se resuelve aqui en vez de forzar una relacion ORM nueva sobre
    `AuditLog` (que no la tiene, y no debe tenerla: el borrado de un usuario
    no debe arrastrar ni bloquear su historial de auditoria, por eso el FK es
    ON DELETE SET NULL)."""
    info = _actor_info(db, fila)
    return {
        "id": fila.id,
        "actor_user_id": fila.actor_user_id,
        **info,
        "action": fila.action,
        "http_method": fila.http_method,
        "endpoint_path": fila.endpoint_path,
        "target_type": fila.target_type,
        "target_id": fila.target_id,
        "details": fila.details,
        "request_params": fila.request_params,
        "request_body_summary": fila.request_body_summary,
        "response_status": fila.response_status,
        "ip_address": fila.ip_address,
        "user_agent": fila.user_agent,
        "duration_ms": fila.duration_ms,
        "created_at": fila.created_at,
    }


def stats(db: Session) -> dict:
    desde = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

    por_dia_filas = (
        db.query(
            func.date(models.AuditLog.created_at).label("dia"),
            func.count(models.AuditLog.id),
        )
        .filter(models.AuditLog.created_at >= desde)
        .group_by(func.date(models.AuditLog.created_at))
        .order_by(func.date(models.AuditLog.created_at))
        .all()
    )
    requests_por_dia = {dia: total for dia, total in por_dia_filas}

    top_endpoints_filas = (
        db.query(models.AuditLog.endpoint_path, func.count(models.AuditLog.id))
        .filter(models.AuditLog.endpoint_path.isnot(None))
        .group_by(models.AuditLog.endpoint_path)
        .order_by(func.count(models.AuditLog.id).desc())
        .limit(10)
        .all()
    )
    top_endpoints = [{"endpoint_path": ep, "total": total} for ep, total in top_endpoints_filas]

    top_usuarios_filas = (
        db.query(
            models.AuditLog.actor_user_id,
            models.User.username,
            func.count(models.AuditLog.id),
        )
        .join(models.User, models.User.id == models.AuditLog.actor_user_id)
        .group_by(models.AuditLog.actor_user_id, models.User.username)
        .order_by(func.count(models.AuditLog.id).desc())
        .limit(10)
        .all()
    )
    top_usuarios = [
        {"actor_user_id": uid, "username": username, "total": total}
        for uid, username, total in top_usuarios_filas
    ]

    distribucion_filas = (
        db.query(models.AuditLog.response_status, func.count(models.AuditLog.id))
        .filter(models.AuditLog.response_status.isnot(None))
        .group_by(models.AuditLog.response_status)
        .all()
    )
    distribucion_status = {str(status): total for status, total in distribucion_filas}

    return {
        "requests_por_dia": requests_por_dia,
        "top_endpoints": top_endpoints,
        "top_usuarios": top_usuarios,
        "distribucion_status": distribucion_status,
    }
