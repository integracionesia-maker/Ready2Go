"""File-upload utilities: validation, unique naming, and disk persistence."""

import os
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile, HTTPException

UPLOAD_DIR = Path("./uploads/tickets")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/jpg", "application/pdf",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_file(file: UploadFile) -> Tuple[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre.")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido: '{ext}'. Solo: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo MIME no permitido: '{mime}'.")
    return ext, mime


def save_upload(file: UploadFile) -> Tuple[str, str, str]:
    ext, mime = validate_file(file)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / unique_name
    try:
        contents = file.file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE // (1024 * 1024)} MB.",
            )
        dest_path.write_bytes(contents)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo: {exc}")
    return unique_name, str(dest_path.resolve()), mime


def delete_upload(file_path: str) -> None:
    try:
        os.remove(file_path)
    except OSError:
        pass
