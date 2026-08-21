"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import audit_queue
from .database import engine, Base
from .errores import registrar_manejadores
from .middleware_audit import AuditMiddleware
from .routers import auth, creators, brands, tickets, dashboard, users, general_expenses
from .routers import roles, user_roles, empresas, equipos_dashboard, equipment
from .routers import loans, approvals, media, responsivas, notifications
from .routers import audit_logs
from .routers import rubros, operational_expenses

Base.metadata.create_all(bind=engine)

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

# En producción se deshabilitan /docs y /redoc (Swagger/Redoc quedaban abiertos sin auth).
IS_PRODUCTION = os.getenv("ENV", "development") == "production"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranca y detiene el consumidor de la cola de auditoria."""
    tarea = audit_queue.iniciar_consumidor()
    yield
    await audit_queue.detener_consumidor(tarea)


app = FastAPI(
    title="Control de Presupuestos - Creadores de Contenido",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Registrado DESPUES de CORS a proposito: Starlette envuelve los middleware en
# orden inverso al que se agregan, asi que CORS queda mas externo (procesa el
# preflight OPTIONS antes) y este corre ya sobre requests reales.
app.add_middleware(AuditMiddleware)

# El mount estático de /uploads se eliminó: todo comprobante se sirve ahora vía
# GET /api/tickets/file/{id}, que valida sesión y pertenencia del ticket.

# Sobre de error unico del contrato de Equipos ({detail, codigo}). El manejador
# por defecto de FastAPI envuelve el detalle y deja `codigo` anidado, asi que el
# cliente no lo encontraria en la raiz. Ver app/errores.py.
registrar_manejadores(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(creators.router)
app.include_router(brands.router)
app.include_router(tickets.router)
app.include_router(dashboard.router)
app.include_router(general_expenses.router)
# Control de Equipos
app.include_router(roles.router)
app.include_router(user_roles.router)
app.include_router(empresas.router)
# El dashboard va ANTES del router de inventario: comparten prefijo y
# /{id} se tragaria /dashboard como si fuera un id (contrato §2).
app.include_router(equipos_dashboard.router)
app.include_router(equipment.router)
app.include_router(loans.router)
app.include_router(approvals.router)
app.include_router(responsivas.router)
app.include_router(media.router)
# Diagnostico de correo. Fuera del contrato v1: lo pide la asignacion (S6) y va
# protegido con `usuarios:gestionar`, que hoy solo tiene el superadmin.
app.include_router(notifications.router)
app.include_router(audit_logs.router)
# Gastos Operativos (modulo aislado de marketing)
app.include_router(rubros.router)
app.include_router(operational_expenses.router)

# Fuerza la construccion de todos los schemas de OpenAPI (incluidos los
# TypeAdapter de Pydantic para cada query param, ej. `Optional[date]`) en el
# arranque en vez de perezosa en el primer request real. Sin esto, la
# primera resolucion de un tipo compartido (ej. `date | None`, usado en
# dashboard.py/loans.py/audit_logs.py) puede caer dentro de un
# `freeze_time(...)` de alguna prueba y reventar con un FastAPIError que no
# tiene nada que ver con esa prueba -- visto en la practica al agregar el
# router de auditoria.
app.openapi()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

# realpath: resuelve symlinks y "." para poder comparar contra el candidato de
# cada request y confirmar que la ruta pedida no se sale del directorio.
_frontend_dist = os.path.realpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "dist"
))

if os.path.isdir(_frontend_dist):
    _assets_dir = os.path.join(_frontend_dist, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    _index_html = os.path.join(_frontend_dist, "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Contención de path traversal. Starlette NO normaliza el `..` de la
        # ruta antes de llegar aquí, así que `os.path.join(dist, full_path)` con
        # `full_path="../../backend/.env"` apuntaba fuera de dist y servía ese
        # archivo (JWT_SECRET_KEY, la base). Se resuelve la ruta real y se exige
        # que caiga DENTRO de dist; cualquier intento de salida cae al SPA.
        candidato = os.path.realpath(os.path.join(_frontend_dist, full_path))
        dentro = candidato == _frontend_dist or candidato.startswith(_frontend_dist + os.sep)
        if dentro and os.path.isfile(candidato):
            return FileResponse(candidato)
        return FileResponse(_index_html)
