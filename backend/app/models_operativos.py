"""Tablas del modulo Gastos Operativos.

Acumulador de gastos **aislado de marketing**: no toca `tickets`,
`general_expenses`, `brands`, ciclos ni ningun dashboard de Presupuestos. Cada
gasto se clasifica en un `rubro` (catalogo propio, editable desde la app).

Regla de este archivo (igual que `models_equipos`/`models_rbac`): **nunca
importa `app.models`**. Las FKs a `users` se declaran por nombre de tabla en
cadena; `models.py` re-exporta este modulo al final para registrar las tablas en
`Base.metadata`. Un import en sentido contrario cierra el ciclo y rompe el
arranque.

Dos decisiones que se prestan a confusion y por eso viven aqui:

1. **Dos fechas.** `fecha_gasto` (manual) es la que define el mes/periodo: un
   gasto hecho el 30 y subido el 4 cuenta en el mes del 30. `upload_date`
   (automatica) es solo trazabilidad. Todo bucketing mensual y todo filtro por
   rango se hace por `fecha_gasto`, nunca por `upload_date`.
2. **Solo borrado logico.** `is_deleted=True` saca el gasto de todo calculo pero
   conserva registro y archivo. No hay borrado fisico (a diferencia de
   `general_expenses`): estos gastos son evidencia contable.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base

__all__ = ["ExpenseRubro", "OperationalExpense"]


class ExpenseRubro(Base):
    """Catalogo de rubros (clasificacion del gasto). Espejo de `brands`:
    editable desde la app, con nombre unico y baja logica por `is_active`.

    Desactivar un rubro lo oculta de las altas nuevas pero conserva el historico:
    los gastos ya registrados lo siguen referenciando (FK RESTRICT)."""

    __tablename__ = "expense_rubros"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    expenses = relationship("OperationalExpense", back_populates="rubro")


class OperationalExpense(Base):
    """Un gasto operativo. Espejo de `general_expenses` con dos fechas y sin
    borrado fisico (ver el docstring del modulo)."""

    __tablename__ = "operational_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # RESTRICT: un rubro con gastos no se puede borrar; solo desactivar.
    rubro_id = Column(Integer, ForeignKey("expense_rubros.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=False)

    # La fecha que define el mes/periodo. Se captura a mano.
    fecha_gasto = Column(Date, nullable=False)

    # Comprobante obligatorio (nullable=False en las tres columnas del archivo).
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)

    # Automatica: cuando se subio. Solo trazabilidad, no cuenta para el mes.
    upload_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Solo borrado logico. No existe hard delete.
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    rubro = relationship("ExpenseRubro", back_populates="expenses", lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    deleted_by = relationship("User", foreign_keys=[deleted_by_user_id], lazy="selectin")

    __table_args__ = (
        Index("ix_operational_expenses_rubro", "rubro_id"),
        Index("ix_operational_expenses_fecha", "fecha_gasto"),
    )
