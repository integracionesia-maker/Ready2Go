"""Firma predeterminada del usuario (perfil) — guardar, leer y borrar.

Una por usuario. Se valida con las mismas reglas que una firma de préstamo
(`media_manager.validar` con un kind de firma: PNG/JPEG por magic bytes, 250 KB,
dimensiones máximas), así que lo que se guarda aquí siempre es aceptable después
como evidencia de un préstamo.

Esta firma NO es evidencia por sí misma: al firmar un préstamo con ella, el
router copia el archivo a un `MediaAsset` del préstamo
(`routers/loans.py::subir_media`). Cambiar o borrar la firma del perfil después
no toca ninguna responsiva ya firmada.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from . import media_manager, tz
from .models import UserSignature

DIRECTORIO = Path("./uploads/firmas_usuario")

# Cualquier kind de firma sirve: comparten límite (250 KB) y validación.
_KIND_VALIDACION = media_manager.KINDS_FIRMA[0]


def obtener(db: Session, user_id: int) -> UserSignature | None:
    return db.query(UserSignature).filter(UserSignature.user_id == user_id).first()


def tiene(db: Session, user_id: int) -> bool:
    return db.query(UserSignature.id).filter(UserSignature.user_id == user_id).first() is not None


def leer_bytes(fila: UserSignature) -> bytes | None:
    """Contenido en disco, o None si el archivo ya no está (respaldo parcial,
    borrado a mano) — el llamador lo trata como "no hay firma guardada"."""
    ruta = Path(fila.file_path)
    return ruta.read_bytes() if ruta.exists() else None


def guardar(db: Session, user_id: int, contenido: bytes) -> UserSignature:
    """Crea o reemplaza la firma del usuario. No hace commit.

    Valida ANTES de tocar disco o base: un archivo inválido no puede dejar al
    usuario sin su firma anterior.
    """
    mime, extension = media_manager.validar(contenido, _KIND_VALIDACION)

    DIRECTORIO.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO / f"{uuid.uuid4().hex}{extension}"
    destino.write_bytes(contenido)

    fila = obtener(db, user_id)
    anterior = fila.file_path if fila else None
    if fila is None:
        fila = UserSignature(user_id=user_id)
        db.add(fila)
    fila.file_path = str(destino.resolve())
    fila.mime_type = mime
    fila.size_bytes = len(contenido)
    fila.sha256 = hashlib.sha256(contenido).hexdigest()
    fila.updated_at = tz.ahora_utc_naive()
    db.flush()

    media_manager.borrar_archivo(anterior)
    return fila


def borrar(db: Session, user_id: int) -> bool:
    """True si había una firma guardada. No hace commit."""
    fila = obtener(db, user_id)
    if fila is None:
        return False
    media_manager.borrar_archivo(fila.file_path)
    db.delete(fila)
    db.flush()
    return True
