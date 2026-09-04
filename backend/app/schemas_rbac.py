"""Schemas del RBAC aditivo.

El contrato v1 (§7) congela ruta, metodo y permiso de estos endpoints, pero no
la forma del cuerpo. Estas formas son propuesta del servidor; si el cliente
necesita otra cosa se pide cambio de contrato, no se cambia de un solo lado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RolResponse(BaseModel):
    """Un paquete del catalogo con lo que abre, ya en forma de transporte
    (listas, no sets)."""

    name: str
    kind: str  # base | aditivo | piso
    descripcion: str
    is_active: bool
    permisos: Dict[str, List[str]] = {}
    singleton: bool = False


class GrantResponse(BaseModel):
    user_id: int
    role_name: str
    kind: str
    descripcion: str
    granted_by: Optional[int] = None
    granted_at: Optional[datetime] = None
    singleton: bool = False


class UserRolesResponse(BaseModel):
    """Rol base + aditivos + el set efectivo ya resuelto.

    El set efectivo va aqui a proposito: sin el, la pantalla de administracion
    tendria que replicar la union de paquetes en el navegador, y esa copia se
    desincroniza el dia que cambie una regla.
    """

    user_id: int
    role_base: str
    aditivos: List[GrantResponse] = []
    permisos_efectivos: Dict[str, List[str]] = {}


class ConcederRolRequest(BaseModel):
    role_name: str = Field(..., min_length=1, max_length=50)
