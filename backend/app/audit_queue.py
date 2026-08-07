"""Cola de auditoria en memoria con consumidor unico y batching de INSERTs.

Problema original que resolvio el middleware actual (sin GET): cada request
abria una sesion de SQLAlchemy sincrona desde el event loop, compitiendo por
el pool y por el lock de escritor de SQLite — bajo trafico concurrente real
esto agoto el pool y colgo la app entera (hasta 291s por request, incluyendo
/api/health).

Este modulo restaura la auditoria del 100% del trafico (incluyendo cada GET)
sin reintroducir ese patron: cada request solo hace un `put` barato a una
cola en memoria (microsegundos, sin I/O, sin locks), y una unica tarea de
fondo flushea en lotes por threadpool — un solo escritor a la vez, sin
competir.

Riesgo aceptado: si el proceso muere abruptamente (OOM kill, `kill -9`,
corte de luz — no un `systemctl restart` normal, que si drena la cola via
el lifespan de shutdown), los eventos en la cola en memoria en ese instante
se pierden sin posibilidad de recuperacion. Aceptable porque:
  (a) es una herramienta interna, no un libro contable regulado;
  (b) las ~35 llamadas curadas a `crud.log_audit()` no pasan por esta cola;
  (c) la exposicion tipica es de ~200ms de trafico (el intervalo maximo de
      lote antes del flush automatico).
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time as time_module
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger("audit_queue")

# ── Constantes ────────────────────────────────────────────────────────────────

AUDIT_BATCH_MAX_SIZE = 200
AUDIT_BATCH_MAX_INTERVAL_S = 0.2
QUEUE_MAXSIZE = 10_000
SHUTDOWN_DRAIN_TIMEOUT_S = 4.0

# Calculado UNA sola vez al importar el modulo — nunca en cada evento.
HOSTNAME = socket.gethostname()

# ── Cola y contadores ─────────────────────────────────────────────────────────

_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)

_eventos_descartados: int = 0
_ultimo_log_descarte: float = 0.0
_LOG_DESCARTE_INTERVAL_S = 30.0  # rate-limited: un log cada 30s, no por evento


def enqueue(evento: dict) -> None:
    """Encola un evento de auditoria sin bloquear.

    Sincrona a proposito: el middleware la llama desde codigo sincrono dentro
    de `dispatch`. Usa `put_nowait` para nunca bloquear la request real.

    Si la cola esta llena, descarta el evento y loguea de forma rate-limited
    (un mensaje cada ~30s, no uno por evento descartado).
    """
    global _eventos_descartados, _ultimo_log_descarte
    try:
        _queue.put_nowait(evento)
    except asyncio.QueueFull:
        _eventos_descartados += 1
        ahora = time_module.monotonic()
        if ahora - _ultimo_log_descarte >= _LOG_DESCARTE_INTERVAL_S:
            logger.warning(
                "audit_queue llena (%d/%d) — %d eventos descartados (ultimo aviso hace %ds)",
                QUEUE_MAXSIZE, QUEUE_MAXSIZE, _eventos_descartados,
                int(ahora - _ultimo_log_descarte),
            )
            _ultimo_log_descarte = ahora


async def _consumidor() -> None:
    """Unica tarea de fondo: junta eventos en lotes y los flushea.

    Cada iteracion del bucle esta envuelta en su propio try/except — una
    excepcion no capturada mataria la tarea para siempre y la auditoria se
    detendria en silencio.
    """
    while True:
        try:
            # Espera el primer evento del lote con timeout: si no hay trafico
            # en el intervalo maximo, el bucle no se cuelga esperando.
            try:
                primer_evento = await asyncio.wait_for(
                    _queue.get(), timeout=AUDIT_BATCH_MAX_INTERVAL_S
                )
            except asyncio.TimeoutError:
                continue  # nada que flushear en esta iteracion

            lote: list[dict] = [primer_evento]
            deadline = time_module.monotonic() + AUDIT_BATCH_MAX_INTERVAL_S

            # Drena la cola hasta el limite de tamano o de tiempo.
            while len(lote) < AUDIT_BATCH_MAX_SIZE:
                remaining = deadline - time_module.monotonic()
                if remaining <= 0:
                    break
                try:
                    evento = await asyncio.wait_for(_queue.get(), timeout=remaining)
                    lote.append(evento)
                except asyncio.TimeoutError:
                    break

            await _flush(lote)
        except Exception:
            logger.exception("audit_queue: excepcion en el bucle del consumidor — recuperando")


async def _flush(lote: list[dict]) -> None:
    """Flushea un lote de eventos a la base de datos via threadpool.

    El INSERT real (y la resolucion de usernames) siempre corre en threadpool,
    nunca directo en el event loop de la tarea consumidora.
    """
    if not lote:
        return
    await run_in_threadpool(_flush_sync, lote)


def _flush_sync(lote: list[dict]) -> None:
    """Parte sincrona del flush: resuelve usernames en UNA query y hace INSERTs.

    Corre dentro de `run_in_threadpool` — nunca en el event loop.
    """
    from .database import SessionLocal
    from . import models

    # 1. Resolver usernames en una sola query para todo el lote.
    ids_unicos = {e["actor_user_id"] for e in lote if e["actor_user_id"] is not None}
    username_map: dict[int, str] = {}
    if ids_unicos:
        db = SessionLocal()
        try:
            filas = (
                db.query(models.User.id, models.User.username)
                .filter(models.User.id.in_(ids_unicos))
                .all()
            )
            username_map = {uid: uname for uid, uname in filas}
        finally:
            db.close()

    # 2. Construir y escribir las filas.
    db = SessionLocal()
    try:
        for evento in lote:
            ocurrido_en: datetime = evento["ocurrido_en"]
            actor_id = evento["actor_user_id"]
            metodo = evento["http_method"]
            path = evento["endpoint_path"]
            status = evento["response_status"]

            username = username_map.get(actor_id) if actor_id is not None else None

            # endpoint.name: ruta sin la barra inicial
            endpoint_name = path.lstrip("/") if path else ""

            standard = {
                "endpoint": {
                    "type": metodo.lower() if metodo else "",
                    "name": endpoint_name,
                },
                "user": {"name": username},
                "host": {"name": HOSTNAME},
                "date": ocurrido_en.isoformat(),
                "status": status,
                "api": {
                    "metod": metodo or "",
                    "response": evento["duration_ms"],
                },
                "time": ocurrido_en.timestamp(),
                "log": f"{metodo} {path} -> {status}",
            }

            fila = models.AuditLog(
                actor_user_id=actor_id,
                action=f"{metodo} {path}",
                http_method=metodo,
                endpoint_path=path,
                request_params=evento.get("request_params"),
                request_body_summary=evento.get("request_body_summary"),
                response_status=status,
                user_agent=evento.get("user_agent"),
                duration_ms=evento["duration_ms"],
                ip_address=evento.get("ip_address"),
                created_at=ocurrido_en,
                standard_fields=json.dumps(standard, ensure_ascii=False),
            )
            db.add(fila)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def iniciar_consumidor() -> asyncio.Task:
    """Arranca la tarea asyncio del consumidor. Llamar en el startup del lifespan."""
    return asyncio.create_task(_consumidor())


def limpiar_cola() -> None:
    """Descarta TODOS los eventos pendientes en la cola sin flushearlos.

    SOLO para uso en tests — se llama en el fixture `_clean_state` para
    evitar que eventos de un test anterior (con IDs de usuarios que ya no
    existen en la DB recien recreada) causen FK violations.
    """
    while True:
        try:
            _queue.get_nowait()
        except asyncio.QueueEmpty:
            break


def drenar_para_test() -> None:
    """Vacia la cola y flushea sincronicamente — SOLO para uso en tests.

    Los tests usan `TestClient` sin `with`, asi que el lifespan no arranca
    la tarea consumidora. Esta funcion permite que los tests drenen la cola
    explicitamente antes de consultar la DB.
    """
    lote: list[dict] = []
    while True:
        try:
            lote.append(_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    if lote:
        _flush_sync(lote)


async def detener_consumidor(tarea: asyncio.Task) -> None:
    """Drena la cola con timeout y cancela la tarea. Llamar en el shutdown del lifespan."""
    # 1. Dejar de aceptar nuevos eventos.
    #    (No hay flag explicito — el middleware seguira llamando enqueue() hasta
    #    que el proceso muera, pero el drenado es best-effort.)

    # 2. Drenar lo que quede en la cola.
    restantes: list[dict] = []
    deadline = time_module.monotonic() + SHUTDOWN_DRAIN_TIMEOUT_S
    while time_module.monotonic() < deadline:
        try:
            restantes.append(_queue.get_nowait())
        except asyncio.QueueEmpty:
            break

    if restantes:
        logger.info("audit_queue: drenando %d eventos pendientes en shutdown", len(restantes))
        try:
            await asyncio.wait_for(_flush(restantes), timeout=SHUTDOWN_DRAIN_TIMEOUT_S)
        except asyncio.TimeoutError:
            logger.warning(
                "audit_queue: flush de shutdown no completo en %ds — %d eventos perdidos",
                SHUTDOWN_DRAIN_TIMEOUT_S, len(restantes),
            )

    # 3. Cancelar la tarea consumidora.
    tarea.cancel()
    try:
        await tarea
    except asyncio.CancelledError:
        pass
