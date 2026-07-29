"""Razones sociales (contrato §6).

Dos notas de contrato, ambas reportadas en `docs/avances/servidor.md`:

1. La tabla del contrato dice `POST/PUT | /api/empresas/{id}`. Un POST a un id
   que todavia no existe no tiene sentido, asi que se lee como taquigrafia de
   "los dos verbos de escritura de este recurso": `POST /api/empresas/` crea y
   `PUT /api/empresas/{id}` edita.
2. §0 dice que los listados responden `{items, total}`, pero
   `fixtures/empresas.json` es un arreglo pelado — y `fixtures/equipos.json` si
   trae el sobre. Los fixtures distinguen: el inventario pagina, el catalogo de
   razones sociales no. Se sigue el fixture; un cliente que mockee contra el se
   rompe con el sobre.

`GET` pide solo sesion: el wizard de prestamo necesita la lista para llenar un
`<select>`, y exigir `usuarios:gestionar` ahi dejaria el formulario vacio para
todo el area de marketing.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, crud_empresas, models, schemas_empresas
from ..database import get_db
from ..dependencies import get_current_user
from ..errores import ErrorEquipos, NoEncontrado
from ..rbac import require_perm

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


def _obtener_o_404(db: Session, empresa_id: int) -> models.Empresa:
    empresa = crud_empresas.obtener(db, empresa_id)
    if empresa is None:
        raise NoEncontrado("Razon social no encontrada.")
    return empresa


@router.get("/", response_model=List[schemas_empresas.EmpresaResponse])
def listar_empresas(
    solo_activas: bool = Query(False, description="Excluye las dadas de baja"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud_empresas.listar(db, solo_activas=solo_activas)


@router.post("/", response_model=schemas_empresas.EmpresaResponse, status_code=201)
def crear_empresa(
    data: schemas_empresas.EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    try:
        empresa = crud_empresas.crear(db, data.model_dump())
    except IntegrityError:
        db.rollback()
        raise ErrorEquipos(409, "Ya existe una razon social con ese nombre.", "DUPLICADO")

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="empresa.create",
        target_type="empresa",
        target_id=empresa.id,
        details=empresa.razon_social,
    )
    return empresa


@router.put("/{empresa_id}", response_model=schemas_empresas.EmpresaResponse)
def actualizar_empresa(
    empresa_id: int,
    data: schemas_empresas.EmpresaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    empresa = _obtener_o_404(db, empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return empresa

    try:
        actualizada = crud_empresas.actualizar(db, empresa, cambios)
    except IntegrityError:
        db.rollback()
        raise ErrorEquipos(409, "Ya existe una razon social con ese nombre.", "DUPLICADO")

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="empresa.update",
        target_type="empresa",
        target_id=empresa_id,
    )
    return actualizada
