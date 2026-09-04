"""Concesion y revocacion de paquetes aditivos por usuario (contrato v1 §7).

Comparte el prefijo `/api/users` con `routers/users.py` sin editarlo: FastAPI
resuelve por ruta completa y `/{user_id}/roles` no choca con `/{user_id}`.

Que se puede conceder: **solo paquetes de kind `aditivo`**. El rol base vive en
`users.role` y se cambia por `PUT /api/users/{id}`, que no es de este carril. Un
aditivo se suma al rol base; jamas lo reemplaza.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, crud_rbac, models, rbac_catalog, schemas, schemas_rbac
from ..database import get_db
from ..errores import NoEncontrado, SinPermiso
from ..rbac import permisos_efectivos, require_perm

router = APIRouter(prefix="/api/users", tags=["roles"])


def _usuario_objetivo(db: Session, user_id: int) -> models.User:
    user = crud.get_user(db, user_id)
    if not user:
        raise NoEncontrado("Usuario no encontrado.")
    return user


def _paquete_aditivo(role_name: str) -> str:
    """404 tanto si el paquete no existe como si existe pero no es aditivo:
    desde este endpoint la coleccion asignable son los aditivos, y `admin` no es
    miembro de esa coleccion.

    Hueco de contrato: v1 no define codigo para "paquete no asignable". Se reusa
    `NO_ENCONTRADO` en vez de inventar uno. Reportado en docs/backlog_servidor.md.
    """
    if rbac_catalog.kind_de(role_name) != rbac_catalog.KIND_ADITIVO:
        raise NoEncontrado(f"No existe un paquete aditivo llamado '{role_name}'.")
    return role_name


def _bloquear_superadmin(target: models.User) -> None:
    if target.role == models.UserRole.SUPERADMIN.value:
        raise SinPermiso("La cuenta superadmin no se modifica por API.")


def _a_grant_response(grant) -> schemas_rbac.GrantResponse:
    return schemas_rbac.GrantResponse(
        user_id=grant.user_id,
        role_name=grant.role_name,
        kind=rbac_catalog.kind_de(grant.role_name) or "",
        descripcion=rbac_catalog.descripcion_de(grant.role_name),
        granted_by=grant.granted_by,
        granted_at=grant.granted_at,
        singleton=rbac_catalog.es_singleton(grant.role_name),
    )


@router.get("/{user_id}/roles", response_model=schemas_rbac.UserRolesResponse)
def listar_roles_de_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar_roles")),
):
    target = _usuario_objetivo(db, user_id)
    grants = crud_rbac.listar_grants(db, target.id)
    return schemas_rbac.UserRolesResponse(
        user_id=target.id,
        role_base=target.role,
        aditivos=[_a_grant_response(g) for g in grants],
        permisos_efectivos=rbac_catalog.a_json(permisos_efectivos(db, target)),
    )


@router.post("/{user_id}/roles", response_model=schemas_rbac.UserRolesResponse, status_code=201)
def conceder_rol(
    user_id: int,
    data: schemas_rbac.ConcederRolRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar_roles")),
):
    target = _usuario_objetivo(db, user_id)
    _bloquear_superadmin(target)
    role_name = _paquete_aditivo(data.role_name)

    # El paquete tiene que estar sembrado: la FK de user_role_grants apunta a
    # roles.name. Si la migracion no corrio, esto lo dice claro en vez de
    # reventar con un IntegrityError sin contexto.
    if crud_rbac.obtener_rol(db, role_name) is None:
        raise NoEncontrado(
            f"El paquete '{role_name}' no esta sembrado en la base. Corre migrate_rbac_aditivo.py."
        )

    # Capturado ANTES de conceder: si el paquete es singleton, `conceder()` ya
    # habra revocado a este anterior titular (si habia uno) para cuando se
    # arma el detalle de la bitacora — sin capturarlo antes, el desplazamiento
    # quedaria mudo en el rastro.
    anterior_titular = (
        crud_rbac.titular_de(db, role_name)
        if rbac_catalog.es_singleton(role_name)
        else None
    )

    crud_rbac.conceder(db, target.id, role_name, current_user.id)

    detalle = f"role_name={role_name}"
    if anterior_titular and anterior_titular.id != target.id:
        detalle += f"; paquete singleton, revocado automaticamente de user_id={anterior_titular.id}"
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="rbac.grant",
        target_type="user",
        target_id=target.id,
        details=detalle,
    )
    return listar_roles_de_usuario(target.id, db=db, current_user=current_user)


@router.delete("/{user_id}/roles/{role_name}", response_model=schemas.MessageResponse)
def revocar_rol(
    user_id: int,
    role_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar_roles")),
):
    target = _usuario_objetivo(db, user_id)
    _bloquear_superadmin(target)

    if not crud_rbac.revocar(db, target.id, role_name):
        raise NoEncontrado(f"El usuario no tiene concedido el paquete '{role_name}'.")

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="rbac.revoke",
        target_type="user",
        target_id=target.id,
        details=f"role_name={role_name}",
    )
    return schemas.MessageResponse(message=f"Paquete '{role_name}' revocado.")


__all__ = ["router"]
