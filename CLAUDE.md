# GOCreate — Plataforma de Marketing (Presupuestos + Control de Equipos) — Grupo Ortiz

> Conexiones pool: [[CLAUDE]] | [[context_proyectos]] | [[framework_operative_enforcement/CLAUDE]] | [[framework_operative_enforcement/PLAYBOOK]] | [[framework_operative_enforcement/FRAMEWORK]]
> Recursos compartidos: [[IDENTIDAD DE MARCA/context_design]] (visual)
> Archivos del proyecto: [[CLAUDE]] | [[context]] | [[status]] | [[BACKLOG]] | [[RISKS]] | [[MVP_BREAKDOWN]] | [[DESIGN_SYSTEM]] | [[CHANGELOG]] | [[avances_diarios]]
> Documentación: [[docs/presupuestos]] | [[docs/equipos]] | [[docs/historico]] | [[docs/deploy]]
> Docs clave: [[docs/equipos/plan-quirurgico]] | [[docs/presupuestos/auth/auth-arquitectura]] | [[docs/presupuestos/auth/auth-manual-usuario]] | [[docs/presupuestos/presupuestos-y-validacion]] | [[docs/presupuestos/gastos-generales-manual]] | [[docs/presupuestos/borrado-tickets]] | [[docs/presupuestos/responsividad-movil]]

## Que es

Dos modulos de negocio, una sola app, un login, un deploy:

- **Presupuestos** (Fase 5, en uso interno): control de presupuesto de creadores de contenido — ciclos, tickets con comprobante, validacion, gastos generales, dashboard.
- **Control de Equipos** (Fase 3.5, plan aprobado, **sin construir**): prestamo de equipo de grabacion de marketing — inventario, carta responsiva firmada en PDF, fotos antes/despues, autorizacion y confirmacion de la aprobadora (Melisa), notificacion por correo.

Antes se llamaba `presupuesto_creadores`. Renombrado a **Ready2Go** el 27/07/2026 al absorber Control de Equipos (reunion con marketing: Emily Perez, Betzabet Fuentes). Renombrado nuevamente a **GOCreate** el 04/08/2026 (el repo de GitHub sigue en `github.com/integracionesia-maker/Ready2Go`, sin renombrar).

Plan de integracion, RBAC aditivo, modelo de datos y revision adversarial: **`docs/equipos/plan-quirurgico.md`**. Especificacion funcional original de marketing: `docs/equipos/maqueta/CONTROL_DE_EQUIPOS_maqueta_mkt.htm` (maqueta HTML+localStorage — referencia funcional, su implementacion NO se porta; ver §1.3 del plan).

## Stack

Backend: `JWT_SECRET_KEY=<ver .env.example> PYTHONPATH=backend python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (ejecutar **desde** `backend/` — rutas de DB y uploads son relativas al cwd; `JWT_SECRET_KEY` es obligatorio, el proceso no arranca sin él)
Frontend: `npm install && npx vite --host 127.0.0.1 --port 5173`

Primer arranque (o para crear el superadmin si no existe): desde `backend/`, `python seed_auth.py` — ver sección "Autenticación" abajo.

## Reglas criticas

- **Repo git**: `github.com/integracionesia-maker/Ready2Go` (org de Damian). Rama principal `master`; Damian trabaja en `dami-branch` y mergea su master; **Jose trabaja en `jose-branch`**; Beni en `BeniBranch`. Cada quien commitea SOLO en su rama; integrar a `master` solo cuando el usuario lo pida explícitamente. Rutas explícitas en `git add` — nunca `-A` ni `.`.
- **Control de Equipos no se construye sin luz verde de Jose.** El plan (`docs/equipos/plan-quirurgico.md`) está aprobado como diseño, no como orden de build.
- **Roles aditivos (patron Bruckner)** — cuando entre el RBAC nuevo: `users.role` sigue siendo el rol base y los paquetes aditivos (`APROBADOR_EQUIPO`, `CUSTODIO_EQUIPO`, `AUDITOR`) SOLO abren los `(modulo, accion)` que tienen listados; jamás sustituyen ni amplían el rol base en otro módulo. Deny-by-default. Si la DB falla al resolver permisos → **503**, nunca `{}` (un dict vacío = 403 masivo que parece política). Ver §3 del plan.
- **Autenticacion obligatoria** — todos los endpoints (excepto `/api/health` y `/api/auth/login`) requieren sesión; los roles son `superadmin`/`admin`/`creador` (ver `docs/presupuestos/auth/auth-arquitectura.md`). Sigue sin haber HTTPS/CSP/HSTS, así que no exponer fuera de `127.0.0.1` sin agregar eso primero (ver RISKS.md #2 residual).
- **Gestión de usuarios es exclusiva de `superadmin`** (R4) — un `admin` ya no gestiona usuarios en absoluto (ni siquiera los de rol `creador`), recibe 403 en todo `/api/users/*`. Sí gestiona creadores, marcas, ciclos de presupuesto y validación de tickets.
- La cuenta `superadmin` es **inmutable por API** en rol y estado (ningún endpoint cambia su rol ni la desactiva). Su **contraseña** solo puede resetearla **otro superadmin** desde la app: `POST /api/users/{id}/reset-password-superadmin` (contraseña temporal + `must_change_password`, cierra sesiones, desbloquea si estaba bloqueada; nunca sobre uno mismo). `backend/reset_superadmin_password.py` queda como emergencia de servidor cuando no hay otro superadmin disponible. Para sembrar un segundo superadmin local (la API no puede crearlos): `backend/crear_superadmin_extra.py`.
- **Ciclos de presupuesto (semanal/mensual) nunca bloquean por fondos insuficientes** — aprobar un ticket puede dejar el ciclo en negativo a propósito (decisión explícita del usuario); no agregar validación de fondos en `crud.approve_ticket`/`create_ticket`. Un ticket se asigna a su ciclo por la fecha en que se **sube**, no la fecha en que se aprueba — ese campo (`budget_cycle_id`) se fija una sola vez al crear el ticket y nunca se recalcula. Detalle completo: `docs/presupuestos/presupuestos-y-validacion.md`.
- **Estados de ticket**: `pendiente → aprobado | rechazado` (terminales). Solo los tickets subidos por un `creador` nacen `pendiente`; los de `admin`/`superadmin` se auto-aprueban. Un ticket `pendiente` nunca descuenta del ciclo; uno `rechazado` tampoco (nunca).
- **Borrado de tickets (lógico y físico, R12)** — exclusivo de `admin`/`superadmin`. Un ticket con `is_deleted=True` deja de contar para TODO cálculo (listados, dashboard, brand-spend, cola de validación) — el filtro `is_deleted == False` debe estar en **todas** las queries de `tickets` sin excepción. Si el ticket borrado estaba `aprobado`, se revierte su monto del ciclo con `max(0, cycle.spent - amount)` (nunca negativo). El borrado lógico conserva registro y archivo; el físico borra ambos y es irreversible. Detalle completo: `docs/presupuestos/borrado-tickets.md`.
- **Gastos generales (R12)** — tabla `general_expenses` independiente de `tickets`: sin `creator_id`, sin `budget_cycle_id`, sin `status` de validación, pero **con `brand_id` obligatorio** (`nullable=False` — todo gasto general debe estar asociado a una marca para trazabilidad y reportes por marca). Se crean y cuentan de inmediato, solo `admin`/`superadmin`. Mismo patrón de soft/hard delete que tickets pero sin reversión de ciclo (no aplica). **Fusionado en la UI con Gastos Operativos** (antes un módulo/switch aparte, retirado): un mismo formulario dentro de Presupuestos con selector de tipo (General/Operativo) y un listado combinado con distintivo visual por tipo — pero siguen siendo **tablas y endpoints separados** (`general_expenses` con `brand_id`/una fecha/soft+hard delete vs `operational_expenses` con `rubro_id`/dos fechas (`fecha_gasto` define el mes)/solo soft delete), bajo la misma puerta de acceso (`admin`/`superadmin`/`marketing_presupuestos`/`marketing_admin`). El rol base `operativo` (que solo veía ese módulo aislado) se retiró del catálogo. Endpoints `/api/rubros` y `/api/operational-expenses`. Detalle completo: `docs/presupuestos/gastos-generales-manual.md`.
- Convenciones de `frontend/` (theming, PDF, ApexCharts, responsividad móvil, design system): ver `frontend/CLAUDE.md`.
- Convenciones de `backend/` (rutas relativas al cwd, seed de datos): ver `backend/CLAUDE.md`.

## Autenticación

Diseño completo y matriz de permisos: `docs/presupuestos/auth/auth-arquitectura.md`. Manual por rol: `docs/presupuestos/auth/auth-manual-usuario.md`.

Variables de entorno nuevas (ver `.env.example`): `JWT_SECRET_KEY` (obligatoria, generar con `python -c "import secrets; print(secrets.token_hex(32))"`), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `ENV` (`development`/`production`, controla `Secure` en cookies y si `/docs`/`/redoc` quedan expuestos), `SUPERADMIN_USERNAME`/`SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` (solo para `seed_auth.py`).

Pruebas: `cd backend && python -m pytest` (737 pruebas, DB de prueba propia). E2E: archivos en `frontend/e2e/` (`auth.spec.js`, `presupuesto-flujo-completo.spec.js`, `gastos-generales.spec.js`) — correrlos por separado para no acercarse al rate limit de login (30/15min por IP); ver `docs/presupuestos/auth/auth-manual-usuario.md` §Pruebas.

## Presupuestos y validación (R7/R9/R10)

Ciclos de presupuesto, estados de ticket y prioridad de marcas: reglas de negocio completas con ejemplos en `docs/presupuestos/presupuestos-y-validacion.md`. Resumen de las reglas que más importan está en "Reglas criticas" arriba.

## Gastos generales y borrado de tickets (R12)

Gastos operativos independientes de creadores/marcas/ciclos, y borrado lógico/físico de tickets (con reversión de ciclo si el ticket estaba aprobado): reglas de negocio completas en `docs/presupuestos/gastos-generales-manual.md` y `docs/presupuestos/borrado-tickets.md`. Resumen en "Reglas criticas" arriba.

## Responsividad móvil

App usable desde 320px de ancho (ver auditoría original en `docs/historico/auditoria-responsividad-movil.md`). Infraestructura y detalle de qué se implementó: `docs/presupuestos/responsividad-movil.md`. Resumen de las reglas que más importan está en "Reglas criticas" arriba.

## Deploy

No desplegado — corre local en `127.0.0.1:8000` (backend) y `127.0.0.1:5173` (frontend). Sin entorno de produccion todavia. Antes de exponer fuera de `127.0.0.1`: agregar HTTPS (obligatorio para `Secure` en cookies), CSP/HSTS, y revisar `CORS_ORIGINS` (ver RISKS.md #2 residual y `docs/deploy/runbook.md`).
