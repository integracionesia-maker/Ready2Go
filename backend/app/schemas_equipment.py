"""Schemas del inventario (contrato §2).

La fila del listado trae `tenedor_actual`, `fecha_regreso_esperada`, `atrasado` y
`dias_atraso` **ya resueltos**: el contrato lo pide explicito para que la
pantalla de inventario no tenga que hacer un segundo request por equipo. Y el
atraso lo calcula el servidor; el cliente nunca lo recalcula (contrato §0).
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class TenedorActual(BaseModel):
    nombre: Optional[str] = None
    user_id: Optional[int] = None


class EquipmentItem(BaseModel):
    """Fila del listado. Espejo de `docs/contratos/fixtures/equipos.json`."""

    id: int
    codigo: Optional[str] = None
    nombre: str
    categoria: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    activo_fijo: Optional[str] = None
    cuenta_gmail: Optional[str] = None
    espacio_disponible: Optional[str] = None
    estado_operativo: str

    # Derivados de la ultima auditoria de condicion, no columnas de `equipment`:
    # la condicion es historial, y guardarla en el equipo perderia el rastro de
    # como llego a estar asi.
    condicion: Optional[str] = None
    estado_fisico: Optional[str] = None
    comentario_auditoria: Optional[str] = None
    fecha_auditoria: Optional[date] = None

    accesorios_tipicos: List[str] = []

    # Derivados de los renglones abiertos. No hay `estado='prestado'`.
    disponible: bool
    tenedor_actual: Optional[TenedorActual] = None
    fecha_regreso_esperada: Optional[date] = None
    atrasado: bool = False
    dias_atraso: int = 0


class EquipmentListResponse(BaseModel):
    items: List[EquipmentItem]
    total: int


class AuditoriaResponse(BaseModel):
    id: int
    condicion: str
    estado_fisico: Optional[str] = None
    espacio_disponible: Optional[str] = None
    comentario: Optional[str] = None
    fecha: Optional[date] = None
    actor_user_id: Optional[int] = None
    actor_nombre: Optional[str] = None
    created_at: Optional[str] = None  # ISO-8601 con offset de CDMX


class HistorialPrestamoItem(BaseModel):
    loan_id: int
    folio: Optional[str] = None
    estado: str
    responsable: Optional[str] = None
    fecha_entrega: Optional[date] = None
    fecha_regreso_esperada: Optional[date] = None
    devuelto_at: Optional[str] = None
    decision: Optional[str] = None


class EquipmentDetail(EquipmentItem):
    """Ficha: la fila del listado + descripcion, auditorias e historial.

    El contrato §2 congela la ruta y el permiso pero no el cuerpo del detalle.
    Esta forma es propuesta del servidor; documentada en docs/avances/servidor.md.
    """

    descripcion: Optional[str] = None
    fotos_originales_url: Optional[str] = None
    auditorias: List[AuditoriaResponse] = []
    historial: List[HistorialPrestamoItem] = []


class EquipmentCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    codigo: Optional[str] = Field(None, max_length=50)
    categoria: Optional[str] = Field(None, max_length=120)
    descripcion: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=120)
    modelo: Optional[str] = Field(None, max_length=120)
    numero_serie: Optional[str] = Field(None, max_length=120)
    activo_fijo: Optional[str] = Field(None, max_length=120)
    cuenta_gmail: Optional[str] = Field(None, max_length=255)
    espacio_disponible: Optional[str] = Field(None, max_length=120)
    accesorios_tipicos: List[str] = []
    fotos_originales_url: Optional[str] = Field(None, max_length=512)


class EquipmentUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    codigo: Optional[str] = Field(None, max_length=50)
    categoria: Optional[str] = Field(None, max_length=120)
    descripcion: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=120)
    modelo: Optional[str] = Field(None, max_length=120)
    numero_serie: Optional[str] = Field(None, max_length=120)
    activo_fijo: Optional[str] = Field(None, max_length=120)
    cuenta_gmail: Optional[str] = Field(None, max_length=255)
    espacio_disponible: Optional[str] = Field(None, max_length=120)
    accesorios_tipicos: Optional[List[str]] = None
    fotos_originales_url: Optional[str] = Field(None, max_length=512)
    # `estado_operativo` se mueve por sus propios endpoints (`/baja`, la
    # confirmacion de devolucion, el cierre de incidencia). Dejarlo editable
    # aqui permitiria sacar un equipo de `revision` sin cerrar la incidencia.


class AuditoriaCreate(BaseModel):
    condicion: str = Field(..., description="bueno | atencion | danado")
    estado_fisico: Optional[str] = Field(None, description="nuevo | usado")
    espacio_disponible: Optional[str] = Field(None, max_length=120)
    comentario: Optional[str] = None
    fecha: Optional[date] = None


class BajaRequest(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)


# ── Dashboard (contrato §2) ─────────────────────────────────────────────────


class RequiereAtencionItem(BaseModel):
    loan_id: int
    folio: Optional[str] = None
    motivo: str
    responsable: Optional[str] = None
    equipos: List[str] = []


class DashboardEquiposResponse(BaseModel):
    prestados: int
    atrasados: int
    pendientes_confirmacion: int
    disponibles: int
    por_estado: dict[str, int]
    requiere_atencion: List[RequiereAtencionItem]
