"""Envio de correo por SMTP con la libreria estandar.

`smtplib` y nada mas: sin SDK, sin API key, sin cuenta nueva que administrar.
La decision esta en §1.2 del plan (se descartaron Telegram, Resend y WhatsApp).

Dos cosas que este modulo hace y conviene no "simplificar":

1. **`NOTIF_ENABLED` es un corta-circuito real**, no un log condicional: con
   `false` no se abre socket. Es el rollback de §13 ("correos disparados por
   error") y lo que permite probar todo el modulo sin cuenta SMTP.
2. **Nunca levanta hacia arriba.** Devuelve un resultado. Un SMTP caido no puede
   tumbar el registro de un prestamo (§10.15): el equipo ya salio por la puerta,
   que el correo falle no puede deshacer eso.

Las variables se leen en cada envio, no al importar: cambiar `NOTIF_ENABLED` no
debe exigir reiniciar uvicorn.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

__all__ = [
    "Config",
    "Resultado",
    "config",
    "notificaciones_activas",
    "enviar",
    "NOMBRE_REMITENTE",
]

NOMBRE_REMITENTE = "Ready2Go — Control de Equipos"


def _bool_env(nombre: str, default: bool) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in ("1", "true", "yes", "si", "on")


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    user: str
    password: str
    remitente: str
    starttls: bool
    habilitado: bool
    url_publica: str

    @property
    def completa(self) -> bool:
        """Hay lo minimo para intentar un envio: servidor y remitente."""
        return bool(self.host and self.remitente)


def config() -> Config:
    return Config(
        host=os.getenv("SMTP_HOST", "").strip(),
        port=int(os.getenv("SMTP_PORT", "587") or 587),
        user=os.getenv("SMTP_USER", "").strip(),
        password=os.getenv("SMTP_PASSWORD", ""),
        remitente=os.getenv("SMTP_FROM", "").strip(),
        starttls=_bool_env("SMTP_STARTTLS", True),
        # Apagado por defecto: que un entorno nuevo no mande correo a nadie del
        # area por el solo hecho de arrancar.
        habilitado=_bool_env("NOTIF_ENABLED", False),
        url_publica=os.getenv("APP_PUBLIC_URL", "http://127.0.0.1:5173").rstrip("/"),
    )


def notificaciones_activas() -> bool:
    cfg = config()
    return cfg.habilitado and cfg.completa


@dataclass(frozen=True)
class Resultado:
    """Resultado de un intento. `enviado=False` con `motivo` explica por que."""

    enviado: bool
    motivo: str | None = None
    omitido: bool = False  # apagado o sin configurar: no es un fallo


def _armar(cfg: Config, destinatario: str, asunto: str, cuerpo: str, adjuntos) -> EmailMessage:
    mensaje = EmailMessage()
    mensaje["From"] = formataddr((NOMBRE_REMITENTE, cfg.remitente))
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    # Texto plano: sin CSP que pelear, sin imagenes remotas que se bloqueen, y
    # legible en cualquier cliente. Si marketing quiere HTML es decision de
    # marca, no del servidor.
    mensaje.set_content(cuerpo)

    for nombre, contenido, tipo in adjuntos or []:
        principal, _, secundario = tipo.partition("/")
        mensaje.add_attachment(
            contenido, maintype=principal, subtype=secundario or "octet-stream", filename=nombre
        )
    return mensaje


def enviar(
    destinatario: str,
    asunto: str,
    cuerpo: str,
    adjuntos: list[tuple[str, bytes, str]] | None = None,
) -> Resultado:
    """Manda un correo. **Nunca levanta.**

    `omitido=True` cuando las notificaciones estan apagadas o sin configurar: no
    es un fallo y no debe contarse como intento fallido ni disparar reintentos.
    """
    cfg = config()

    if not cfg.habilitado:
        return Resultado(False, "NOTIF_ENABLED=false", omitido=True)
    if not cfg.completa:
        return Resultado(False, "Falta SMTP_HOST o SMTP_FROM", omitido=True)
    if not destinatario:
        return Resultado(False, "Destinatario vacio", omitido=True)

    mensaje = _armar(cfg, destinatario, asunto, cuerpo, adjuntos)

    try:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as servidor:
            if cfg.starttls:
                servidor.starttls(context=ssl.create_default_context())
            if cfg.user:
                servidor.login(cfg.user, cfg.password)
            servidor.send_message(mensaje)
    except Exception as exc:  # noqa: BLE001
        # Se atrapa todo a proposito: DNS caido, TLS mal configurado, credencial
        # vencida, buzon lleno. Cualquiera de esas cosas es un problema de
        # correo, no del prestamo que acaba de registrarse.
        return Resultado(False, f"{type(exc).__name__}: {exc}")

    return Resultado(True)
