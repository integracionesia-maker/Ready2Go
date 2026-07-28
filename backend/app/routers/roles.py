"""Catalogo de paquetes de permisos.

Contrato v1 §7 congela **solo** `GET /api/roles/`. La tarea del reparto pedia
"CRUD de paquetes"; el contrato no tiene POST, PUT ni DELETE para este recurso,
asi que aqui va nada mas la lectura. Inventar los otros tres verbos seria salirse
del contrato de un solo lado, que es el modo tipico de falla de este reparto.
Reportado en `docs/avances/servidor.md` y `docs/backlog_servidor.md`.

De donde sale la lista: de la tabla `roles` si esta sembrada, y del catalogo en
codigo si no. Un catalogo vacio en pantalla se leeria como "no hay paquetes"
cuando lo que pasa es que falta correr la migracion.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud_rbac, models, rbac_catalog, schemas_rbac
from ..database import get_db
from ..rbac import require_perm

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("/", response_model=List[schemas_rbac.RolResponse])
def listar_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar_roles")),
):
    filas = crud_rbac.listar_roles(db)
    activos = {fila.name: fila.is_active for fila in filas}

    # Orden estable: piso, base, aditivo; alfabetico dentro de cada grupo.
    orden_kind = {
        rbac_catalog.KIND_PISO: 0,
        rbac_catalog.KIND_BASE: 1,
        rbac_catalog.KIND_ADITIVO: 2,
    }
    nombres = sorted(
        rbac_catalog.PAQUETES,
        key=lambda n: (orden_kind.get(rbac_catalog.kind_de(n), 9), n),
    )

    return [
        schemas_rbac.RolResponse(
            name=nombre,
            kind=rbac_catalog.kind_de(nombre),
            descripcion=rbac_catalog.descripcion_de(nombre),
            is_active=activos.get(nombre, True),
            permisos=rbac_catalog.a_json(rbac_catalog.permisos_de_paquete(nombre)),
        )
        for nombre in nombres
    ]
