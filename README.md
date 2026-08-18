# GOCreate — Plataforma de Marketing (Grupo Ortiz)

Herramienta interna del área de marketing: **dos módulos, una app, un login, un deploy**.

- **Presupuestos** — control de presupuesto de creadores de contenido: ciclos semanal/mensual, tickets con comprobante, validación, gastos generales y dashboard.
- **Control de Equipos** — préstamo de equipo de grabación: inventario, carta responsiva firmada (PDF en servidor), fotos antes/después, aprobaciones y notificaciones por correo.

> Historial de nombres: `presupuesto_creadores` → `Ready2Go` (27/07/2026) → `GOCreate` (04/08/2026). El repo de GitHub sigue en `github.com/integracionesia-maker/Ready2Go`.

## Arranque rápido

```bash
# Backend (desde backend/ — rutas de DB y uploads son relativas al cwd)
cd backend
JWT_SECRET_KEY=<ver .env.example> PYTHONPATH=backend python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Primer arranque: crear superadmin si no existe (desde backend/)
python seed_auth.py

# Frontend
cd frontend
npm install
npx vite --host 127.0.0.1 --port 5173
```

## Pruebas

- **Backend**: `cd backend && python -m pytest` — 680 pruebas (auth, permisos, ciclos, validación, soft-delete, equipos, RBAC).
- **E2E**: Playwright en `frontend/e2e/` — requieren backend y frontend corriendo; correr los specs por separado (rate limit de login: 30/15min por IP). Ver `docs/presupuestos/auth/auth-manual-usuario.md`.

## Repositorio y ramas

Rama principal `master`. Cada persona commitea **solo en su rama** y la integración a `master` es explícita:

| Rama | Persona | Carril |
|---|---|---|
| `dami-branch` | Damián | Servidor y datos |
| `jose-branch` | José | Integración y supervisión |
| `BeniBranch` | Beni | Interfaz |

`git add` con rutas explícitas — nunca `-A` ni `.`.

## Documentación

- **Reglas del proyecto**: [CLAUDE.md](./CLAUDE.md) (críticas de negocio, RBAC, estados, borrados)
- **Estado y planes**: [status.md](./status.md) · [BACKLOG.md](./BACKLOG.md) · [RISKS.md](./RISKS.md) · [MVP_BREAKDOWN.md](./MVP_BREAKDOWN.md)
- **Módulos**: [docs/presupuestos/](./docs/presupuestos/) · [docs/equipos/](./docs/equipos/) · [docs/deploy/](./docs/deploy/)
- **Seguridad**: [diagnóstico 2026-08-18](./docs/seguridad/diagnostico-seguridad-2026-08-18.md)

## Estado del deploy

Sin entorno de producción — corre local en `127.0.0.1:8000` (backend) y `127.0.0.1:5173` (frontend). Antes de exponer fuera de localhost: HTTPS (obligatorio para cookies `Secure`), CSP/HSTS y revisión de `CORS_ORIGINS` (ver RISKS.md y `docs/deploy/runbook.md`).
