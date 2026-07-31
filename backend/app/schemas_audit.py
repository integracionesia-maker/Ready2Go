"""Schemas de la vista de auditoria (solo superadmin)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogItem(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    actor_full_name: Optional[str] = None
    action: str
    http_method: Optional[str] = None
    endpoint_path: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: Optional[str] = None
    request_params: Optional[str] = None
    request_body_summary: Optional[str] = None
    response_status: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogStats(BaseModel):
    requests_por_dia: Dict[str, int]
    top_endpoints: List[Dict[str, object]]
    top_usuarios: List[Dict[str, object]]
    distribucion_status: Dict[str, int]
