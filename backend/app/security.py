"""Password hashing, JWT access tokens, refresh-token helpers and login rate limiting."""

import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import Request
from fastapi.responses import JSONResponse

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"
IS_PRODUCTION = os.getenv("ENV", "development") == "production"


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY no esta configurado. Defina esta variable de entorno "
            "(ver .env.example) antes de levantar el backend."
        )
    return secret


_hasher = PasswordHasher()


# ── Contraseñas ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def validate_password_strength(password: str, username: str) -> Optional[str]:
    """Devuelve un mensaje de error en español, o None si la contraseña es válida."""
    if len(password) < 10:
        return "La contraseña debe tener al menos 10 caracteres."
    if password.lower() == username.lower():
        return "La contraseña no puede ser igual al nombre de usuario."
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        return "La contraseña debe combinar letras y números."
    return None


def generate_temp_password() -> str:
    return f"Temporal-{secrets.token_hex(4)}"


# ── Access token (JWT) ──────────────────────────────────────────────────────

def create_access_token(user_id: int, role: str, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# ── Refresh token (opaco, hasheado en DB) ───────────────────────────────────

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    # Naive UTC: SQLite devuelve datetimes sin tzinfo, y se compara contra este valor
    # (ver routers/auth.py:refresh) — debe quedar en el mismo formato para poder comparar.
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


# ── Error de cuenta bloqueada ────────────────────────────────────────────────
# `HTTPException` normal no sirve aqui: su manejador por defecto envuelve el
# detalle en `{"detail": <lo que sea>}`, asi que un `codigo` adentro quedaria
# anidado y el cliente no lo encontraria en la raiz del cuerpo (mismo problema
# que resuelve `errores.py` para Equipos; ese archivo es de otro modulo y no
# se toca desde aqui, asi que esta es su propia excepcion con su propio
# manejador, mismo patron).

CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA"


class CuentaBloqueadaError(Exception):
    def __init__(self, detail: str, locked_until: datetime | None):
        super().__init__(detail)
        self.detail = detail
        self.locked_until = locked_until

    def cuerpo(self) -> dict:
        return {
            "detail": self.detail,
            "codigo": CUENTA_BLOQUEADA,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
        }


async def _manejador_cuenta_bloqueada(request: Request, exc: CuentaBloqueadaError) -> JSONResponse:
    return JSONResponse(status_code=401, content=exc.cuerpo())


def registrar_manejador_cuenta_bloqueada(app) -> None:
    app.add_exception_handler(CuentaBloqueadaError, _manejador_cuenta_bloqueada)


# ── Rate limiting en memoria por IP (defensa adicional al bloqueo por cuenta) ─
# Proceso único (uvicorn sin --workers) — el contador vive en memoria y se
# reinicia si el proceso se reinicia; no es distribuido. Ver doc/auth-diseno-fase1.md §0.6.

_LOGIN_WINDOW_SECONDS = 15 * 60
_MAX_ATTEMPTS_PER_IP = 30

_login_attempts_by_ip: dict[str, list[float]] = {}


def register_login_attempt(ip: str) -> None:
    now = time.monotonic()
    cutoff = now - _LOGIN_WINDOW_SECONDS
    attempts = [t for t in _login_attempts_by_ip.get(ip, []) if t >= cutoff]
    attempts.append(now)
    _login_attempts_by_ip[ip] = attempts


def is_ip_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    cutoff = now - _LOGIN_WINDOW_SECONDS
    attempts = [t for t in _login_attempts_by_ip.get(ip, []) if t >= cutoff]
    return len(attempts) >= _MAX_ATTEMPTS_PER_IP


# ── Rompecabezas de auto-desbloqueo ─────────────────────────────────────────
# Casero a proposito: sin cuenta externa ni API key que administrar (mismo
# criterio que descarto Resend por correo, ver mailer.py). No es defensa
# seria contra un atacante que automatiza un navegador real — eso requeriria
# un proveedor dedicado — pero exige ejecutar JS con eventos de puntero y
# arrastrar con un tiempo minimo plausible, lo suficiente para que una cuenta
# bloqueada por error (typo repetido) no dependa de esperar el backoff ni de
# molestar al superadmin.
#
# En memoria, proceso unico, mismo patron que `_login_attempts_by_ip` arriba:
# no sobrevive un reinicio y no es distribuido.

_CHALLENGE_TTL_SECONDS = 120
_CHALLENGE_MAX_INTENTOS = 5
_CHALLENGE_TOLERANCIA_PERCENT = 4.0
_CHALLENGE_MIN_SOLVE_SECONDS = 0.35

# Limite de auto-desbloqueos por cuenta: sin esto, el rompecabezas volveria
# inutil el backoff exponencial (bloquear -> resolver -> volver a probar
# contraseñas, indefinidamente). 3 por dia deja margen de sobra para un typo
# repetido y sigue forzando contactar al superadmin ante algo mas serio.
_SELF_UNLOCK_MAX_PER_DAY = 3
_SELF_UNLOCK_WINDOW_SECONDS = 24 * 60 * 60

_unlock_challenges: dict[str, dict] = {}
_self_unlock_count_by_user: dict[int, list[float]] = {}


def _purgar_challenges_vencidos() -> None:
    ahora = time.monotonic()
    vencidos = [cid for cid, c in _unlock_challenges.items() if ahora - c["creado"] > _CHALLENGE_TTL_SECONDS]
    for cid in vencidos:
        _unlock_challenges.pop(cid, None)


def self_unlock_disponible(user_id: int) -> bool:
    now = time.monotonic()
    cutoff = now - _SELF_UNLOCK_WINDOW_SECONDS
    usados = [t for t in _self_unlock_count_by_user.get(user_id, []) if t >= cutoff]
    _self_unlock_count_by_user[user_id] = usados
    return len(usados) < _SELF_UNLOCK_MAX_PER_DAY


def registrar_self_unlock(user_id: int) -> None:
    _self_unlock_count_by_user.setdefault(user_id, []).append(time.monotonic())


def crear_challenge_desbloqueo(user_id: int) -> dict:
    _purgar_challenges_vencidos()
    challenge_id = secrets.token_urlsafe(16)
    target_percent = round(secrets.randbelow(760) / 10 + 12, 1)  # 12.0-87.9
    _unlock_challenges[challenge_id] = {
        "user_id": user_id,
        "target_percent": target_percent,
        "creado": time.monotonic(),
        "intentos": 0,
    }
    return {
        "challenge_id": challenge_id,
        "target_percent": target_percent,
        "expira_en_segundos": _CHALLENGE_TTL_SECONDS,
    }


def verificar_challenge_desbloqueo(
    challenge_id: str, user_id: int, posicion_percent: float, trail: list[dict]
) -> tuple[bool, str | None]:
    """`(exito, motivo_si_fallo)`. Nunca levanta: un challenge invalido o
    vencido es un fallo mas, no un 500."""
    _purgar_challenges_vencidos()
    challenge = _unlock_challenges.get(challenge_id)
    if challenge is None:
        return False, "El rompecabezas expiró o no es válido. Genera uno nuevo."
    if challenge["user_id"] != user_id:
        return False, "El rompecabezas expiró o no es válido. Genera uno nuevo."

    challenge["intentos"] += 1
    if challenge["intentos"] > _CHALLENGE_MAX_INTENTOS:
        _unlock_challenges.pop(challenge_id, None)
        return False, "Demasiados intentos con este rompecabezas. Genera uno nuevo."

    transcurrido = time.monotonic() - challenge["creado"]
    if transcurrido < _CHALLENGE_MIN_SOLVE_SECONDS:
        return False, "Muy rápido para ser un arrastre real. Inténtalo de nuevo."

    # Rastro minimo de movimiento: dos puntos identicos (o solo el inicio y el
    # final) sugieren un valor inyectado directo, no un arrastre real.
    xs = {p.get("x") for p in (trail or [])}
    if len(trail or []) < 3 or len(xs) < 2:
        return False, "No se detectó un arrastre real. Inténtalo de nuevo."

    if abs(posicion_percent - challenge["target_percent"]) > _CHALLENGE_TOLERANCIA_PERCENT:
        return False, "La pieza no quedó en su lugar. Inténtalo de nuevo."

    _unlock_challenges.pop(challenge_id, None)
    return True, None
