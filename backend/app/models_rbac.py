"""Tablas del RBAC aditivo (patron Bruckner): `roles`, `role_permissions`,
`user_role_grants`.

Regla de este archivo: **nunca importa `app.models`**. Las llaves foraneas a
`users` se declaran por nombre de tabla en cadena; `models.py` re-exporta este
modulo al final para registrar las tablas en `Base.metadata`. Un import en
sentido contrario cierra el ciclo y rompe el arranque.

Que hace cada tabla:

- `roles` y `role_permissions` son la **materializacion** del catalogo que vive
  en `rbac_catalog.py`. Sirven para listar/inspeccionar y para que
  `user_role_grants` tenga a que apuntar con integridad referencial.
- `user_role_grants` es el unico dato de aqui que el motor consulta en caliente:
  que paquetes aditivos tiene concedidos un usuario. Es por usuario y cambia sin
  desplegar, asi que tiene que estar en la base.

Ver `doc/rbac-aditivo.md` para el por que de esa division.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base

__all__ = ["Role", "RolePermission", "UserRoleGrant"]


class Role(Base):
    """Catalogo de paquetes: base, aditivo o piso."""

    __tablename__ = "roles"

    name = Column(String(50), primary_key=True)
    kind = Column(String(20), nullable=False)  # base | aditivo | piso
    descripcion = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)

    # Carga diferida a proposito (lazy por defecto, no `selectin`): listar el
    # catalogo no debe arrastrar todas las concesiones de todos los usuarios.
    # Con `selectin` un simple GET /api/roles/ pegaba a user_role_grants sin que
    # nadie usara el resultado — y se caia si esa tabla no estaba.
    permisos = relationship(
        "RolePermission",
        back_populates="rol",
        cascade="all, delete-orphan",
    )
    grants = relationship("UserRoleGrant", back_populates="rol")


class RolePermission(Base):
    """Que (modulo, accion) abre un paquete. Sin fila = sin permiso."""

    __tablename__ = "role_permissions"

    role_name = Column(
        String(50), ForeignKey("roles.name", ondelete="CASCADE"), primary_key=True
    )
    modulo = Column(String(50), primary_key=True)
    accion = Column(String(50), primary_key=True)

    rol = relationship("Role", back_populates="permisos")

    __table_args__ = (
        Index("ix_role_permissions_modulo_accion", "modulo", "accion"),
    )


class UserRoleGrant(Base):
    """Paquete aditivo concedido a un usuario (0..n por usuario).

    `role_name` con `ON DELETE RESTRICT`: borrar un paquete concedido tiene que
    fallar en la base, no dejar una concesion apuntando al vacio.
    """

    __tablename__ = "user_role_grants"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_name = Column(
        String(50), ForeignKey("roles.name", ondelete="RESTRICT"), primary_key=True
    )
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    granted_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    rol = relationship("Role", back_populates="grants")
    # backref desde este lado: models.py tiene prohibido declarar relaciones
    # nuevas dentro de la clase User (ver docs/ASIGNACION_EQUIPOS.md).
    usuario = relationship(
        "User",
        foreign_keys=[user_id],
        backref="role_grants",
        lazy="selectin",
    )
    concedido_por = relationship("User", foreign_keys=[granted_by], lazy="selectin")
