"""Tablas del modulo Control de Equipos (§4 del plan).

Regla de este archivo: **nunca importa `app.models`**. FKs a `users` por nombre
de tabla en cadena; `models.py` re-exporta este modulo al final para registrar
las tablas en `Base.metadata`.

Las dos invariantes que se sostienen en la base y no en el codigo:

1. `ux_loan_item_equipo_abierto` — un equipo no puede tener dos renglones de
   prestamo abiertos. La maqueta solo lo evitaba filtrando al pintar, asi que dos
   personas pidiendo el mismo equipo a la vez se lo llevaban las dos.
2. `loan.folio UNIQUE` + `folio_counter` — el contador de la maqueta vivia en el
   estado del navegador y colisionaba.

Y la decision estructural que las hace posibles: **no existe
`equipment.estado = 'prestado'`**. La disponibilidad se deriva de los renglones
abiertos (ver `disponibilidad.py`). Guardar el mismo hecho en dos lados es lo que
dejaba equipos prestados para siempre cuando un prestamo fallaba a medias.
"""

from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from .database import Base

__all__ = [
    "EstadoOperativo",
    "CondicionEquipo",
    "EstadoFisico",
    "EstadoPrestamo",
    "DecisionDevolucion",
    "KindMedia",
    "EstadoNotificacion",
    "TipoEvento",
    "ESTADOS_PRESTAMO_ACTIVO",
    "ESTADOS_PRESTAMO_TERMINAL",
    "Equipment",
    "EquipmentAudit",
    "Loan",
    "LoanItem",
    "MediaAsset",
    "ResponsivaDoc",
    "LoanEvent",
    "NotificationLog",
    "Empresa",
    "FolioCounter",
]


def _ahora_utc() -> datetime:
    """UTC sin tzinfo: es lo que ya guarda el resto del proyecto y lo que SQLite
    conserva. La conversion a CDMX se hace al serializar (`app/tz.py`)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Vocabularios ────────────────────────────────────────────────────────────


class EstadoOperativo(str, enum.Enum):
    """Lo unico de la situacion de un equipo que NO se deduce de los prestamos.

    Deliberadamente no hay `prestado`: eso se deriva. Ver `disponibilidad.py`.
    """

    ACTIVO = "activo"
    REVISION = "revision"
    BAJA = "baja"


class CondicionEquipo(str, enum.Enum):
    BUENO = "bueno"
    ATENCION = "atencion"
    DANADO = "danado"


class EstadoFisico(str, enum.Enum):
    NUEVO = "nuevo"
    USADO = "usado"


class EstadoPrestamo(str, enum.Enum):
    BORRADOR = "borrador"
    PRESTADO = "prestado"
    PENDIENTE_CONFIRMACION = "pendiente_confirmacion"
    COMPLETADO = "completado"
    INCOMPLETO = "incompleto"
    CANCELADO = "cancelado"


# Estados en los que el prestamo sigue vivo. `incompleto` cuenta como vivo: tiene
# salida por `cerrar-incidencia` y en la maqueta era terminal, que es como un
# equipo quedaba en revision para siempre.
ESTADOS_PRESTAMO_ACTIVO = (
    EstadoPrestamo.BORRADOR.value,
    EstadoPrestamo.PRESTADO.value,
    EstadoPrestamo.PENDIENTE_CONFIRMACION.value,
    EstadoPrestamo.INCOMPLETO.value,
)

ESTADOS_PRESTAMO_TERMINAL = (
    EstadoPrestamo.COMPLETADO.value,
    EstadoPrestamo.CANCELADO.value,
)


class DecisionDevolucion(str, enum.Enum):
    OK = "ok"
    DANADO = "danado"
    FALTANTE = "faltante"


class KindMedia(str, enum.Enum):
    FOTO_ENTREGA_FRENTE = "foto_entrega_frente"
    FOTO_ENTREGA_ATRAS = "foto_entrega_atras"
    FOTO_DEV_FRENTE = "foto_dev_frente"
    FOTO_DEV_ATRAS = "foto_dev_atras"
    FIRMA_ENTREGA = "firma_entrega"
    FIRMA_RESPONSABLE = "firma_responsable"


class EstadoNotificacion(str, enum.Enum):
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    FALLIDO = "fallido"


class TipoEvento(str, enum.Enum):
    """Bitacora del prestamo. Reemplaza el `loan.log` de la maqueta."""

    CREADO = "creado"
    ITEM_AGREGADO = "item_agregado"
    ITEM_QUITADO = "item_quitado"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    DEVOLUCION_REGISTRADA = "devolucion_registrada"
    ENTREGA_AUTORIZADA = "entrega_autorizada"
    DEVOLUCION_CONFIRMADA = "devolucion_confirmada"
    INCIDENCIA_CERRADA = "incidencia_cerrada"
    RESPONSIVA_GENERADA = "responsiva_generada"
    FIRMA_COMPLETADA = "firma_completada"


# ── Inventario ──────────────────────────────────────────────────────────────


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # UNIQUE con NULL permitido: SQLite acepta varios NULL. La mayoria del
    # inventario real no trae codigo (ver fixtures/equipos.json).
    codigo = Column(String(50), unique=True, nullable=True)
    nombre = Column(String(255), nullable=False)
    categoria = Column(String(120), nullable=True)
    descripcion = Column(Text, nullable=True)
    marca = Column(String(120), nullable=True)
    modelo = Column(String(120), nullable=True)
    numero_serie = Column(String(120), nullable=True)
    activo_fijo = Column(String(120), nullable=True)
    cuenta_gmail = Column(String(255), nullable=True)
    espacio_disponible = Column(String(120), nullable=True)

    estado_operativo = Column(
        String(20), nullable=False, default=EstadoOperativo.ACTIVO.value
    )
    accesorios_tipicos = Column(Text, nullable=True)  # JSON array
    fotos_originales_url = Column(String(512), nullable=True)

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=_ahora_utc)
    updated_at = Column(DateTime, nullable=False, default=_ahora_utc, onupdate=_ahora_utc)

    auditorias = relationship(
        "EquipmentAudit",
        back_populates="equipo",
        cascade="all, delete-orphan",
        order_by="desc(EquipmentAudit.id)",
    )
    items = relationship("LoanItem", back_populates="equipo")

    __table_args__ = (
        Index("ix_equipment_estado_operativo", "estado_operativo"),
        Index("ix_equipment_categoria", "categoria"),
    )


class EquipmentAudit(Base):
    """Historial de condicion. La maqueta guardaba solo la ultima revision, asi
    que no habia forma de saber si un rayon venia de antes del prestamo."""

    __tablename__ = "equipment_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    condicion = Column(String(20), nullable=False, default=CondicionEquipo.BUENO.value)
    estado_fisico = Column(String(20), nullable=True)
    espacio_disponible = Column(String(120), nullable=True)
    comentario = Column(Text, nullable=True)
    # Fecha de la revision fisica. NULL = el equipo se dio de alta sin auditar
    # todavia (los dos iPhone nuevos del inventario real).
    fecha = Column(Date, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=_ahora_utc)

    equipo = relationship("Equipment", back_populates="auditorias")

    __table_args__ = (Index("ix_equipment_audit_equipment", "equipment_id"),)


# ── Prestamos ───────────────────────────────────────────────────────────────


class Loan(Base):
    __tablename__ = "loan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # NULL mientras es borrador: el folio se asigna al confirmar, para no quemar
    # numeros en borradores abandonados.
    folio = Column(String(20), unique=True, nullable=True)

    responsable_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Se copian nombre y correo al crear: si el usuario se da de baja, la
    # responsiva ya firmada tiene que seguir diciendo quien la firmo.
    responsable_nombre = Column(String(150), nullable=False)
    responsable_email = Column(String(255), nullable=True)

    area = Column(String(120), nullable=True)
    empresa = Column(String(255), nullable=True)
    motivo = Column(Text, nullable=True)
    notas_responsiva = Column(Text, nullable=True)

    entregado_por_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    fecha_entrega = Column(Date, nullable=True)
    fecha_regreso_esperada = Column(Date, nullable=True)
    fecha_regreso_real = Column(Date, nullable=True)

    estado = Column(String(30), nullable=False, default=EstadoPrestamo.BORRADOR.value)

    # Ortogonal al estado (§4.3): Melisa puede autorizar antes o despues de que
    # el equipo vuelva. Son dos insignias distintas, no una. Pero bloquea el
    # cierre: sin autorizacion no se llega a `completado`.
    entrega_autorizada = Column(Boolean, nullable=False, default=False)
    entrega_autorizada_por_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    fecha_autorizacion_entrega = Column(DateTime, nullable=True)

    confirmada_por_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    fecha_confirmacion = Column(DateTime, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=_ahora_utc)
    updated_at = Column(DateTime, nullable=False, default=_ahora_utc, onupdate=_ahora_utc)

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    items = relationship(
        "LoanItem", back_populates="loan", cascade="all, delete-orphan", order_by="LoanItem.id"
    )
    eventos = relationship(
        "LoanEvent", back_populates="loan", cascade="all, delete-orphan", order_by="LoanEvent.id"
    )
    media = relationship("MediaAsset", back_populates="loan", cascade="all, delete-orphan")
    responsivas = relationship(
        "ResponsivaDoc",
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="desc(ResponsivaDoc.version)",
    )

    responsable = relationship("User", foreign_keys=[responsable_user_id])
    entregado_por = relationship("User", foreign_keys=[entregado_por_user_id])
    autorizada_por = relationship("User", foreign_keys=[entrega_autorizada_por_user_id])
    confirmada_por = relationship("User", foreign_keys=[confirmada_por_user_id])

    __table_args__ = (
        Index("ix_loan_estado", "estado"),
        Index("ix_loan_responsable", "responsable_user_id"),
        Index("ix_loan_fecha_regreso", "fecha_regreso_esperada"),
    )


class LoanItem(Base):
    """Un equipo dentro de un prestamo.

    `devuelto_at IS NULL` significa **renglon abierto**: ese equipo esta fuera.
    Es la unica fuente de verdad de la disponibilidad, y por eso lleva indice
    unico parcial.

    Consecuencia operativa que hay que respetar en toda la API: cualquier
    operacion que libere el equipo (cancelar, confirmar devolucion, borrar el
    prestamo) **tiene que escribir `devuelto_at`**. Si no, el indice bloquea el
    equipo mientras la formula de disponibilidad lo muestra libre, y el usuario
    ve un equipo disponible que da 409 al pedirlo.
    """

    __tablename__ = "loan_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(Integer, ForeignKey("loan.id", ondelete="CASCADE"), nullable=False)
    # RESTRICT: un equipo con historial no se borra fisicamente. Romperia la
    # responsiva ya firmada, que es evidencia.
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False)

    accesorios_seleccionados = Column(Text, nullable=True)  # JSON array
    accesorios_otros = Column(Text, nullable=True)
    cargador_con = Column(String(30), nullable=True)  # responsable | resguardo | sin_cargador

    devuelto_at = Column(DateTime, nullable=True)
    no_devuelto = Column(Boolean, nullable=False, default=False)
    nota_devolucion = Column(Text, nullable=True)

    decision = Column(String(20), nullable=True)  # ok | danado | faltante
    nota_decision = Column(Text, nullable=True)

    loan = relationship("Loan", back_populates="items")
    equipo = relationship("Equipment", back_populates="items")
    media = relationship("MediaAsset", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("loan_id", "equipment_id", name="ux_loan_item_loan_equipo"),
        # LA invariante del modulo. Sin esto, dos personas pidiendo el mismo
        # equipo al mismo tiempo se lo llevan las dos: la carrera se pierde en
        # el hueco entre validar y guardar.
        Index(
            "ux_loan_item_equipo_abierto",
            "equipment_id",
            unique=True,
            sqlite_where=text("devuelto_at IS NULL"),
        ),
        Index("ix_loan_item_loan", "loan_id"),
    )


class MediaAsset(Base):
    """Fotos y firmas. En disco con sha256, nunca base64 en la base.

    La maqueta guardaba dataURL dentro del JSON de localStorage: con 2 fotos por
    equipo en entrega y otras 2 en devolucion, la cuota de 5 MB se agotaba en
    decenas de prestamos.
    """

    __tablename__ = "media_asset"

    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(Integer, ForeignKey("loan.id", ondelete="CASCADE"), nullable=True)
    loan_item_id = Column(Integer, ForeignKey("loan_item.id", ondelete="CASCADE"), nullable=True)

    kind = Column(String(30), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=_ahora_utc)

    loan = relationship("Loan", back_populates="media")
    item = relationship("LoanItem", back_populates="media")

    __table_args__ = (
        Index("ix_media_asset_loan", "loan_id"),
        Index("ix_media_asset_item_kind", "loan_item_id", "kind"),
    )


class ResponsivaDoc(Base):
    """Carta responsiva en PDF, versionada. **Nunca se sobrescribe.**

    Un documento firmado es evidencia: regenerarlo encima destruye el rastro.
    Regenerar crea `version + 1` con su motivo.
    """

    __tablename__ = "responsiva_doc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(Integer, ForeignKey("loan.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    file_path = Column(String(512), nullable=False)
    sha256 = Column(String(64), nullable=True)
    generated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at = Column(DateTime, nullable=False, default=_ahora_utc)
    motivo_regeneracion = Column(Text, nullable=True)

    loan = relationship("Loan", back_populates="responsivas")

    __table_args__ = (
        UniqueConstraint("loan_id", "version", name="ux_responsiva_loan_version"),
    )


class LoanEvent(Base):
    __tablename__ = "loan_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(Integer, ForeignKey("loan.id", ondelete="CASCADE"), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Se copia el nombre del actor: la bitacora tiene que seguir legible si el
    # usuario se da de baja.
    actor_nombre = Column(String(150), nullable=True)
    tipo = Column(String(40), nullable=False)
    detalle = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_ahora_utc)

    loan = relationship("Loan", back_populates="eventos")

    __table_args__ = (Index("ix_loan_event_loan", "loan_id"),)


class NotificationLog(Base):
    """Registro de correos. El UNIQUE es la idempotencia: reintentar un envio no
    duplica el aviso a la aprobadora."""

    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(Integer, ForeignKey("loan.id", ondelete="CASCADE"), nullable=True)
    canal = Column(String(20), nullable=False, default="email")
    destinatario = Column(String(255), nullable=False)
    asunto = Column(String(255), nullable=True)
    tipo = Column(String(50), nullable=False)
    estado = Column(String(20), nullable=False, default=EstadoNotificacion.PENDIENTE.value)
    intentos = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_ahora_utc)
    sent_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("loan_id", "tipo", "destinatario", name="ux_notificacion_idempotente"),
        Index("ix_notification_log_estado", "estado"),
    )


# ── Catalogos ───────────────────────────────────────────────────────────────


class Empresa(Base):
    """Razones sociales. La emisora de la carta responsiva sale de aqui,
    **jamas hardcode en el PDF** (§10.21 del plan: la maqueta las tenia en un
    `<select>` del JS)."""

    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    razon_social = Column(String(255), unique=True, nullable=False)
    direccion = Column(String(255), nullable=True)
    ciudad = Column(String(120), nullable=True)
    rfc = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class FolioCounter(Base):
    """Contador de folios por prefijo. En la maqueta vivia en el estado del
    navegador, asi que dos pestañas producian el mismo folio."""

    __tablename__ = "folio_counter"

    scope = Column(String(10), primary_key=True)  # 'CE'
    last_value = Column(Integer, nullable=False, default=0)
