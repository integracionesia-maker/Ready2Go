"""Firma predeterminada del usuario (sección "Mi firma" del Perfil).

Solo el dueño la ve, la guarda y la borra: no hay forma de leer la firma de
otro usuario por aquí, ni siquiera siendo superadmin (no hay `{user_id}` en la
ruta). Cualquier usuario autenticado puede tener una, independientemente de
sus permisos de Equipos.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import crud, models, schemas, user_signature
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/auth/me/signature", tags=["auth"])


@router.get("")
def ver_mi_firma(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fila = user_signature.obtener(db, current_user.id)
    contenido = user_signature.leer_bytes(fila) if fila else None
    if contenido is None:
        raise HTTPException(status_code=404, detail="No tienes una firma guardada.")
    # `private` + ETag sobre el sha256: mismo criterio que /api/media — ningún
    # caché compartido guarda la firma de alguien, y re-validar cuesta un 304.
    return Response(
        content=contenido,
        media_type=fila.mime_type,
        headers={
            "Cache-Control": "private, max-age=0, must-revalidate",
            "ETag": f'"{fila.sha256}"',
        },
    )


@router.put("", response_model=schemas.MessageResponse)
async def guardar_mi_firma(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contenido = await file.read()
    # `validar` decodifica con PIL: bloqueante, al threadpool (igual que /media).
    fila = await run_in_threadpool(user_signature.guardar, db, current_user.id, contenido)
    db.commit()
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="user.signature_saved",
        target_type="user",
        target_id=current_user.id,
        details=fila.sha256,
    )
    return schemas.MessageResponse(message="Firma guardada.")


@router.delete("", response_model=schemas.MessageResponse)
def borrar_mi_firma(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user_signature.borrar(db, current_user.id):
        raise HTTPException(status_code=404, detail="No tienes una firma guardada.")
    db.commit()
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="user.signature_deleted",
        target_type="user",
        target_id=current_user.id,
    )
    return schemas.MessageResponse(message="Firma eliminada.")
