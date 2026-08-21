"""Schemas del modulo Gastos Operativos (rubros + gastos).

El alta de un gasto llega como multipart (Form + archivo), asi que no hay un
schema de entrada para ese caso: la validacion vive en el router, igual que en
`general_expenses`. Aqui van los schemas de rubro y las respuestas.

`file_path` NO se expone en las respuestas (a diferencia de
`GeneralExpenseResponse`): es una ruta interna del servidor y el cliente solo
necesita el id para pedir el comprobante a `GET /{id}/file`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Rubros (catalogo) ────────────────────────────────────────────────────────


class RubroCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)


class RubroUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class RubroResponse(BaseModel):
    id: int
    nombre: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Gastos ───────────────────────────────────────────────────────────────────


class OperationalExpenseResponse(BaseModel):
    id: int
    rubro_id: int
    rubro_nombre: Optional[str] = None
    amount: float
    description: str
    fecha_gasto: date
    file_name: str
    mime_type: str
    upload_date: datetime
    created_by_user_id: Optional[int] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Dashboard / export ───────────────────────────────────────────────────────


class RubroTotalItem(BaseModel):
    rubro_id: int
    rubro_nombre: str
    total: float
    count: int


class OperationalMonthlyItem(BaseModel):
    month: str  # "2026-07"
    total: float
    count: int


class OperationalDashboardResponse(BaseModel):
    total: float
    count: int
    por_rubro: List[RubroTotalItem]
    mensual: List[OperationalMonthlyItem]


class OperationalExportResponse(BaseModel):
    months: List[str]
    items: List[OperationalExpenseResponse]
    total: float
