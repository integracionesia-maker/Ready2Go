# GOCreate — Plataforma de Marketing (Grupo Ortiz)

Herramienta interna del área de marketing: **dos módulos, una app, un login, un deploy**.

- **Presupuestos** — control de presupuesto de creadores de contenido: ciclos semanal/mensual, tickets con comprobante, validación, gastos generales y operativos, dashboard con meta de gasto mensual y reporte HTML.
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

- **Backend**: `cd backend && python -m pytest` — 786 funciones de prueba (conteo por búsqueda al 05/11/26; auth, permisos, ciclos, validación, soft-delete, equipos, RBAC, auditoría).
- **E2E**: 11 specs Playwright en `frontend/e2e/` — requieren backend y frontend corriendo; correr los specs por separado (rate limit de login: 30/15min por IP). Ver `docs/presupuestos/auth/auth-manual-usuario.md`.

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
- **Seguridad**: [SECURITY.md](./SECURITY.md) · [diagnóstico 2026-08-18](./docs/seguridad/diagnostico-seguridad-2026-08-18.md)

## Estado del deploy

**En producción** en `https://gocreate.mx` (Mac mini de marketing, túnel Cloudflare hacia uvicorn en `127.0.0.1:8000`, un worker). Despliegue: `sudo /opt/go/bin/deploy-app.sh gocreate` (respaldo y rollback automáticos); ver `docs/deploy/acceso-deploy-gocreate.md` antes de rehacer nada. Fecha de salida: el Observatorio dice 10/08/26 y el repo la prueba desde el 27/08/26 (ver `status.md`). Pendiente de seguridad en producción: cabeceras CSP/HSTS y respaldos programados (`SECURITY.md`). En desarrollo corre local en `127.0.0.1:8000` y `127.0.0.1:5173`.
