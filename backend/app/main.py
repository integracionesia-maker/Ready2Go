"""FastAPI application entry point."""

import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .errores import registrar_manejadores
from .routers import auth, creators, brands, tickets, dashboard, users, general_expenses
from .routers import roles, user_roles, empresas, equipos_dashboard, equipment
from .routers import loans, approvals, media, responsivas, notifications

Base.metadata.create_all(bind=engine)

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

# En producción se deshabilitan /docs y /redoc (Swagger/Redoc quedaban abiertos sin auth).
IS_PRODUCTION = os.getenv("ENV", "development") == "production"

app = FastAPI(
    title="Control de Presupuestos - Creadores de Contenido",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
