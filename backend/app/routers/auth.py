"""Login, refresh, logout, perfil propio y cambio de contraseña."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import crud, models, rbac_catalog, schemas, security
from ..database import get_db
from ..dependencies import get_current_user
from ..rbac import permisos_del_request

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=security.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=security.IS_PRODUCTION,
        samesite="lax",
        path="/",
        max_age=security.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key=security.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=security.IS_PRODUCTION,
        samesite="lax",
        path=security.REFRESH_COOKIE_PATH,
        max_age=security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(security.ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(security.REFRESH_COOKIE_NAME, path=security.REFRESH_COOKIE_PATH)


def _issue_session(db: Session, response: Response, user: models.User) -> None:
    access_token = security.create_access_token(user.id, user.role, user.token_version)
    raw_refresh = security.generate_refresh_token()
    crud.create_refresh_token_record(
        db, user.id, security.hash_refresh_token(raw_refresh), security.refresh_token_expiry()
    )
    _set_auth_cookies(response, access_token, raw_refresh)


@router.post("/login", response_model=schemas.LoginResponse)
def login(
    payload: schemas.LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"

    if security.is_ip_rate_limited(client_ip):
        raise HTTPException(
            status_code=429, detail="Demasiados intentos de inicio de sesión. Intenta más tarde."
        )
    security.register_login_attempt(client_ip)

    generic_error = HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    user = crud.get_user_by_identifier(db, payload.identificador)

    if not user:
        crud.log_audit(db, action="login.failed", ip_address=client_ip, details="usuario no encontrado")
        raise generic_error

    if crud.is_locked(user):
        crud.log_audit(
            db, actor_user_id=user.id, action="login.failed", ip_address=client_ip,
            details="cuenta bloqueada temporalmente",
        )
        raise HTTPException(
            status_code=401,
            detail="Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.",
        )

    if not user.is_active:
        crud.log_audit(
            db, actor_user_id=user.id, action="login.failed", ip_address=client_ip,
            details="usuario inactivo",
        )
        raise generic_error

    if not security.verify_password(payload.password, user.password_hash):
        crud.register_failed_login(db, user)
        crud.log_audit(db, actor_user_id=user.id, action="login.failed", ip_address=client_ip)
        raise generic_error

    crud.register_successful_login(db, user)
    crud.log_audit(db, actor_user_id=user.id, action="login.success", ip_address=client_ip)

    _issue_session(db, response, user)
    return schemas.LoginResponse(user=schemas.UserResponse.model_validate(user))


@router.post("/refresh", response_model=schemas.LoginResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    invalid_session = HTTPException(status_code=401, detail="Sesión no válida. Inicia sesión de nuevo.")
    raw_refresh = request.cookies.get(security.REFRESH_COOKIE_NAME)
    if not raw_refresh:
        _clear_auth_cookies(response)
        raise invalid_session

    token_row = crud.get_refresh_token_by_hash(db, security.hash_refresh_token(raw_refresh))
    if not token_row:
        _clear_auth_cookies(response)
        raise invalid_session

    if token_row.revoked_at is not None:
        crud.revoke_all_refresh_tokens_for_user(db, token_row.user_id)
        # Invalida los access tokens ya emitidos para que un JWT robado
        # no sobreviva a la detección de reuso (hallazgo #1 auditoría).
        user_who_reused = crud.get_user(db, token_row.user_id)
        if user_who_reused:
            user_who_reused.token_version += 1
            db.commit()
        crud.log_audit(
            db, actor_user_id=token_row.user_id, action="refresh.reuse_detected",
        )
        _clear_auth_cookies(response)
        raise invalid_session

    if token_row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="La sesión expiró. Inicia sesión de nuevo.")

    user = crud.get_user(db, token_row.user_id)
    if not user or not user.is_active:
        _clear_auth_cookies(response)
        raise invalid_session

    new_raw_refresh = security.generate_refresh_token()
    crud.rotate_refresh_token(
        db, token_row, security.hash_refresh_token(new_raw_refresh), security.refresh_token_expiry()
    )
    access_token = security.create_access_token(user.id, user.role, user.token_version)
    _set_auth_cookies(response, access_token, new_raw_refresh)

    return schemas.LoginResponse(user=schemas.UserResponse.model_validate(user))


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(
    request: Request,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_refresh = request.cookies.get(security.REFRESH_COOKIE_NAME)
    if raw_refresh:
        token_row = crud.get_refresh_token_by_hash(db, security.hash_refresh_token(raw_refresh))
        if token_row and token_row.revoked_at is None:
            crud.revoke_refresh_token(db, token_row)

    # Invalida los access tokens ya emitidos para que un JWT robado
    # no sobreviva al cierre de sesión (hallazgo #1 auditoría).
    current_user.token_version += 1
    db.commit()

    crud.log_audit(db, actor_user_id=current_user.id, action="logout")
    _clear_auth_cookies(response)
    return schemas.MessageResponse(message="Sesión cerrada.")


@router.get("/me", response_model=schemas.UserResponse)
def me(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Los permisos van aquí y no en login/refresh: es el único endpoint que el
    # cliente vuelve a consultar cuando cambia algo, así que un aditivo
    # concedido se ve sin cerrar sesión. El cliente los usa SOLO para pintar;
    # cada endpoint valida por su cuenta (contrato §1).
    # Si la base falla al resolverlos sale 503 PERMISOS_NO_DISPONIBLES, nunca
    # {} silencioso ni 401: un dict vacío se leería como política y el cliente
    # desloguearía a todo el mundo por un problema de infraestructura.
    respuesta = schemas.UserResponse.model_validate(current_user)
    respuesta.permisos = rbac_catalog.a_json(
        permisos_del_request(request, db, current_user)
    )
    return respuesta


@router.put("/me", response_model=schemas.UserResponse)
def update_me(
    payload: schemas.UpdateProfileRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.email and payload.email != current_user.email:
        existing = crud.get_user_by_email(db, payload.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=409, detail="Ese correo ya está en uso.")

    updated = crud.update_user_profile(db, current_user, payload.full_name, payload.email)
    crud.log_audit(
        db, actor_user_id=current_user.id, action="user.update",
        target_type="user", target_id=current_user.id,
    )
    return updated


@router.post("/change-password", response_model=schemas.MessageResponse)
def change_password(
    payload: schemas.ChangePasswordRequest,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not security.verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")

    error = security.validate_password_strength(payload.new_password, current_user.username)
    if error:
        raise HTTPException(status_code=400, detail=error)

    crud.set_user_password(
        db, current_user, security.hash_password(payload.new_password), must_change_password=False
    )
    # Invalida el resto de sesiones activas; esta misma sesión se re-emite abajo.
    crud.revoke_all_refresh_tokens_for_user(db, current_user.id)
    _issue_session(db, response, current_user)

    crud.log_audit(db, actor_user_id=current_user.id, action="password.changed_self")
    return schemas.MessageResponse(message="Contraseña actualizada.")
