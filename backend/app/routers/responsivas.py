"""Descarga de la carta responsiva (contrato §3).

Router propio bajo el mismo prefijo `/api/loans` que `loans.py`, como pide el
reparto: FastAPI lo acepta y asi el PDF no obliga a tocar el archivo de
prestamos.

Autorizacion: participante o `equipos_prestamos:ver_global`, igual que la ficha.
**Nunca mount estatico** — es el recurso mas sensible del modulo: la carta trae
nombre, area, numero de serie y las dos firmas.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..errores import NoEncontrado
from ..models_equipos import ResponsivaDoc
from ..rbac import require_cualquiera
from .loans import VER_GLOBAL, VER_PROPIOS, _prestamo_visible

router = APIRouter(prefix="/api/loans", tags=["loans"])


@router.get("/{loan_id:int}/responsiva.pdf")
def descargar_responsiva(
    loan_id: int,
    request: Request,
    version: Optional[int] = Query(
        None,
        ge=1,
        description="Version historica. Sin el parametro se sirve la ultima.",
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cualquiera(VER_PROPIOS, VER_GLOBAL)),
):
    """Ultima version por defecto; `?version=n` para una historica.

    El parametro esta en el plan §5 pero **no** en el contrato congelado. Se
    implementa porque es puramente aditivo —no cambia la forma de ningun
    payload y el default sigue siendo la ultima version— y porque sin el, el
    versionado que la base ya sostiene no tiene forma de consultarse. Reportado
    para que entre al contrato v2 junto con la forma de enumerar versiones.
    """
    prestamo = _prestamo_visible(request, db, current_user, loan_id)

    consulta = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == prestamo.id)
    if version is not None:
        consulta = consulta.filter(ResponsivaDoc.version == version)
    documento = consulta.order_by(ResponsivaDoc.version.desc()).first()

    if documento is None:
        # Un borrador o un cancelado no tienen responsiva. Se responde igual que
        # un recurso inexistente: el contrato §0 no distingue los dos casos.
        raise NoEncontrado("Este prestamo no tiene carta responsiva.")

    ruta = Path(documento.file_path)
    if not ruta.exists():
        raise NoEncontrado("El archivo de la carta responsiva ya no esta en disco.")

    nombre = f"{prestamo.folio or prestamo.id}_v{documento.version}.pdf"
    return Response(
        content=ruta.read_bytes(),
        media_type="application/pdf",
        headers={
            # `inline` con filename: se puede previsualizar en el navegador y al
            # guardarla conserva un nombre con folio y version. `attachment`
            # forzaria descarga y rompe la vista previa del wizard.
            "Content-Disposition": f'inline; filename="{nombre}"',
            "Cache-Control": "private, max-age=0, must-revalidate",
            "ETag": f'"{documento.sha256 or documento.id}"',
        },
    )
