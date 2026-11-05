# RISKS — GOCreate (Presupuestos + Control de Equipos)

> Registro de riesgos activos y cerrados del sistema.
> Los riesgos del modulo Control de Equipos que ya estan **mitigados en el diseno** (22 hallazgos adversariales) viven en §10 de `docs/equipos/plan-quirurgico.md`. Aqui solo los que siguen abiertos como riesgo real del proyecto. Puesto al dia el 2026-11-05; el detalle tecnico esta en `SECURITY.md`.

---

## Activos

| # | Riesgo | Severidad | Fecha | Impacto | Mitigacion |
|---|---|---|---|---|---|
| 3 | Respaldos de `presupuesto.db` y `uploads/` solo al desplegar (7 copias, misma maquina, sin cifrar, sin tarea programada) | **Alto** | 2026-07-15 (actualizado 2026-11-05) | Disco corrupto o borrado entre deploys = perdida de presupuestos y de cartas responsivas firmadas (evidencia) | Respaldo programado y copia fuera de la Mac; BACKLOG #3. Hoy: `docs/deploy/deploy-app.sh` |
| 10 | Firma en canvas no es firma electronica avanzada | Medio | 2026-07-27 | Si RH o legal esperan valor probatorio pleno, la responsiva digital no lo da: es evidencia razonable (firma + fotos + hash + bitacora + copia por correo), no prueba irrefutable. La huella sha256 se guarda pero ningun endpoint la recalcula al servir | Declararlo por escrito ante el area. Si se necesita valor legal pleno, es otro proyecto (e.firma/PSC). Confirmar con Damian si ya se hizo |
| 11 | Sin owner tecnico dedicado al modulo de Equipos | Medio | 2026-07-27 | Damian (owner) esta en marketing y supervisa otro proyecto; el modulo ya esta construido y operando | Por confirmar con Damian quien lo mantiene |
| 12 | Rendimiento del liquid glass en Mac mini y en celular | Medio | 2026-07-27 | Mal usado deja la app con jank en el dispositivo del usuario final | Presupuesto de superficies y medicion en dispositivo real; no hay registro de medicion en el repo (Por confirmar) |
| 4 | Cobertura de CRUD puro de creadores/marcas | Medio | 2026-07-15 | La suite (786 funciones) cubre permisos, ciclos, validacion, borrado y Equipos; el CRUD puro sigue sin cubrirse | Tests basicos de CRUD; BACKLOG #4 |
| 7 | Sin cabeceras de seguridad (CSP, HSTS, `nosniff`, `X-Frame-Options`) en la app | Medio | 2026-07-16 (actualizado 2026-11-05) | HTTPS y `Secure` ya existen en produccion (`ENV=production`, Cloudflare); sin CSP/HSTS un XSS o un downgrade son mas peligrosos. Que pone el borde: Por confirmar | Middleware o regla en el borde; BACKLOG #8; `SECURITY.md` gap 1 |
| 8 | Limite de intentos de login por IP en memoria de un proceso, cuenta tambien los exitosos | Bajo | 2026-07-16 | Se reinicia con el proceso; no protege con varios workers; detras del tunel falta confirmar que IP ve el backend | Almacen compartido si se escala; BACKLOG #11 |
| 13 | Comprobantes de ticket validados solo por extension y MIME declarado; archivo leido completo a memoria antes del tope | Medio | 2026-08-18 (reverificado 2026-11-05) | Contenido falso como comprobante; consumo de memoria con archivos enormes | Portar la validacion por firma de bytes de `media_manager.py`; BACKLOG #13 |
| 14 | `must_change_password` solo lo exige la pantalla | Medio | 2026-08-18 (reverificado 2026-11-05) | Una contrasena temporal sirve por API indefinidamente | Exigirlo en el backend; BACKLOG #14 |
| 15 | Datos personales reales en el repo (`seed_usuarios_mkt.py`) y copias de la base sin ignorar por git (`presupuesto.db.bak-*`) | Medio | 2026-11-05 | Fuga o commit accidental de datos y hashes | `.gitignore` y saneo; BACKLOG #17 |
| 16 | Aviso de correo sin confirmar en produccion y recordatorio de vencidos retirado (14/09/26) | Medio | 2026-11-05 | Prestamos vencidos sin aviso; la aprobadora puede no enterarse de una autorizacion pendiente | Confirmar `NOTIF_ENABLED`/SMTP con Damian; decidir si se reabre E10 |
| 17 | Paquete `ADMIN_USUARIOS` aun no sembrado en produccion | Bajo | 2026-10-19 | La delegacion de cuentas no funciona hasta correr la migracion | `migrate_rbac_aditivo.py`; BACKLOG #15 |

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
| 9 | Tipografia de marca no formalizada (Space Grotesk/Inter en vez de Blauer Nue/Conthic) | 2026-07-27 | Decidido: Blauer Nue (display) + Conthic (cuerpo) + JetBrains Mono (cifras), autohospedadas. **Los woff2 siguen sin cargarse** (BACKLOG T7) |
| 9 (activo) | Equipos no servia en `127.0.0.1` (camara y firma desde el celular exigen contexto seguro) | 2026-11-05 | Produccion en `https://gocreate.mx` con HTTPS de Cloudflare (`docs/deploy/`). Se cierra por evidencia del repo; usabilidad en celular Por confirmar |
| 11 (activo, ex-alcance) | Alcance duplicado sin quien construya el modulo nuevo | 2026-11-05 | El modulo se construyo (ver `MVP_BREAKDOWN.md`); queda abierto solo el dueno tecnico (#11) |

## Top 3 para direccion (05/11/26)

1. **Respaldos solo al desplegar** — `uploads/` guarda cartas responsivas firmadas; un disco corrupto entre deploys borra evidencia.
2. **Sin cabeceras de seguridad ni `/cyber-neo` de Equipos** — el sistema ya esta expuesto en internet.
3. **Correo sin confirmar y sin recordatorio de vencidos** — la autorizacion y la devolucion dependen de que la gente entre a la pantalla.
