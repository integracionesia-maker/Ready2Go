# Avances Diarios — Ready2Go (Presupuestos + Control de Equipos)

> Owner: Damian (marketing) · Supervision: Jose Aguilar
> Inicio de seguimiento: 2026-07-15

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

---

## Historial de semaforos

| Semana | Semaforo | Bloqueo principal |
|---|---|---|
| Sem 29 (15 Jul 2026) | Verde | ninguno |
| Sem 31 (27 Jul 2026) | Verde | luz verde de build del modulo Equipos |
