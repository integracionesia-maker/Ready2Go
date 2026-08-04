# Avances Diarios — GOCreate (Presupuestos + Control de Equipos)

> Owner: Damian (marketing) · Supervision: Jose Aguilar
> Inicio de seguimiento: 2026-07-15

---

## Semana 32 — Agosto 2026

### MAR 04/08 — Renombre a GOCreate

**Que hice:**
- Cambio de nombre del proyecto: **Ready2Go** → **GOCreate**. Actualizadas las menciones de marca en los documentos de la raiz (`CLAUDE.md`, `status.md`, `context.md`, `RISKS.md`, `BACKLOG.md`, `MVP_BREAKDOWN.md`, `CHANGELOG.md`), en `docs/`, en el frontend (`LoginPage.jsx`, `Header.jsx`, `<title>` de `index.html`) y en el backend (plantillas de correo, PDF de responsiva, logger, `.env.example`).
- El repo de GitHub **no** se renombro: sigue en `github.com/integracionesia-maker/Ready2Go` (decision explicita para no romper los remotes de Jose/`jose-branch` y Beni/`BeniBranch` sin coordinar primero). Las referencias textuales a esa URL se dejaron intactas.
- Historial de nombres del proyecto: `presupuesto_creadores` → `Ready2Go` (27/07/2026) → `GOCreate` (04/08/2026).

**Evidencia:**
- `git diff` de la raiz, `frontend/`, `docs/` y `backend/` con las menciones de marca actualizadas.

**MVP:** sin cambio (renombre de marca, no afecta entregables).

**Bloqueo:** ninguno.

**Siguiente:** seguir con lo que estaba en curso antes del renombre (WP1 del modulo Equipos en espera de luz verde).

**Semaforo:** Verde

---

## Semana 31 — Julio 2026

### LUN 27/07 — Renombre a Ready2Go + plan quirurgico del modulo Control de Equipos

**Que hice:**
- Reunion con marketing (Emily Perez, Betzabet Fuentes): pidieron plataforma para el control de prestamo de equipo de grabacion, con carta responsiva firmada, fotos del equipo, y autorizacion de Melisa. Traian una maqueta HTML con localStorage.
- Repo renombrado: remote reapuntado de `presupuesto_creadores` a `Ready2Go` (misma org, `integracionesia-maker`), carpeta local renombrada, rama `jose-branch` creada y publicada.
- Actualice las referencias del pool: `OWNERS.md`, `context_proyectos.md`, `playbook_registry.json`, `observatorio/collector/repo_map.py`.
- Escribi el plan quirurgico completo del modulo nuevo: RBAC aditivo (patron de roles base + paquetes, deny-by-default, 503 en fallo de resolucion), modelo de 11 tablas, maquina de estados del prestamo, 24 endpoints, PDF de responsiva en servidor versionado con hash, notificaciones SMTP con log idempotente y reintentos, y direccion visual liquid glass para toda la app.
- Pasada adversarial sobre la maqueta y el codigo existente: 22 hallazgos (5 criticos) mitigados en el diseno antes de escribir una linea. Los criticos: doble fuente de verdad de disponibilidad, mismo equipo en dos prestamos abiertos, IDOR en fotos y PDF, aprobacion sin auth (en la maqueta cualquiera elige "Melisa" en un select), y colision de folio.
- Actualice los 6 archivos de framework + cree `CHANGELOG.md` (no existia).

**Evidencia:**
- `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md`
- `docs/maqueta/CONTROL_DE_EQUIPOS_maqueta_mkt.htm` (especificacion funcional de marketing)
- `git remote -v` → `github.com/integracionesia-maker/Ready2Go`; `jose-branch` publicada
- `CLAUDE.md`, `context.md`, `status.md`, `BACKLOG.md`, `RISKS.md`, `MVP_BREAKDOWN.md`, `DESIGN_SYSTEM.md`, `CHANGELOG.md`

**MVP:** 40% (10/25 — el denominador crecio al absorber el modulo nuevo; el modulo Presupuestos por si solo va en 77%)

**Bloqueo:** esperando luz verde de Jose para construir. De marketing faltan: usuarios+correos del area, inventario de camaras/luces/tripies, razon social emisora de la responsiva, nombre de dominio y aprobacion firmada del gasto del dominio.

**Siguiente:** con luz verde, WP1 (RBAC aditivo) — pruebas primero, luego motor, luego migracion idempotente.

**Semaforo:** Verde

---

## Semana 29 — Julio 2026

### MIE 15/07 — Debug critico + poblado de datos + fusion de duplicados + setup de framework

**Que hice:**
- Diagnostique y corregi el error fatal "Invalid hook call" / React duplicado en el frontend — causado por un alias manual de `react`/`react-dom` en `vite.config.js` que rompia la resolucion de modulos de Vite (no habia ninguna copia duplicada real de React en disco)
- Reinstale `node_modules` limpio, mate procesos zombie en puertos 5173/8000, levante backend y frontend correctamente (el comando documentado de arranque del backend asumia el cwd incorrecto)
- Instale Playwright + Chromium para verificar el dashboard en un navegador real (no habia herramienta de browser disponible) — confirme 0 errores de consola
- Encontre y corregi un segundo bug real: `createApexOptions` asignaba `undefined` explicito a `stroke`/`fill`/`plotOptions`/`responsive`, lo que rompia los defaults internos de ApexCharts 5.x y crasheaba el dashboard completo (pantalla en blanco, sin error boundary)
- Genere 78 tickets adicionales distribuidos en 12 meses de historial (`seed_more_months.py`) para poblar el dashboard con datos representativos
- Detecte y fusione creadores/marcas duplicados por variantes con/sin acento (Mariana Lopez/López, Diego Fernandez/Fernández, Sofia/Sofía Herrera, L'Oreal/L'Oréal) — reasigne tickets al registro canonico y corregi `seed.py` para no reintroducir el duplicado en un futuro reseed
- La fusion dejo 3 creadores con presupuesto negativo (cada duplicado habia acumulado gasto por separado contra el mismo presupuesto); recorte los tickets de relleno mas grandes hasta volver a presupuesto positivo, con confirmacion del usuario sobre el criterio a aplicar
- Encontre y corregi un bug preexistente en el backend: el KPI "Marcas Activas" mostraba 89 (contaba filas del JOIN) en vez de 8 (marcas distintas reales)
- Identifique y elimine procesos backend "zombie" (workers huerfanos que sobrevivian a la muerte de su proceso padre y seguian sirviendo codigo desactualizado)

**Evidencia:**
- `vite.config.js` — alias manual eliminado
- `frontend/src/components/charts/apexTheme.js` — claves opcionales condicionales
- `backend/seed_more_months.py`, `merge_duplicates.py`, `trim_overbudget.py` — scripts de datos
- `backend/app/crud.py::get_dashboard_summary` — fix `func.distinct`
- Screenshots Playwright (dashboard completo, 4 graficos, 0 errores de consola)
- `GET /api/dashboard/summary` → `active_brands: 8` (antes: 89)

**MVP:** 67% (8/12 entregables — ver `MVP_BREAKDOWN.md`)

**Bloqueo:** ninguno

**Siguiente:** inicializar git (repo sin control de versiones hoy es el gap mas urgente)

**Semaforo:** Verde

### LUN 27/07 (tarde) — Integracion a master, contrato de API v1 y arranque de los dos carriles

**Que hice:**
- Integre `jose-branch` a master con `--no-ff` siguiendo el protocolo del pool: lock tomado, 4 tags `pre-integracion` y bundle pusheados antes de tocar nada, precheck de divergencia en las dos direcciones por rama.
- Verifique que `dami-branch` y `BeniBranch` no tenian trabajo propio sin integrar: las dos estaban exactamente en el mismo commit que master. Lo unico que subio fue el plan.
- Borre la rama remota basura `origin` (cero commits propios, respaldada con tag y bundle antes). De paso diagnostique por que rompia el loop de integracion: `%(refname:short)` acorta `refs/remotes/origin/HEAD` a `origin`, no a `HEAD`.
- Parti el trabajo en dos carriles con **interseccion de codigo cero**: la frontera es el contrato HTTP, no un archivo. De 47 archivos que se habrian disputado, 41 quedan con dueno unico por pertenencia de capa.
- Escribi y publique el **contrato de API v1 congelado** en `docs/contratos/`: 24 endpoints, catalogo de permisos, forma de `/auth/me`, tokens de marca para el PDF, y fixtures con los codigos de error feos, no solo el camino feliz.
- Replique master a las tres ramas con FF puro y sembre en cada una **solo su** documento de asignacion, con el mismo nombre de archivo y el mismo mensaje de commit para que ni la forma delate el reparto.
- Doble loop de cero perdida en verde y lock liberado.

**Evidencia:**
- master `865a81b` (plan + contrato) · `dami-branch` `d735723` · `BeniBranch` `281f10b` · `jose-branch` `865a81b`
- `docs/contratos/` (7 archivos) · `docs/ASIGNACION_EQUIPOS.md` en cada rama de trabajo
- Loop 1: los 4 tags `pre-integracion` sin un solo commit fuera de master. Loop 2: cada rama sobra exactamente su propia asignacion.

**MVP:** 40% (10/25). Sin cambio: hoy no se cerro ningun entregable de construccion.

**Bloqueo:** ninguno. Los dos carriles pueden trabajar desde hoy sin depender uno del otro ni de pendientes de marketing.

**Siguiente:** cada carril arranca por su tarea 0 (mecanica, aislada). Generar y congelar `openapi_equipos_v1.json` cuando existan los primeros endpoints.

**Semaforo:** Verde

---

## Historial de semaforos

| Semana | Semaforo | Bloqueo principal |
|---|---|---|
| Sem 29 (15 Jul 2026) | Verde | ninguno |
| Sem 31 (27 Jul 2026) | Verde | luz verde de build del modulo Equipos |
