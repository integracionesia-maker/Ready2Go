"""Gestión de usuarios (sección Administración): exclusiva de superadmin.

Cambio R4 (doc/prompt-mejoras-integrales.md): antes un admin podía gestionar
usuarios de rol 'creador'; ahora TODA la gestión de usuarios es exclusiva del
superadmin. El rol/estado del propio superadmin sigue siendo inmutable por API.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, models, schemas, security
from ..database import get_db
from ..rbac import require_perm

router = APIRouter(prefix="/api/users", tags=["users"])

VALID_ROLES = {r.value for r in models.UserRole}


def _ensure_assignable_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Rol inválido: '{role}'.")
    if role == models.UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=400, detail="El rol 'superadmin' no se puede crear ni asignar por API."
        )


def _ensure_not_superadmin_target(target: models.User) -> None:
    if target.role == models.UserRole.SUPERADMIN.value:
        raise HTTPException(status_code=403, detail="La cuenta superadmin no se puede modificar por API.")


def _get_target_or_404(db: Session, user_id: int) -> models.User:
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


@router.get("/", response_model=List[schemas.UserResponse])
def list_users(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    return crud.list_users(db, role=role)


@router.post("/", response_model=schemas.UserResponse, status_code=201)
def create_user(
    data: schemas.UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    _ensure_assignable_role(data.role)

    if data.role == models.UserRole.CREADOR.value:
        if not data.creator_id:
            raise HTTPException(
                status_code=400,
                detail="Debes vincular un creador para un usuario de rol 'creador'.",
            )
        if not crud.get_creator(db, data.creator_id):
            raise HTTPException(status_code=404, detail="Creador no encontrado.")
    elif data.creator_id:
        raise HTTPException(
            status_code=400,
            detail="Solo los usuarios de rol 'creador' pueden vincularse a un creador.",
        )

    if data.password:
        error = security.validate_password_strength(data.password, data.username)
        if error:
            raise HTTPException(status_code=400, detail=error)
        password = data.password
    else:
        password = security.generate_temp_password()

    try:
        user = crud.create_user(
            db,
            username=data.username,
            email=data.email,
            password_hash=security.hash_password(password),
            full_name=data.full_name,
            role=data.role,
            creator_id=data.creator_id,
            must_change_password=True,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un usuario con ese nombre de usuario, correo, o el creador ya tiene un usuario vinculado.",
        )

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="user.create",
        target_type="user",
        target_id=user.id,
        details=f"role={user.role}",
    )
    return user


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    return _get_target_or_404(db, user_id)


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    data: schemas.UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    target = _get_target_or_404(db, user_id)
    _ensure_not_superadmin_target(target)

    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("role") is not None:
        _ensure_assignable_role(update_data["role"])

    if update_data.get("creator_id") is not None:
        if not crud.get_creator(db, update_data["creator_id"]):
            raise HTTPException(status_code=404, detail="Creador no encontrado.")

    if update_data.get("email"):
        existing = crud.get_user_by_email(db, update_data["email"])
        if existing and existing.id != target.id:
            raise HTTPException(status_code=409, detail="Ese correo ya está en uso.")

    try:
        updated = crud.update_user_admin(db, target, update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese creador ya tiene un usuario vinculado.")

    crud.log_audit(
        db, actor_user_id=current_user.id, action="user.update", target_type="user", target_id=target.id,
    )
    return updated


@router.post("/{user_id}/reset-password", response_model=schemas.ResetPasswordResponse)
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    target = _get_target_or_404(db, user_id)
    _ensure_not_superadmin_target(target)

    temp_password = security.generate_temp_password()
    crud.set_user_password(db, target, security.hash_password(temp_password), must_change_password=True)
    crud.revoke_all_refresh_tokens_for_user(db, target.id)

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="password.reset_by_admin",
        target_type="user",
        target_id=target.id,
    )
    return schemas.ResetPasswordResponse(temporary_password=temp_password)


@router.patch("/{user_id}/estado", response_model=schemas.UserResponse)
def set_user_estado(
    user_id: int,
    data: schemas.SetUserActiveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    target = _get_target_or_404(db, user_id)
    _ensure_not_superadmin_target(target)

    updated = crud.set_user_active(db, target, data.is_active)
    if not data.is_active:
        crud.revoke_all_refresh_tokens_for_user(db, target.id)

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="user.activate" if data.is_active else "user.deactivate",
        target_type="user",
        target_id=target.id,
    )
    return updated
