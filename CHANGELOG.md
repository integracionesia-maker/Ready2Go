# CHANGELOG — Ready2Go

Registro de cambios del proyecto. Formato: `Agregado` / `Actualizado` / `Eliminado` / `Corregido`.

---

## 2026-07-27 — Renombre a Ready2Go + plan de integracion de Control de Equipos (Fase 3.5)

### Agregado
- `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` — plan quirurgico completo del modulo Control de Prestamo de Equipo: contexto de la reunion con marketing, decisiones tomadas, RBAC aditivo (3 tablas + motor deny-by-default), modelo de datos de 11 tablas, maquina de estados del prestamo, API nueva (24 endpoints), PDF de responsiva en servidor versionado, notificaciones SMTP con log idempotente, direccion visual liquid glass, 22 hallazgos de revision adversarial, plan de trabajo en 9 paquetes, verificacion y rollback.
- `docs/maqueta/CONTROL_DE_EQUIPOS_maqueta_mkt.htm` — maqueta HTML de marketing como especificacion funcional de referencia (su implementacion no se porta: localStorage, `mailto:`, HTML renderizado en el estado, importar/borrar todo desde la UI).
- `CHANGELOG.md` — este archivo (faltaba).
- Rama `jose-branch` para supervision de Jose.

### Actualizado
- Remote de git: `integracionesia-maker/presupuesto_creadores` → **`integracionesia-maker/Ready2Go`**. Carpeta local renombrada a `Ready2Go`.
- `CLAUDE.md` — nombre, alcance de dos modulos, politica de ramas por persona, regla de roles aditivos, decision de tipografia, direccion visual y sus limites.
- `context.md` — reescrito: dos modulos, tabla de fases por modulo, usuarios y roles (incluido `colaborador_mkt` y los aditivos), proceso objetivo de prestamo, dependencias de terceros.
- `status.md` — Fase 3.5, owner Damian, metricas reales (167 pruebas, 3 suites e2e, git si), metricas de impacto esperadas del modulo nuevo, bloqueo = luz verde de build.
- `MVP_BREAKDOWN.md` — dividido en modulo A (Presupuestos, 10/13 = 77%) y modulo B (Equipos, 0/12). Total 10/25 = **40%**. El porcentaje baja porque el alcance crecio.
- `BACKLOG.md` — 17 tareas nuevas del modulo Equipos ordenadas por paquete de trabajo, 7 pendientes de terceros, cierre de los pendientes historicos ya resueltos (git, auth, owner, responsividad, R12).
- `RISKS.md` — cerrados 3 riesgos obsoletos (sin git, owner sin confirmar, tipografia sin decidir); elevado el de backups (ahora `uploads/` guardara responsivas firmadas); 4 riesgos nuevos (el modulo no sirve en localhost, firma en canvas no es firma avanzada, alcance duplicado sin owner tecnico, rendimiento del cristal).
- `DESIGN_SYSTEM.md` — direccion liquid glass con receta CSS unica, 7 reglas duras (incluido que el SVG `backdrop-filter` es solo Chromium y que el cristal esta prohibido en tablas y scroll), tipografia oficial de marca decidida, componentes del sistema, presupuesto de rendimiento y registro de decisiones.

### Decisiones
- Arquitectura: **misma app FastAPI, misma DB SQLite, tablas nuevas** (descartado: DB aparte, servicio aparte).
- Roles: **aditivos** (patron portado de la implementacion de RBAC granular de otro proyecto del pool) — `users.role` sigue siendo el rol base.
- Notificaciones: **correo SMTP corporativo** (descartado WhatsApp por costo de API de Meta; Telegram y Resend por piezas extra que administrar).
- Responsiva: **PDF generado en servidor** (reportlab) y adjunto al correo, versionado y con hash; nunca se sobrescribe.
- Frontend: **100% React**, liquid glass en toda la app, React 18.3.1 (no se salta a 19 en esta entrega).

### Nota de proceso
La pasada adversarial del plan la hizo el agente principal por enumeracion, no tres agentes independientes en paralelo como pide el framework (fan-out deshabilitado en la sesion). Queda declarado en §10 del plan.

---

## 2026-07-23 — Responsividad movil + gastos generales vinculados a marca (R12.1)

### Agregado
- Responsividad movil completa: tablas, KPIs, graficas, modales y navegacion usables desde 320px. `hooks/useMobile.js`, `components/RowActions.jsx`, clases `go-table-scroll-wrapper`/`go-table-scroll`. Ver `doc/responsividad-movil.md`.
- Gastos generales vinculados a la tabla de marcas.

---

## 2026-07-17 — Autenticacion, roles, ciclos de presupuesto y validacion de tickets

### Agregado
- Sistema de autenticacion: JWT en cookie httpOnly + refresh token con rotacion, bloqueo incremental y rate limit de login, 3 roles con matriz de permisos por endpoint. Ver `doc/auth-arquitectura.md`.
- Ciclos de presupuesto semanal/mensual (snapshot inmutable), validacion de tickets (`pendiente → aprobado/rechazado`), prioridad de marcas. Ver `doc/presupuestos-y-validacion.md`.
- Gastos generales y borrado logico/fisico de tickets con reversion de ciclo (R12). Ver `doc/gastos-generales-manual.md`, `doc/borrado-tickets.md`.
- Repo git inicializado.

### Corregido
- IDOR en descarga de comprobantes: `GET /api/tickets/file/{id}` ahora responde 403 si el ticket no es del creador autenticado.
- `/uploads` como mount estatico eliminado: todo archivo se sirve por endpoint autenticado.

---

## 2026-07-15 — Estabilizacion del dashboard y limpieza de datos

### Corregido
- "Invalid hook call" por React duplicado: alias manual de `react`/`react-dom` eliminado de `vite.config.js`.
- Crash de ApexCharts por claves `undefined` explicitas en `createApexOptions`.
- KPI "Marcas Activas" mostraba 89 en vez de 8 (contaba filas del JOIN).
- Sobregiro de 3 creadores tras fusionar duplicados por acentos.

### Agregado
- 12 meses de historial de tickets de prueba; `seed.py` corregido para no reintroducir duplicados por acentos.
