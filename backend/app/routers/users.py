"""Gestión de usuarios (sección Administración): exclusiva de superadmin.

Cambio R4 (doc/prompt-mejoras-integrales.md): antes un admin podía gestionar
usuarios de rol 'creador'; ahora TODA la gestión de usuarios es exclusiva del
superadmin. El rol/estado del propio superadmin sigue siendo inmutable por API;
su CONTRASEÑA solo puede resetearla otro superadmin
(POST /{user_id}/reset-password-superadmin, 2026-08-19).
"""

from typing import Optional

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


@router.get("/", response_model=schemas.UserListResponse)
def list_users(
    role: Optional[str] = Query(None),
    exclude_role: Optional[str] = Query(
        None,
        description="Excluir este rol del listado (p.ej. superadmin en la tabla principal)",
    ),
    search: Optional[str] = Query(None, description="Buscar en username, email o nombre"),
    is_active: Optional[bool] = Query(None),
    locked_only: bool = Query(False, description="Solo cuentas bloqueadas ahora mismo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("username"),
    sort_dir: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    filas, total = crud.list_users(
        db,
        role=role,
        exclude_role=exclude_role,
        search=search,
        is_active=is_active,
        locked_only=locked_only,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return schemas.UserListResponse(
        items=[schemas.UserResponse.model_validate(f) for f in filas],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


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

    # Un `null` explícito significa "no tocar": ninguna de estas columnas admite
    # NULL salvo `creator_id`, y ese enlace se gestiona abajo (nunca se borra
    # por mandar null, así el perfil de creador sobrevive a un cambio de rol).
    update_data = {
        k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None
    }

    if "role" in update_data:
        _ensure_assignable_role(update_data["role"])

    if update_data.get("email"):
        existing = crud.get_user_by_email(db, update_data["email"])
        if existing and existing.id != target.id:
            raise HTTPException(status_code=409, detail="Ese correo ya está en uso.")

    rol_anterior = target.role
    rol_nuevo = update_data.get("role", rol_anterior)
    era_creador = rol_anterior == models.UserRole.CREADOR.value
    sera_creador = rol_nuevo == models.UserRole.CREADOR.value
    creator_id_explicito = update_data.pop("creator_id", None)

    elegido = None
    if creator_id_explicito is not None:
        if not sera_creador:
            raise HTTPException(
                status_code=400,
                detail="Solo los usuarios de rol 'creador' pueden vincularse a un creador.",
            )
        elegido = crud.get_creator(db, creator_id_explicito)
        if not elegido:
            raise HTTPException(status_code=404, detail="Creador no encontrado.")
        otro = (
            db.query(models.User)
            .filter(models.User.creator_id == elegido.id, models.User.id != target.id)
            .first()
        )
        if otro:
            raise HTTPException(status_code=409, detail="Ese creador ya tiene un usuario vinculado.")

    # Un usuario con rol 'creador' SIEMPRE debe tener su perfil de creador
    # (tickets, ciclos y préstamos de Equipos cuelgan de él). Al promover a
    # alguien (p.ej. admin → creador) el perfil se crea o reactiva aquí mismo;
    # al sacarlo del rol se desactiva (no se borra: conserva su historial).
    accion = None
    creador = None
    if sera_creador:
        if elegido is not None:
            creador = elegido
        elif target.creator_id:
            creador = crud.get_creator(db, target.creator_id)
        if creador is None:
            nombre = update_data.get("full_name") or target.full_name
            creador = crud.create_creator_for_user(db, nombre)
            accion = "creado"
        else:
            if not era_creador and not creador.is_active:
                creador.is_active = True
                accion = "reactivado"
            elif elegido is not None and elegido.id != target.creator_id:
                accion = "vinculado"
        target.creator_id = creador.id
    elif era_creador and target.creator_id:
        creador = crud.get_creator(db, target.creator_id)
        if creador and creador.is_active:
            creador.is_active = False
            accion = "desactivado"

    try:
        updated = crud.update_user_admin(db, target, update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese creador ya tiene un usuario vinculado.")

    detalle = f"role {rol_anterior}->{rol_nuevo}" if rol_anterior != rol_nuevo else None
    if accion and creador is not None:
        detalle = f"{detalle + '; ' if detalle else ''}creador {accion} (creator_id={creador.id})"
    crud.log_audit(
        db, actor_user_id=current_user.id, action="user.update", target_type="user", target_id=target.id,
        details=detalle,
    )

    respuesta = schemas.UserResponse.model_validate(updated)
    if accion and creador is not None:
        respuesta.creador_accion = accion
        respuesta.creador_nombre = creador.name
    return respuesta


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


@router.post("/{user_id}/reset-password-superadmin", response_model=schemas.ResetPasswordResponse)
def reset_password_superadmin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    """Reset de contraseña ENTRE superadmins (2026-08-19): la única operación
    permitida sobre la cuenta superadmin por API. Rol y estado siguen siendo
    inmutables; esto resuelve "un superadmin perdió su contraseña" sin acceso
    al servidor. backend/reset_superadmin_password.py queda como emergencia
    de último recurso (cuando no hay otro superadmin disponible).

    Diferencias a propósito con el script de servidor: este endpoint NO
    reactiva un superadmin desactivado (cambiar su estado sigue prohibido) y
    nunca aplica sobre uno mismo."""
    target = _get_target_or_404(db, user_id)

    if target.role != models.UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=400, detail="El usuario destino no es superadministrador."
        )
    if target.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Para tu propia contraseña usa /api/auth/change-password.",
        )

    # Desbloquea el target si estaba bloqueado por intentos fallidos (igual que
    # el script de servidor): un reset entre pares debe poder rescatar a un
    # superadmin bloqueado por un ataque de login. Un solo commit al final
    # (set_user_password commitea).
    target.failed_login_attempts = 0
    target.locked_until = None

    temp_password = security.generate_temp_password()
    crud.set_user_password(db, target, security.hash_password(temp_password), must_change_password=True)
    crud.revoke_all_refresh_tokens_for_user(db, target.id)

    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="password.reset_superadmin",
        target_type="user",
        target_id=target.id,
    )
    return schemas.ResetPasswordResponse(temporary_password=temp_password)


@router.post("/{user_id}/unlock", response_model=schemas.UserResponse)
def desbloquear_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("usuarios", "gestionar")),
):
    """Un clic: limpia intentos fallidos y `locked_until`, sin tocar contraseña
    ni sesiones. Para la cuenta superadmin sigue existiendo el camino dedicado
    (`reset-password-superadmin`, que ya desbloquea de paso)."""
    target = _get_target_or_404(db, user_id)
    _ensure_not_superadmin_target(target)

    crud.unlock_user(db, target)
    crud.log_audit(
        db,
        actor_user_id=current_user.id,
        action="account.unlock_by_admin",
        target_type="user",
        target_id=target.id,
    )
    return target


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
    # Un usuario 'creador' y su perfil van juntos: si la cuenta se desactiva (o
    # reactiva), el perfil deja de aparecer (o vuelve a aparecer) en las listas.
    # Solo aplica mientras el rol sea 'creador': un perfil desactivado porque su
    # usuario pasó a otro rol no se reactiva por activar la cuenta.
    if target.role == models.UserRole.CREADOR.value and target.creator_id:
        perfil = crud.get_creator(db, target.creator_id)
        if perfil and perfil.is_active != data.is_active:
            perfil.is_active = data.is_active
            db.commit()
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
