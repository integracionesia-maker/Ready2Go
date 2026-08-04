# RISKS — GOCreate (Presupuestos + Control de Equipos)

> Registro de riesgos activos y cerrados del sistema.
> Los riesgos del modulo Control de Equipos que ya estan **mitigados en el diseno** (22 hallazgos adversariales) viven en §10 de `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md`. Aqui solo los que siguen abiertos como riesgo real del proyecto.

---

## Activos

| # | Riesgo | Severidad | Fecha | Impacto | Mitigacion |
|---|---|---|---|---|---|
| 3 | Sin backups de `presupuesto.db` **ni de `uploads/`** (SQLite es un solo archivo; `uploads/` guardara las cartas responsivas firmadas) | **Alto** | 2026-07-15 (elevado 2026-07-27) | Corrupcion o borrado accidental = perdida total de presupuestos y de documentos firmados que son evidencia | Script de backup diario de DB + `uploads/`; ver BACKLOG #3 |
| 9 | El modulo de Equipos **no sirve en `127.0.0.1`**: los colaboradores lo usan desde su celular (fotos con la camara, firma con el dedo) | Alto | 2026-07-27 | Sin dominio + HTTPS el modulo no se puede pilotear; ademas `getUserMedia`/camara exige contexto seguro | Dominio + TLS antes del piloto (WP9); depende de T4/T5 del BACKLOG |
| 10 | Firma en canvas no es firma electronica avanzada | Medio | 2026-07-27 | Si RH o legal esperan valor probatorio pleno, la responsiva digital no lo da: es evidencia razonable (firma + fotos + hash + bitacora + copia por correo), no prueba irrefutable | Declararlo por escrito ante el area antes del piloto. Si se necesita valor legal pleno, es otro proyecto (e.firma/PSC) |
| 11 | Alcance del proyecto duplicado sin owner tecnico dedicado al modulo nuevo | Medio | 2026-07-27 | Damian (owner) esta en marketing y ademas es sup de otro proyecto; el modulo de Equipos son 9 paquetes de trabajo | Definir quien construye antes de dar luz verde; el plan esta ordenado para poder repartir por WP |
| 12 | Rendimiento del liquid glass en Mac mini y en celular | Medio | 2026-07-27 | Cada superficie de cristal reserva GPU y compositing; mal usado deja la app con jank justo en el dispositivo del usuario final | Presupuesto de 3-4 superficies, prohibido en tablas/scroll, `@supports` para la refraccion SVG (solo Chromium), medicion en el dispositivo real antes de cerrar WP7/WP8 |
| 4 | Sin tests automatizados end-to-end del resto de la app (creadores/marcas/tickets) | Medio | 2026-07-15 | Cambios pueden romper el calculo de presupuestos sin detectarse — ya casi ocurre hoy al fusionar duplicados (ver "Cerrados" #3). La suite pytest agregada junto con auth (ver "Cerrados" #6) no cubre CRUD de creadores/marcas/tickets en si, solo permisos | Tests basicos de CRUD + calculo de presupuesto; ver BACKLOG #4 |
| 7 | Sin HTTPS/CSP/HSTS (residual de #2, ver "Cerrados" #6) | Medio | 2026-07-16 | Las cookies de sesion viajan sin `Secure` en `ENV=development`; sin CSP/HSTS un XSS o downgrade a HTTP son mas peligrosos | Agregar HTTPS + esas cabeceras antes de exponer fuera de `127.0.0.1`; ver `doc/auth-arquitectura.md` §6 |
| 8 | Rate limiting de login por IP vive en memoria de un solo proceso | Bajo | 2026-07-16 | Se reinicia si el proceso se reinicia; no protege si se escala a multiples workers/instancias | Mover a un almacen compartido (Redis u otro) si se escala horizontalmente; ver `doc/auth-arquitectura.md` §6 |

## Cerrados

| # | Riesgo | Fecha cerrado | Como se resolvio |
|---|---|---|---|
| 1 | Dashboard roto por error "Invalid hook call" (React duplicado) | 2026-07-15 | Alias manual de `react`/`react-dom` en `vite.config.js` eliminado; `resolve.dedupe` + `optimizeDeps.include` es suficiente |
| 2 | Dashboard completo crasheaba (pantalla en blanco) al agregar graficos ApexCharts | 2026-07-15 | `createApexOptions` ya no asigna `stroke`/`fill`/`plotOptions`/`responsive` como `undefined` explicito |
| 3 | Creadores/marcas duplicados por variantes con/sin acento generaron sobregiro (3 creadores con presupuesto negativo tras fusion) | 2026-07-15 | Tickets de relleno mas grandes recortados hasta volver a presupuesto positivo; `seed.py` corregido para no reintroducir el duplicado |
| 4 | KPI "Marcas Activas" mostraba 89 en vez de 8 (contaba filas del JOIN, no marcas distintas) | 2026-07-15 | `func.count(func.distinct(models.Brand.id))` + `join` en vez de `outerjoin` sin agrupar |
| 5 | Procesos backend "zombie" (workers huerfanos) servian codigo desactualizado tras reinicios | 2026-07-15 | Identificados y eliminados via `Get-CimInstance Win32_Process` (parent_pid muerto); backend reiniciado limpio |
| 6 | Sin autenticacion en la API (`main.py` solo tenia CORS, sin login/roles) | 2026-07-16 | Sistema completo de auth: cookies httpOnly (JWT access + refresh con rotacion), 3 roles con matriz de permisos por endpoint, bloqueo incremental + rate limit de login, IDOR de comprobantes corregido. 90 pruebas pytest + 5 E2E Playwright en verde. Ver `doc/auth-arquitectura.md`. Quedan riesgos residuales menores, ver Activos #7 y #8 |
| 7 | Sin control de versiones (la carpeta no era repo git) | 2026-07-17 | Repo inicializado; hoy en `github.com/integracionesia-maker/Ready2Go` con ramas por persona |
| 8 | Owner del proyecto no confirmado en la documentacion | 2026-07-17 | Damian = owner (marketing), Jose = supervision. Registrado en `OWNERS.md` del pool |
| 9 | Tipografia de marca no formalizada (Space Grotesk/Inter en vez de Blauer Nue/Conthic) | 2026-07-27 | Decidido: Blauer Nue (display) + Conthic (cuerpo) + JetBrains Mono (cifras), autohospedadas. Se implementa en WP7 |

## Top 3 para direccion

1. **Sin dominio + HTTPS el modulo de Equipos no se puede pilotear** — los colaboradores lo usan desde el celular. Requiere el nombre de dominio y la aprobacion del gasto (~11 USD/ano).
2. **Sin backups de DB ni de `uploads/`** — con Equipos, `uploads/` guarda cartas responsivas firmadas. Un disco corrupto borra evidencia.
3. **Quien construye el modulo nuevo** — 9 paquetes de trabajo sin owner tecnico dedicado asignado todavia.
