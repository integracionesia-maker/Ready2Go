"""Pydantic schemas for request/response validation."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class CreatorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cycle_budget_amount: float = Field(..., gt=0, description="Monto del ciclo (semanal/mensual)")
    cycle_period: str = Field(..., description="'semanal' o 'mensual'")
    initial_budget: float = Field(0.0, ge=0, description="Histórico acumulado, opcional")
    # Datos para crear el usuario vinculado (rol "creador")
    # El full_name del usuario se toma del name del creador automáticamente
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., max_length=255)


class CreatorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    initial_budget: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    cycle_budget_amount: Optional[float] = Field(None, gt=0)
    cycle_period: Optional[str] = None


class CreatorResponse(BaseModel):
    id: int
    name: str
    initial_budget: float
    spent_budget: float
    remaining_budget: float
    is_active: bool
    created_at: datetime
    cycle_period: Optional[str] = None
    cycle_amount: Optional[float] = None
    cycle_spent: Optional[float] = None
    # Solo presente al crear (POST): contraseña temporal del usuario vinculado
    temporary_password: Optional[str] = None
    cycle_remaining: Optional[float] = None
    cycle_start_date: Optional[date] = None
    cycle_end_date: Optional[date] = None

    model_config = {"from_attributes": True}


class CreatorKpiResponse(BaseModel):
    total_budget: float
    total_spent: float
    total_remaining: float
    active_creators: int


class BudgetCycleResponse(BaseModel):
    id: int
    creator_id: int
    period_type: str
    amount: float
    spent: float
    remaining: float
    start_date: date
    end_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class BrandBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class BrandCreate(BrandBase):
    priority: str = Field("media", description="'alta' | 'media' | 'baja'")


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    priority: Optional[str] = None


class BrandResponse(BrandBase):
    id: int
    is_active: bool
    priority: str

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: int
    creator_id: int
    brand_id: int
    budget_cycle_id: Optional[int] = None
    amount: float
    status: str
    rejection_reason: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    file_name: str
    file_path: str
    mime_type: str
    upload_date: datetime
    notes: Optional[str] = None
    creator_name: Optional[str] = None
    brand_name: Optional[str] = None
    brand_priority: Optional[str] = None
    cycle_amount: Optional[float] = None
    cycle_spent: Optional[float] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TicketRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class BrandSpendItem(BaseModel):
    brand_name: str
    total_spent: float
    priority: str = "media"


class MessageResponse(BaseModel):
    message: str


# ── Gastos generales (R12) ──────────────────────────────────────────────────


class GeneralExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    brand_id: int = Field(..., gt=0)


class GeneralExpenseResponse(BaseModel):
    id: int
    brand_id: int
    amount: float
    description: str
    file_name: str
    file_path: str
    mime_type: str
    upload_date: datetime
    created_by_user_id: Optional[int] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    brand_name: Optional[str] = None
    brand_priority: Optional[str] = None

    model_config = {"from_attributes": True}


class GeneralExpenseMonthlyItem(BaseModel):
    month: str  # "2026-07"
    total: float
    count: int


class GeneralExpensesExportResponse(BaseModel):
    months: List[str]
    items: List[GeneralExpenseResponse]
    total: float


# ── Dashboard ──────────────────────────────────────────────────────────────────


class MonthlySpendItem(BaseModel):
    month: str  # "2026-07"
    total: float
    count: int


class CreatorUsageItem(BaseModel):
    creator_id: int
    name: str
    spent: float
    initial_budget: float
    percentage: float  # 0-100


class DashboardSummary(BaseModel):
    total_spent: float
    ticket_count: int
    avg_ticket: float
    active_brands: int


# ── Autenticación ────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    identificador: str = Field(..., min_length=1, description="Nombre de usuario o correo")
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    role: str
    creator_id: Optional[int] = None
    is_active: bool
    must_change_password: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    # Permisos efectivos {modulo: [acciones]}. Solo GET /api/auth/me los llena;
    # el resto de endpoints que devuelven UserResponse (login, refresh, gestión
    # de usuarios) los dejan en {} a propósito, para no resolver RBAC en rutas
    # que no lo necesitan. Lista y no set porque JSON no tiene sets.
    permisos: dict[str, list[str]] = {}

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=10)


# ── Gestión de usuarios (Administración) ────────────────────────────────────


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=150)
    role: str
    password: Optional[str] = Field(None, min_length=10)
    creator_id: Optional[int] = None


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    creator_id: Optional[int] = None


class SetUserActiveRequest(BaseModel):
    is_active: bool


class ResetPasswordResponse(BaseModel):
    temporary_password: str
