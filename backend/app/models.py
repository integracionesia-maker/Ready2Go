"""SQLAlchemy ORM models for creators, brands, tickets, and authentication."""

from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, Index, text,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, enum.Enum):
    """Roles soportados. Extensible: agregar un valor aquí + su fila en la matriz
    de permisos (doc/auth-diseno-fase1.md §2) no requiere migración de esquema."""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    CREADOR = "creador"
    # Marketing — Presupuestos (acceso completo al módulo de Presupuestos,
    # cero acceso a Equipos). Para el equipo de marketing que maneja
    # creadores, marcas, tickets y validación.
    MARKETING_PRESUPUESTOS = "marketing_presupuestos"
    # Marketing — Equipos (acceso completo al módulo de Equipos: inventario,
    # préstamos, devoluciones). Sin aprobación — ese es un permiso extra
    # (APROBADOR_EQUIPO). Cero acceso a Presupuestos.
    MARKETING_EQUIPOS = "marketing_equipos"
    # Marketing — Administrador (organigrama de accesos, jul-2026). Presupuestos
    # completo + Equipos completo, SIN aprobación (esa sigue siendo exclusiva
    # de "admin" — la jefa de departamento). Un nivel debajo de "admin".
    MARKETING_ADMIN = "marketing_admin"
    # Marketing — acceso básico (organigrama de accesos, jul-2026). Solo subir
    # tickets propios y solicitar préstamos de equipo; ve unicamente lo que
    # ellos mismos subieron/solicitaron. Sin dashboards ni gestión.
    MARKETING_BASICO = "marketing_basico"
    # Legacy — migrado a marketing_equipos/marketing_basico. Se conserva para
    # no romper usuarios existentes; el seeder ya no lo asigna.
    COLABORADOR_MKT = "colaborador_mkt"
    # Empleado general sin acceso por defecto a ningun modulo (solo el piso:
    # inicio + perfil propio). Todo acceso se concede via paquetes aditivos.
    USUARIO = "usuario"


class CyclePeriod(str, enum.Enum):
    SEMANAL = "semanal"
    MENSUAL = "mensual"


class TicketStatus(str, enum.Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class BrandPriority(str, enum.Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class Creator(Base):
    __tablename__ = "creators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    # Histórico acumulado — congelado desde la migración a ciclos (R7); ya no se
    # escribe en ningún flujo nuevo, solo se conserva como snapshot informativo.
    initial_budget = Column(Float, nullable=False, default=0.0)
    spent_budget = Column(Float, nullable=False, default=0.00)
    remaining_budget = Column(Float, nullable=False, default=0.00)
    # Configuración vigente para el PRÓXIMO ciclo a materializar (get_or_create_cycle_for_date).
    # Cambiarla nunca afecta ciclos ya creados (doc/mejoras-diseno-fase1.md §0.D).
    cycle_budget_amount = Column(Float, nullable=True)
    cycle_period = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    tickets = relationship("Ticket", back_populates="creator", lazy="selectin")
    budget_cycles = relationship(
        "BudgetCycle", back_populates="creator", cascade="all, delete-orphan"
    )


class BudgetCycle(Base):
    """Un periodo de presupuesto (semanal o mensual) para un creador. Se crea
    perezosamente (get_or_create_cycle_for_date) — nunca por cron. Es un snapshot
    inmutable: su `amount`/fechas no cambian una vez creado, aunque el creador
    reconfigure su ciclo/monto para ciclos futuros."""

    __tablename__ = "budget_cycles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False)
    period_type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    spent = Column(Float, nullable=False, default=0.0)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    creator = relationship("Creator", back_populates="budget_cycles")
    tickets = relationship("Ticket", back_populates="budget_cycle")

    __table_args__ = (
        Index("ix_budget_cycles_creator_dates", "creator_id", "start_date", "end_date"),
    )


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    priority = Column(String(20), nullable=False, default=BrandPriority.MEDIA.value)
    is_active = Column(Boolean, nullable=False, default=True)

    tickets = relationship("Ticket", back_populates="brand", lazy="selectin")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="RESTRICT"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
    budget_cycle_id = Column(
        Integer, ForeignKey("budget_cycles.id", ondelete="SET NULL"), nullable=True
    )
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default=TicketStatus.PENDIENTE.value)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    # Quien subio el ticket (distinto de creator_id: ese es el creador de
    # contenido AL QUE pertenece el gasto, no quien lo cargo). Nullable porque
    # tickets viejos no lo tienen. Permite acotar "ver_propio" a roles que no
    # son "creador" y no tienen creator_id propio (ej. marketing_basico).
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    upload_date = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    notes = Column(Text, nullable=True)

    # Soft delete (R12): un ticket borrado deja de contar para todo cálculo pero
    # el registro y el archivo se conservan (auditoría). Ver doc/borrado-tickets.md.
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    creator = relationship("Creator", back_populates="tickets")
    brand = relationship("Brand", back_populates="tickets")
    budget_cycle = relationship("BudgetCycle", back_populates="tickets", lazy="selectin")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id], lazy="selectin")
    deleted_by = relationship("User", foreign_keys=[deleted_by_user_id], lazy="selectin")


class GeneralExpense(Base):
    """Gasto operativo vinculado a una marca (apps, servicios, suscripciones, etc.).
    Tabla independiente de `tickets` a propósito: no tiene ciclo de presupuesto
    ni estado de validación — se crea y cuenta de inmediato (solo admin/superadmin,
    ver doc/gastos-generales-manual.md).

    Tiene brand_id (no nullable) porque TODO gasto general debe estar asociado a
    una marca para trazabilidad y reportes por marca."""

    __tablename__ = "general_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    upload_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    brand = relationship("Brand", lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    deleted_by = relationship("User", foreign_keys=[deleted_by_user_id], lazy="selectin")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(20), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    token_version = Column(Integer, nullable=False, default=0)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator = relationship("Creator")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Un Creator tiene a lo sumo un usuario vinculado (NULL = sin vincular, permitido).
        Index(
            "ix_users_creator_id_unique",
            "creator_id",
            unique=True,
            sqlite_where=text("creator_id IS NOT NULL"),
        ),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(Integer, ForeignKey("refresh_tokens.id"), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Campos del middleware de auditoria automatica (backend/app/middleware_audit.py).
    # Nullable a proposito: las llamadas manuales a log_audit() de mas arriba
    # (login, cambios de usuario, concesion de roles, etc.) siguen escribiendo
    # solo los campos de siempre y coexisten con estas filas nuevas, mas
    # genericas, del middleware -- ninguna reemplaza a la otra.
    http_method = Column(String(10), nullable=True)
    endpoint_path = Column(String(255), nullable=True)
    request_params = Column(Text, nullable=True)
    request_body_summary = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True)
    user_agent = Column(String(255), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    __table_args__ = (
        # created_at: orden por defecto y filtro de rango de fecha en cada
        # GET /api/audit-logs/. actor_user_id: filtro directo por usuario.
        # Sin estos, cada request de esa pantalla es un table scan completo.
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_actor_user_id", "actor_user_id"),
    )


# Re-export al final, no arriba: los modulos de abajo referencian tablas de este
# archivo por nombre de cadena, nunca por import, para no cerrar un ciclo.
# Importarlos aqui es lo que registra sus tablas en Base.metadata.
from .models_rbac import *  # noqa: E402,F401,F403
from .models_equipos import *  # noqa: E402,F401,F403
