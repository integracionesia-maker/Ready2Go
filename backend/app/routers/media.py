"""Descarga de fotos y firmas (contrato §5).

**Nunca hay mount estatico.** Todo byte sale por aqui, con sesion y autorizacion
por participacion. Un `StaticFiles` sirve por ruta de disco sin consultar la
fila: quien reciba o adivine la URL descarga la foto del prestamo de otro. Ya
paso en este repo con `tickets/file/{id}` y por eso se elimino el mount de
`/uploads` (§10.3, CRITICO).

`?tamano=thumb` exige exactamente el mismo permiso que el original: la miniatura
no es un atajo sin autorizacion.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from .. import crud_loans, media_manager, models, rbac
from ..database import get_db
from ..dependencies import get_current_user
from ..errores import ErrorEquipos, NoEncontrado, SinPermiso
from ..models_equipos import LoanItem, MediaAsset
from ..rbac import permisos_del_request

router = APIRouter(prefix="/api/media", tags=["media"])

TAMANO_THUMB = "thumb"


@router.get("/{media_id:int}")
def descargar_media(
    media_id: int,
    request: Request,
    tamano: Optional[str] = Query(None, description="Omitir para el original; 'thumb' para 96px"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    fila = db.get(MediaAsset, media_id)
    if fila is None:
        raise NoEncontrado("Archivo no encontrado.")

    # El prestamo se resuelve por media_asset.loan_id; si llegara nulo en una
    # foto, se cae al loan_id del renglon. Nunca se autoriza contra el renglon
    # suelto: la autorizacion es del prestamo.
    loan_id = fila.loan_id
    if loan_id is None and fila.loan_item_id is not None:
        item = db.get(LoanItem, fila.loan_item_id)
        loan_id = item.loan_id if item else None

    prestamo = crud_loans.obtener(db, loan_id) if loan_id else None
    if prestamo is None:
        # Existir borrado y no existir se responden igual, para no filtrar que
        # el registro esta ahi.
        raise NoEncontrado("Archivo no encontrado.")

    permisos = permisos_del_request(request, db, current_user)
    ver_global = rbac.tiene_permiso(permisos, "equipos_prestamos", "ver_global")
    if not crud_loans.puede_ver(prestamo, current_user.id, ver_global):
        raise SinPermiso()

    if tamano is not None and tamano != TAMANO_THUMB:
        # Ignorarlo en silencio haria que un typo del cliente baje 3 MB para
        # pintar 96 px, y nadie se enteraria.
        raise ErrorEquipos(
            422, f"tamano invalido: '{tamano}'. Unico valor aceptado: '{TAMANO_THUMB}'.",
            "VALOR_INVALIDO",
        )

    ruta = Path(fila.file_path)
    if not ruta.exists():
        raise NoEncontrado("El archivo ya no esta en disco.")

    if tamano == TAMANO_THUMB:
        contenido, mime = media_manager.miniatura(str(ruta), fila.mime_type)
    else:
        contenido, mime = ruta.read_bytes(), fila.mime_type

    # `private`: un cache compartido o un proxy que guardara la respuesta
    # recrearia el IDOR justo debajo del endpoint que lo cierra.
    # `ETag` sobre el sha256 que ya esta en la fila: la revalidacion cuesta un
    # 304 en vez de volver a mandar 3 MB.
    # Sin `filename=`: se sirve inline para poder pintarlo en un <img>, no como
    # descarga forzada.
    return Response(
        content=contenido,
        media_type=mime,
        headers={
            "Cache-Control": "private, max-age=0, must-revalidate",
            "ETag": f'"{fila.sha256}{"-thumb" if tamano == TAMANO_THUMB else ""}"',
        },
    )
