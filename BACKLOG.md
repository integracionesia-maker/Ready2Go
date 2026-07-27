# BACKLOG — Ready2Go (Presupuestos + Control de Equipos)

> Plataforma interna del area de marketing de Grupo Ortiz. Dos modulos, una app.
> Fase actual: **3.5 Planeacion Quirurgica** (modulo Control de Equipos) · Presupuestos en Fase 5.
> Plan de referencia: `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md`

---

## Bloqueado por decision

| # | Tarea | Fase | Prioridad | Bloqueado por |
|---|---|---|---|---|
| 0 | **Luz verde de build del modulo Control de Equipos** | 3.5 | Critica | Jose — revision del plan quirurgico |

## Pendientes de terceros (marketing)

| # | Tarea | De quien | Bloquea |
|---|---|---|---|
| T1 | Tabla de nombres + correos GO del area de marketing | Emily | Alta de usuarios (WP1) / piloto |
| T2 | Inventario de camaras, luces y tripies con nombre completo | Emily / Betzabet | Seed de inventario (WP2) |
| T3 | Confirmar razon social emisora de la carta responsiva | Marketing / RH | PDF (WP5) |
| T4 | Nombre de dominio deseado | Emily / Melisa | Deploy (WP9) |
| T5 | Aprobacion firmada del costo del dominio (~11 USD/ano) | Melisa | Deploy (WP9) |
| T6 | Credenciales de la cuenta SMTP emisora | Jose / Sistemas | Notificaciones (WP6) |
| T7 | Fuentes Blauer Nue / Conthic en woff2 | `context_desing_go` | Shell visual (WP7) |

## Pendientes — modulo Control de Equipos (por WP del plan)

| # | Tarea | WP | Fase | Prioridad | Estado |
|---|---|---|---|---|---|
| E1 | RBAC aditivo: 3 tablas + motor `rbac.py` + `require_perm` + permisos en `/auth/me` + migracion idempotente | WP1 | 5 | Alta | Pendiente |
| E2 | Pruebas de RBAC: set efectivo por combinacion de roles, 503 en fallo de DB, `APROBADOR_EQUIPO` sin acceso a presupuestos | WP1 | 5 | Alta | Pendiente |
| E3 | Modelo de datos de equipos: 11 tablas, indice unico parcial de disponibilidad, `folio_counter`, `empresa` | WP2 | 5 | Alta | Pendiente |
| E4 | Seed del inventario auditado (8 equipos del 10/06) + 2 razones sociales | WP2 | 5 | Alta | Pendiente |
| E5 | API inventario + auditorias de condicion + ficha con historial | WP3 | 5 | Alta | Pendiente |
| E6 | API prestamos: borrador, items (409 si ocupado), media, confirmar, cancelar, devolucion, historial, export CSV | WP4 | 5 | Alta | Pendiente |
| E7 | API aprobacion: autorizar entrega, confirmar devolucion por equipo, cerrar incidencia | WP4 | 5 | Alta | Pendiente |
| E8 | Carta responsiva PDF en servidor (reportlab) + versionado + hash | WP5 | 5 | Alta | Pendiente |
| E9 | Mailer SMTP + `notification_log` idempotente + reintentos | WP6 | 5 | Alta | Pendiente |
| E10 | Recordatorio diario de prestamos vencidos (LaunchAgent, no cron en uvicorn) | WP6 | 5 | Media | Pendiente |
| E11 | Shell liquid glass: tokens, primitivas, fuentes de marca, `motion`, dark/light | WP7 | 5 | Alta | Pendiente |
| E12 | Migracion visual de las vistas de Presupuestos al shell nuevo (sin tocar logica) | WP7 | 5 | Media | Pendiente |
| E13 | Frontend inventario (busqueda, filtros, ficha, alta/edicion, auditoria) | WP8 | 5 | Alta | Pendiente |
| E14 | Frontend nuevo prestamo (wizard 4 pasos + `SignaturePad` + `PhotoCapture`) | WP8 | 5 | Alta | Pendiente |
| E15 | Frontend activos + aprobaciones + historial + ficha de prestamo con bitacora | WP8 | 5 | Alta | Pendiente |
| E16 | Dashboard de equipos (KPIs, requiere atencion, distribucion de estados) | WP8 | 5 | Media | Pendiente |
| E17 | e2e Playwright del flujo completo (solicitar → firmar → autorizar → devolver → confirmar) | WP8 | 6 | Alta | Pendiente |

## Pendientes — modulo Presupuestos y transversales

| # | Tarea | Fase | Prioridad | Estado |
|---|---|---|---|---|
| 3 | Backups automaticos de `presupuesto.db` **y de `uploads/`** (ahora guardara responsivas firmadas) | 5 | Alta | Pendiente |
| 4 | Tests de CRUD de creadores/marcas (la suite actual cubre permisos y calculo, no CRUD puro) | 6 | Media | Pendiente |
| 5 | Crear `SECURITY.md` con checklist formal | 6 | Media | Pendiente |
| 8 | HTTPS + CSP + HSTS + revision de `CORS_ORIGINS` antes de exponer fuera de `127.0.0.1` | 6 | Alta | Pendiente |
| 9 | Auditoria `/cyber-neo` del modulo nuevo antes de piloto | 6 | Alta | Pendiente |
| 10 | Dominio + deploy en Mac mini segun `doc/deploy-runbook.md` | 8 | Alta | Pendiente |
| 11 | Rate limit de login en almacen compartido si se escala a varios workers | 8 | Baja | Pendiente |

## En progreso

_Ninguna. El modulo Equipos espera luz verde; Presupuestos sin cambios esta semana._

## Completados (recientes)

| # | Tarea | Fase | Completado | Evidencia |
|---|---|---|---|---|
| 12 | Plan quirurgico de integracion de Control de Equipos (RBAC aditivo, modelo de datos, PDF, correo, liquid glass, 22 hallazgos adversariales) | 3.5 | 27 Jul 2026 | `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` |
| 13 | Repo renombrado a Ready2Go, remote reapuntado, `jose-branch` creada, referencias del pool actualizadas | 3.5 | 27 Jul 2026 | `git remote -v` → `integracionesia-maker/Ready2Go`; OWNERS.md, context_proyectos.md, playbook_registry.json |
| 14 | Decision de tipografia de marca (Blauer Nue + Conthic + JetBrains Mono) — cierra pendiente historico #7 | 3.5 | 27 Jul 2026 | `DESIGN_SYSTEM.md` |
| 1 | Inicializar repo git | 5 | 17 Jul 2026 | Historial real en `master` |
| 2 | Autenticacion / control de acceso en la API | 5 | 17 Jul 2026 | `doc/auth-arquitectura.md`, 167 pruebas |
| 6 | Confirmar owner del proyecto (Damian, supervision Jose) | 5 | 17 Jul 2026 | `OWNERS.md` raiz del pool |
| 7 | Responsividad movil completa (320px, `RowActions`, scroll de tablas) | 5 | 23 Jul 2026 | `doc/responsividad-movil.md` |
| 8 | Gastos generales + borrado logico/fisico de tickets (R12) | 5 | 23 Jul 2026 | `doc/gastos-generales-manual.md`, `doc/borrado-tickets.md` |
