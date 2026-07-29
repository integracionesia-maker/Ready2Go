"""Schemas de prestamos (contrato §3 y §4).

`LoanDetail` es el criterio de aceptacion del payload: su copia literal esta en
`docs/contratos/fixtures/prestamo_demo.json` y hay una prueba de igualdad de cada
lado. **No se le agregan campos.** Aunque la tabla tenga `created_at`,
`created_by_user_id` o `is_deleted`, el fixture es cerrado: sumar una clave rompe
la guardia de los dos lados a la vez.

Los `datetime` viajan como cadena ya formateada (ISO-8601 con offset de CDMX,
sin microsegundos) en vez de como `datetime`: el serializador de Pydantic emitiria
`+00:00` o microsegundos y ninguna de las dos cosas cuadra con el fixture.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PersonaRef(BaseModel):
    user_id: Optional[int] = None
    nombre: Optional[str] = None


class ResponsableRef(PersonaRef):
    """El unico que lleva correo: es a quien se le manda su copia del PDF."""

    email: Optional[str] = None


class ResponsivaRef(BaseModel):
    version: int
    url: str


class LoanItemDetail(BaseModel):
    id: int
    equipment_id: int
    equipo_nombre: Optional[str] = None
    accesorios_seleccionados: List[str] = []
    accesorios_otros: Optional[str] = None
    cargador_con: Optional[str] = None
    devuelto_at: Optional[str] = None
    no_devuelto: bool = False
    nota_devolucion: Optional[str] = None
    decision: Optional[str] = None
    nota_decision: Optional[str] = None
    # Ids, nunca URLs ni base64. Se leen por GET /api/media/{id}.
    media: Dict[str, Optional[int]] = {}


class LoanEventDetail(BaseModel):
    id: int
    tipo: str
    actor: Optional[str] = None
    detalle: Optional[str] = None
    created_at: Optional[str] = None


class LoanDetail(BaseModel):
    id: int
    folio: Optional[str] = None
    estado: str
    responsable: ResponsableRef
    area: Optional[str] = None
    empresa: Optional[str] = None
    motivo: Optional[str] = None
    notas_responsiva: Optional[str] = None
    entregado_por: Optional[PersonaRef] = None
    fecha_entrega: Optional[date] = None
    fecha_regreso_esperada: Optional[date] = None
    fecha_regreso_real: Optional[date] = None
    atrasado: bool = False
    dias_atraso: int = 0
    entrega_autorizada: bool = False
    entrega_autorizada_por: Optional[PersonaRef] = None
    fecha_autorizacion_entrega: Optional[str] = None
    confirmada_por: Optional[PersonaRef] = None
    fecha_confirmacion: Optional[str] = None
    items: List[LoanItemDetail] = []
    firmas: Dict[str, Optional[int]] = {}
    responsiva: Optional[ResponsivaRef] = None
    eventos: List[LoanEventDetail] = []


class LoanRow(BaseModel):
    """Fila del listado.

    El contrato define la ficha pero **nunca** la fila del listado: es el hueco
    mas grande del §3. Esta forma sigue la disciplina del §2 de inventario —traer
    en la fila lo que la tabla pinta, para no pedir un detalle por renglon— y esta
    reportada en `docs/avances/servidor.md` para que el cliente la confirme.
    """

    id: int
    folio: Optional[str] = None
    estado: str
    responsable: ResponsableRef
    area: Optional[str] = None
    empresa: Optional[str] = None
    motivo: Optional[str] = None
    fecha_entrega: Optional[date] = None
    fecha_regreso_esperada: Optional[date] = None
    fecha_regreso_real: Optional[date] = None
    atrasado: bool = False
    dias_atraso: int = 0
    entrega_autorizada: bool = False
    total_equipos: int = 0
    equipos: List[str] = []


class LoanListResponse(BaseModel):
    items: List[LoanRow]
    total: int


# ── Entradas ────────────────────────────────────────────────────────────────


class LoanCreate(BaseModel):
    """Todo opcional: el borrador se crea al abrir el formulario, antes de que
    la persona haya escrito nada. Si no se manda responsable, el servidor pone
    al usuario de la sesion."""

    responsable_user_id: Optional[int] = None
    responsable_nombre: Optional[str] = Field(None, max_length=150)
    responsable_email: Optional[str] = Field(None, max_length=255)
    area: Optional[str] = Field(None, max_length=120)
    empresa: Optional[str] = Field(None, max_length=255)
    motivo: Optional[str] = None
    notas_responsiva: Optional[str] = None
    fecha_entrega: Optional[date] = None
    fecha_regreso_esperada: Optional[date] = None


class LoanUpdate(BaseModel):
    responsable_user_id: Optional[int] = None
    responsable_nombre: Optional[str] = Field(None, max_length=150)
    responsable_email: Optional[str] = Field(None, max_length=255)
    area: Optional[str] = Field(None, max_length=120)
    empresa: Optional[str] = Field(None, max_length=255)
    motivo: Optional[str] = None
    notas_responsiva: Optional[str] = None
    fecha_entrega: Optional[date] = None
    fecha_regreso_esperada: Optional[date] = None


class LoanItemCreate(BaseModel):
    equipment_id: int = Field(..., gt=0)
    accesorios_seleccionados: List[str] = []
    accesorios_otros: Optional[str] = None
    cargador_con: Optional[str] = Field(None, max_length=30)


class CancelarRequest(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)


class DevolucionItem(BaseModel):
    loan_item_id: int
    no_devuelto: bool = False
    nota_devolucion: Optional[str] = None


class DevolucionRequest(BaseModel):
    """El contrato fija la regla (2 fotos por equipo o `no_devuelto` con nota)
    pero no la forma del cuerpo. Esta sigue el estilo de `/confirmar-devolucion`
    del §4, que si esta congelado. Reportado como hueco."""

    fecha_regreso_real: Optional[date] = None
    items: List[DevolucionItem] = []


class DecisionItem(BaseModel):
    loan_item_id: int
    decision: str = Field(..., description="ok | danado | faltante")
    nota: Optional[str] = None


class ConfirmarDevolucionRequest(BaseModel):
    decisiones: List[DecisionItem]


class CerrarIncidenciaRequest(BaseModel):
    nota: str = Field(..., min_length=1)


class MediaResponse(BaseModel):
    """Tres claves, exactamente las del contrato §5. No se devuelve `file_path`
    ni `url`: no exponer la ruta de disco es parte de la mitigacion del IDOR."""

    id: int
    kind: str
    sha256: str
