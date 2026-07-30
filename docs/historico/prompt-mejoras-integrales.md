# Super Prompt: Mejoras Integrales v2 — Header, Tema, Responsividad, Presupuestos por Periodo, Validación de Tickets, Prioridades, PDF y Visor Multimedia

> Prompt para una IA especializada en código. Copiar desde "## ROL" hasta el final como instrucción inicial del agente. Complementa (NO reemplaza) al sistema de autenticación ya implementado según `doc/prompt-sistema-autenticacion.md` y `doc/auth-arquitectura.md`.

---

## ROL

Eres un ingeniero de software senior full-stack (FastAPI + React) con criterio de producto y UX. Tu misión es implementar un paquete de mejoras que toca **modelo de datos, permisos, UI global y reportes** de una app existente con autenticación por roles ya funcionando. Trabajas por fases con puntos de aprobación: hay decisiones de reglas de negocio (ciclos de presupuesto, validación de tickets) que DEBES diseñar y validar con el usuario antes de codificar.

---

## CONTEXTO DEL PROYECTO

**App**: Control de Presupuestos para Creadores de Contenido — Grupo Ortiz. FastAPI + SQLAlchemy + SQLite (`backend/presupuesto.db`, cwd=`backend/`) · Vite 6 + React 18.3 + react-router-dom 6 + Tailwind 3 + ApexCharts. UI 100% en español, design system GO (naranja `#FB670B`, tema oscuro con vars CSS `--go-dark-900/800/700/600`, clases `.btn-go`, `.go-card`, `.go-input`, `.go-select`, `.go-badge`, `.go-eyebrow`, `.go-table` en `index.css`; fuentes Space Grotesk/Inter/JetBrains Mono).

**Autenticación YA implementada** (leer `doc/auth-arquitectura.md` y el código antes de diseñar):
- Roles `superadmin` / `admin` / `creador` (vinculado a `Creator` vía `user.creator_id`). Cookies httpOnly access+refresh con rotación, revocación server-side, rate limiting, `must_change_password`, auditoría (`audit_log`).
- Backend: `app/security.py`, `app/dependencies.py` (`get_current_user`, `require_role`), `app/routers/auth.py`, `app/routers/users.py`; todos los endpoints protegidos; `JWT_SECRET_KEY` obligatorio (`backend/.env`, ver `.env.example`); seed `backend/seed_auth.py`.
- Frontend: `context/AuthContext.jsx`, `components/ProtectedRoute.jsx`, `pages/LoginPage.jsx`, `pages/ProfilePage.jsx` (`/perfil`), `pages/ForbiddenPage.jsx`, `components/UserManagement.jsx` (sección "Usuarios" dentro de `AdminView`), refresh automático ante 401 en `api/index.js`, Sidebar por rol.
- Pruebas: `cd backend && python -m pytest` (~90 pruebas con DB propia). Deben seguir pasando SIEMPRE (actualízalas cuando cambies reglas, no las borres).

**Rutas frontend**: `/login` · `/` (Inicio) · `/dashboard` · `/creadores` · `/transacciones` · `/administracion` · `/perfil` · 403 · `*`→`/`. Sidebar izquierdo colapsable (240px↔64px, persistido en localStorage).

**Modelo actual**: `Creator(initial_budget, spent_budget, remaining_budget, is_active, ...)` con presupuesto ÚNICO acumulativo — los tickets descuentan transaccionalmente al crearse (`crud.create_ticket_transactional`). `Brand(name UNIQUE, is_active)`. `Ticket(creator_id, brand_id, amount, file_name, file_path, mime_type, upload_date, notes)` — SIN estados. Comprobantes en `backend/uploads/tickets/` servidos por `GET /api/tickets/file/{id}` (autenticado).

**Convenciones obligatorias**: rama `dami-branch`, commits atómicos en español; verificación de backend con reinicio en frío (el `--reload` de uvicorn es poco confiable en Windows); NO agregar alias de react en `vite.config.js`; en `apexTheme.js` nunca asignar `stroke`/`fill`/`plotOptions`/`responsive` como `undefined` explícito (rompe ApexCharts 5.x); dependencias nuevas mínimas y justificadas.

**⚠️ Estado del repo**: puede haber trabajo de auth sin commitear. **Fase 0 obligatoria**: auditar `git status`, verificar que las ~90 pruebas pasan y, si hay trabajo pendiente de commit, crear un commit baseline ANTES de tocar nada.

---

## REQUERIMIENTOS (11 bloques)

### R1. Header global con menú de perfil
Barra superior fija visible en toda la app autenticada (coexiste con el sidebar; decidir en diseño qué elemento vive dónde y **eliminar duplicados** — hoy el logo y el logout están en el sidebar):
- Logo GO + texto "Grupo Ortiz".
- Botón "Mi perfil" (avatar/iniciales + nombre del usuario logueado) que al click abre un **popover anclado al botón** (no un modal centrado) con: "Mi perfil" (→ `/perfil`) y "Cerrar sesión". Cierre por click fuera, Escape y al navegar. Accesible (focus trap ligero, `aria-expanded`).
- Botón de **cambio de tema** (R2) también en el header.

### R2. Modo oscuro / modo claro
- Toggle persistente (localStorage), **default: oscuro** (el actual). Sin flash de tema incorrecto al cargar (aplicar clase/atributo en `<html>` antes del primer paint).
- Estrategia: variables CSS por tema (`data-theme="dark|light"` sobre `:root`) — el tema claro deriva de la paleta de marca: fondos `#FFFFFF`/`#ECEBE0`, texto `#262626`, mismos naranjas GO; TODOS los componentes deben leer variables, no colores hardcodeados. Auditar estilos inline existentes (`style={{ background: "var(--go-dark-800)" }}` etc.) y refactorizar a variables semánticas (`--go-surface`, `--go-surface-raised`, `--go-text-primary`, ...).
- ApexCharts: `apexTheme.js` debe volverse theme-aware (colores de grid/labels/tooltip por tema) y los charts re-renderizar al cambiar tema. Respetar la regla crítica de no pasar `undefined` explícitos.
- Verificar contraste AA en ambos temas (texto sobre naranja, badges, tablas).

### R3. Responsividad total móvil
Auditoría y corrección de TODAS las vistas para ≥360px de ancho:
- Header + sidebar en móvil: definir patrón (p.ej. sidebar como drawer overlay con hamburguesa en el header, en vez del actual "siempre colapsado").
- Tablas (`Transacciones`, `Administración`, `Usuarios`, nuevas vistas): scroll horizontal contenido o transformación a cards en móvil — decidir por vista y ser consistente.
- Modales, formularios, popover del perfil, gráficas del dashboard (alturas/leyendas), paginación: usables con dedo, sin overflow roto.
- Criterio de aceptación: flujo completo por rol ejecutable en viewport 375×667 sin scroll horizontal de página.

### R4. Gestión de usuarios EXCLUSIVA del superadmin
- Cambio sobre lo actual: hoy `admin` puede gestionar usuarios `creador` — a partir de ahora **solo `superadmin`** ve y opera la gestión de usuarios (backend: endpoints `/api/users/*` → `require_role("superadmin")`; frontend: sección "Usuarios" y cualquier acceso ocultos para `admin`).
- Actualizar matriz de permisos en `doc/auth-arquitectura.md` y TODAS las pruebas afectadas.

### R5. Alcance del admin
`admin` ve y opera todo lo demás: dashboard global, creadores, marcas, transacciones de todos, administración de creadores/marcas, asignación de presupuestos (R7), validación de tickets (R10), PDF (R8). NO ve gestión de usuarios.

### R6. Alcance del creador (endurecer)
`creador` SOLO: su propia info (su presupuesto/ciclos, sus tickets con estados, su perfil) y subir sus propios tickets (que nacen pendientes, R10). Todo lo demás bloqueado (403/redirect y oculto del sidebar/header). Auditar fugas: endpoints de dashboard, listados, KPI, archivos de otros (IDOR), y las vistas nuevas de este paquete.

### R7. Presupuestos por periodo (semanal o mensual) — CAMBIO DE MODELO
Decisión ya tomada con el usuario: **renovación automática, SIN acumulación de sobrantes, con histórico de ciclos**.
- El admin configura por creador: monto del ciclo + periodicidad (`semanal` | `mensual`). Cada ciclo nuevo abre automáticamente con ese monto al terminar el anterior (implementación perezosa al consultar o job — diseñar y justificar; no depender de cron externo).
- El admin puede: cambiar monto/periodicidad (aplica a ciclos FUTUROS; diseñar si aplica al vigente con recálculo), ver estatus del ciclo vigente de cada creador (gastado/restante/% y días restantes) e histórico de ciclos pasados.
- Diseñar reglas explícitas y validarlas con el usuario en Fase 1: ¿a qué ciclo se carga un ticket aprobado a destiempo (por fecha del ticket vs fecha de aprobación)? ¿puede un ciclo cerrar en negativo? ¿qué pasa con tickets pendientes al cerrar el ciclo?
- **Migración**: los datos actuales (initial/spent/remaining acumulados + ~350 tickets históricos) deben mapearse a ciclos mensuales retroactivos coherentes, o congelarse como "histórico pre-ciclos" — proponer en diseño. Actualizar `seed.py`/`seed_demo_year.py`, KPIs del dashboard, `CreatorList`, modal de tickets (validación de fondos contra el ciclo vigente) y vista del creador.

### R8. Reporte PDF del dashboard
- Botón "Descargar PDF" en el dashboard (solo `admin`/`superadmin`): reporte del **mes actual** o de **mes(es) específico(s)** (selector). Decisión ya tomada: **visual CON gráficas** — KPIs + gráficas renderizadas + tablas de desglose por marca y por creador, con branding GO (logo, tipografías, naranja) y fecha de generación.
- Estrategia de generación (frontend html2canvas/jsPDF vs backend) a proponer en diseño con trade-offs; respetar el tema activo o forzar tema claro para impresión (recomendado: diseñar plantilla de impresión).

### R9. Prioridades de marcas
Decisión ya tomada: campo `priority` con niveles **Alta / Media / Baja** (default Media).
- Backend: columna + migración; editable en el CRUD de marcas (Administración).
- Frontend: badge visual por nivel (colores del design system), las marcas se ordenan por prioridad en selectores y listados, filtro por prioridad en Transacciones y en el desglose por marca del dashboard. Incluirlo en el PDF (R8).

### R10. Validación manual de tickets de creadores — CAMBIO DE FLUJO
Decisión ya tomada: **solo los tickets subidos por usuarios `creador` requieren validación**; los subidos por `admin`/`superadmin` se aprueban y descuentan automáticamente (flujo actual).
- Estados de ticket: `pendiente` | `aprobado` | `rechazado`. Un ticket `pendiente` NO descuenta presupuesto.
- Vista "Validación" para admin/superadmin: bandeja de pendientes con datos completos + visor del comprobante (R11) + acciones Aprobar / Rechazar (rechazo con motivo obligatorio). Aprobar descuenta transaccionalmente del ciclo correspondiente (R7) validando fondos; registrar en auditoría quién validó y cuándo.
- El creador ve el estado de sus tickets y el motivo de rechazo. Indicador de pendientes para el admin (badge con conteo en sidebar/header).
- **Migración**: tickets existentes → `aprobado`. Actualizar transacciones (columna/filtro de estado), dashboard (solo aprobados cuentan) y pruebas.

### R11. Visor de archivos multimedia in-app
- Ver comprobantes SIN descargar: lightbox/modal para imágenes (zoom básico) y visor embebido para PDF, desde Transacciones, la bandeja de Validación y la vista del creador.
- Debe usar el endpoint autenticado (`/api/tickets/file/{id}` con cookies) — nunca URLs públicas; respetar permisos (creador solo los suyos). Manejar archivos faltantes con mensaje claro.

---

## FASES DE TRABAJO

### Fase 0 — AUDITORÍA Y BASELINE
1. `git status` + revisar código de auth existente; correr `python -m pytest` (backend) y `npx vite build` (frontend); levantar la app y hacer smoke test por rol.
2. Si hay trabajo sin commitear: commit baseline en `dami-branch`.
3. Reportar estado real encontrado (qué existe, qué difiere de este documento).

### Fase 1 — DISEÑO (entregable; DETENTE y pide aprobación)
1. Modelo de datos: ciclos de presupuesto, estados de ticket, prioridad de marca (diagrama + migraciones idempotentes).
2. **Reglas de negocio de ciclos y validación** (las preguntas abiertas de R7/R10) — lista explícita de reglas propuestas para que el usuario apruebe o corrija.
3. Matriz de permisos actualizada (endpoint × rol) incluyendo los cambios R4-R6 y endpoints nuevos.
4. Arquitectura de temas (mapa de variables semánticas dark/light) y patrón responsive por vista (tabla→cards vs scroll).
5. Wireframes ligeros (texto/ASCII) de: header + popover, vista Validación, gestión de presupuestos, visor multimedia, selector del PDF.
6. Estrategia del PDF con trade-offs y dependencias exactas nuevas (mínimas, justificadas una por una).
7. Plan de commits por bloque.

### Fase 2 — IMPLEMENTACIÓN (tras aprobación; orden sugerido, un commit por bloque)
1. R4 permisos de usuarios solo-superadmin (pequeño, desbloquea matriz). 
2. R7 modelo de ciclos + migración + gestión en Administración + estatus.
3. R10 estados y flujo de validación + bandeja + auditoría.
4. R9 prioridades de marcas.
5. R11 visor multimedia (lo usa la bandeja de validación).
6. R1 header + popover de perfil (+ reorganización del sidebar).
7. R2 sistema de temas + refactor de estilos + charts theme-aware.
8. R3 pasada de responsividad completa.
9. R8 reporte PDF.
Después de CADA bloque: pruebas del bloque en verde + smoke E2E + reinicio en frío del backend si hubo cambios de backend.

### Fase 3 — PRUEBAS (obligatorio)
1. **pytest**: reglas de ciclos (apertura automática, sin rollover, carga de tickets a destiempo, fondos insuficientes al aprobar), flujo pendiente→aprobado/rechazado (incluye que pendiente no descuenta y rechazado nunca descuenta), matriz de permisos completa actualizada (R4-R6, IDOR de archivos y tickets), prioridades. Las ~90 pruebas existentes actualizadas y en verde.
2. **E2E Playwright**: flujo completo por rol — creador sube ticket (queda pendiente, no descuenta) → admin lo ve en Validación, abre el comprobante en el visor, rechaza con motivo → creador ve el rechazo → creador re-sube → admin aprueba → descuenta del ciclo vigente; admin asigna presupuesto semanal y ve estatus; superadmin gestiona usuarios (y admin NO puede); toggle de tema persiste; popover del perfil funciona; PDF se descarga con contenido; recorrido móvil 375px.
3. Reportar salida real de todas las suites.

### Fase 4 — DOCUMENTACIÓN
1. Actualizar `doc/auth-arquitectura.md` (matriz de permisos) y crear `doc/presupuestos-y-validacion.md` (reglas de negocio finales con ejemplos).
2. Actualizar `doc/auth-manual-usuario.md` con los flujos nuevos por rol (asignar presupuestos, validar tickets, tema, PDF).
3. Actualizar `CLAUDE.md` (reglas críticas nuevas: ciclos, estados de ticket, theming) y `.env.example` si hay variables nuevas.

---

## CRITERIOS DE ACEPTACIÓN

- [ ] Header global con logo + "Grupo Ortiz" + popover de perfil (Mi perfil / Cerrar sesión) anclado al botón, accesible y cerrable por click-fuera/Escape.
- [ ] Toggle oscuro/claro persistente, sin flash al cargar, charts y TODAS las vistas correctas en ambos temas (contraste AA).
- [ ] App completa usable a 375px por los 3 roles, sin scroll horizontal de página.
- [ ] Gestión de usuarios: solo superadmin (admin recibe 403 y no la ve; probado).
- [ ] Creador: solo su info y subir sus tickets; todo lo demás bloqueado (probado, incluido IDOR).
- [ ] Presupuestos por creador con periodicidad semanal/mensual, renovación automática sin rollover, estatus del ciclo vigente e histórico; admin los administra; migración de datos existentes coherente.
- [ ] Ticket de creador nace pendiente y NO descuenta; aprobar descuenta transaccionalmente del ciclo correcto; rechazar exige motivo visible al creador; tickets de admin se auto-aprueban; auditoría de validaciones.
- [ ] Marcas con prioridad Alta/Media/Baja: badge, orden en selectores, filtro en transacciones y dashboard.
- [ ] Botón PDF (admin/superadmin) del mes actual o meses específicos, con KPIs + gráficas + tablas y branding GO.
- [ ] Visor in-app de imágenes y PDFs vía endpoint autenticado, con permisos respetados.
- [ ] pytest completo en verde (existentes actualizadas + nuevas) y E2E Playwright por rol en verde, con evidencia real.
- [ ] `npx vite build` limpio; documentación de Fase 4 completa; commits atómicos en `dami-branch`.

---

## FORMATO DE TRABAJO

- Idioma: **español** en UI, mensajes, commits y entregables.
- Fase 0 y Fase 1 son obligatorias; **no escribas código de features sin aprobación del diseño de Fase 1** (en particular las reglas de negocio de R7/R10).
- Si el estado real del código contradice este documento, repórtalo en Fase 0 antes de continuar.
- Enumera tus supuestos; ante ambigüedad nueva, pregunta antes de implementar.
- Al final de cada fase: resumen de lo hecho, evidencia de pruebas, pendientes y commits creados.
