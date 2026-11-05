# Security — GOCreate (Presupuestos + Control de Equipos)

> Checklist de seguridad. Aplica: hay login, roles, datos de gasto (tickets con comprobante), cartas responsivas firmadas y fotos de equipo.
> Fecha de corte: 05/11/26. Describe lo que el código HACE hoy (evidencia en rutas de `backend/app/`); se apoya en `docs/seguridad/diagnostico-seguridad-2026-08-18.md` y `docs/presupuestos/auth/auth-arquitectura.md`, y cada gap del diagnóstico se volvió a verificar contra el código actual.
> Producción: `https://gocreate.mx`, Mac mini de marketing, túnel `cloudflared` hacia uvicorn en `127.0.0.1:8000`, un solo worker (`docs/deploy/migracion-macmini.md`).

---

## Checklist mínimo

| Área | Pregunta | Estado |
|---|---|---|
| Secretos | ¿Hay claves o credenciales en archivos? | `backend/.env` fuera de git (`.gitignore`: `.env`, `*.db`, `uploads/`). `JWT_SECRET_KEY` obligatoria: sin ella el proceso no arranca (`security._jwt_secret`), pero sin longitud mínima. Los `.env.example` traen valores débiles de muestra para el superadmin y los usuarios sembrados: no usarlos en producción |
| Auth | ¿Login, roles, permisos y sesiones definidos? | Sí. Contraseñas con argon2 (`argon2-cffi`), mínimo 10 caracteres con letras y números (`security.validate_password_strength`). Access token JWT HS256 de 15 min por defecto en cookie `httpOnly`, `SameSite=Lax`, `Secure` si `ENV=production`. Refresh opaco de 7 días con hash SHA-256 en base, cookie con ruta `/api/auth`, rotación y detección de reuso (revoca todo y sube `token_version`). Logout, cambio de contraseña y desactivar usuario invalidan tokens vivos (`dependencies.get_current_user` revisa `is_active` y `token_version` en cada request) |
| Roles | ¿Qué roles y paquetes existen? | 9 roles base (`superadmin`, `admin`, `creador`, `marketing_presupuestos`, `marketing_equipos`, `marketing_admin`, `marketing_basico`, `colaborador_mkt` legado, `usuario`) y 6 paquetes aditivos: `APROBADOR_EQUIPO`, `CUSTODIO_EQUIPO`, `AUDITOR`, `APROBADOR_PRESUPUESTOS`, `TITULAR_FIRMA_EQUIPO` (singleton, se resuelve por identidad) y `ADMIN_USUARIOS` (solo sobre rol `admin`, solo lo concede un superadmin). Catálogo en `rbac_catalog.py`, motor deny-by-default en `rbac.py`; si la base falla al resolver permisos responde 503, nunca un 403 masivo |
| Autorización | ¿El backend valida o solo oculta botones? | El backend valida. Equipos usa `require_perm`/`require_cualquiera` más alcance por participación (préstamo, foto, responsiva). Presupuestos sigue con `require_role` fijo (`tickets.py`, `creators.py`) y la excepción `require_rol_o_paquete` para `APROBADOR_PRESUPUESTOS`; el catálogo y esos endpoints no coinciden del todo (ver gaps) |
| Datos | ¿Qué datos sensibles se guardan? | Usuarios (correo, nombre, hash), tickets y comprobantes de gasto, cartas responsivas (nombre, área, serie del equipo, firmas manuscritas), fotos de entrega y devolución, firma guardada por usuario |
| Exposición | ¿Endpoints públicos sin protección? | Sin sesión: `GET /api/health`, `POST /api/auth/login`, `POST /api/auth/unlock/challenge` y `/verify` (rompecabezas de auto-desbloqueo, por diseño), más el SPA estático. `/docs` y `/redoc` solo si `ENV` no es `production`. El mount estático de `/uploads` se eliminó: todo archivo sale por endpoint con sesión |
| Archivos | ¿Se validan uploads? | Comprobantes de ticket: extensión `.jpg/.jpeg/.png/.pdf` y MIME declarado por el cliente, 10 MB, 20 por ticket, nombre `uuid` (`upload_manager.py`). Equipos: firma de bytes PNG/JPEG (el MIME se deriva de los bytes), foto 3 MB, firma 250 KB, tope 50 Mpx, nombre `uuid` (`media_manager.py`); descarga solo por `GET /api/media/{id}` con participación, `Cache-Control: private` |
| Logs | ¿Exponen secretos? | La auditoría redacta `password`, `token`, `secret`, `authorization`, `api_key` y no guarda cuerpo de login, cambio de contraseña ni refresh (`middleware_audit.py`). No se revisó por ejecución que los logs de uvicorn estén limpios |
| Backups | ¿Respaldos protegidos? | `docs/deploy/deploy-app.sh` respalda la base (API `backup` de sqlite) y `uploads/` (tar) en cada deploy y conserva los últimos 7, en `backups/` de la misma máquina, sin cifrar. No hay respaldo programado (ver gaps) |
| Dependencias | ¿Librerías vulnerables? | Última auditoría documentada: `pip-audit` sin hallazgos y `npm audit` con 2 moderadas en `react-router-dom` 6 (CHANGELOG, 18/08/26). `requirements.txt` usa mínimos `>=` sin versiones fijas. No se volvió a correr |
| Git | ¿Secretos, bases o archivos privados? | `.env`, `*.db` y `uploads/` ignorados. `backend/presupuesto.db.bak-*` NO está ignorado (aparece sin seguimiento en `git status`). `backend/seed_usuarios_mkt.py` versionado trae correos corporativos reales (hallazgo A3 del diagnóstico) |
| Red | ¿Puertos, túneles, dominios? | uvicorn solo en `127.0.0.1:8000`; TLS lo termina Cloudflare; `CORS_ORIGINS` lista explícita (`main.py`). Qué cabeceras pone el borde: Por confirmar con Damián / Sistemas |
| Errores | ¿Revelan información interna? | Sobre uniforme `{detail, codigo}` (`errores.py`). Excepción: `upload_manager.py` devuelve `Error al guardar el archivo: {exc}` en un 500 |
| Auditoría | ¿Quién hizo qué? | Sí. `AuditMiddleware` registra cada request a `/api/*` (salvo `/api/health` y `/api/audit-logs`): actor, método, ruta, estado, IP, agente, duración; más llamadas manuales a `crud.log_audit` (login, bloqueos, usuarios, roles, firma guardada, fotos con sha anterior y nuevo). Cola en memoria: un `kill -9` pierde los últimos eventos (`audit_queue.py`). Solo la lee quien tenga `auditoria:ver` (superadmin). Bitácora por préstamo en `loan_event`. Sin plazo de retención definido |
| Recuperación | ¿Plan si algo falla? | `deploy-app.sh` vuelve solo a la release anterior si el health check falla. Procedimiento de restauración de datos desde un respaldo: Por confirmar con Damián (no hay documento) |

## Controles específicos

- **Bloqueo y límite de intentos** (`crud.py`, `security.py`, `routers/auth.py`): 5 fallos por cuenta bloquean 5 min y se duplica por fallo extra hasta 60 min; 30 intentos por 15 min por IP (`request.client.host`, en memoria; cuenta también los logins exitosos). Rompecabezas de auto-desbloqueo: reto de 120 s, 5 intentos por reto, 3 desbloqueos por cuenta por día, todo en memoria. Un superadmin desbloquea con un clic (`POST /api/users/{id}/unlock`, no aplica a la cuenta superadmin; esa se resuelve con `reset-password-superadmin` entre superadmins).
- **Carta responsiva con huella** (`pdf/responsiva.py`, `crud_loans.generar_responsiva`): cada firma o cambio crea una versión nueva en `responsiva_doc` (UNIQUE préstamo+versión); nunca se sobrescribe un archivo (`ArchivoYaExiste`); se guarda el SHA-256 del PDF, y de cada foto y firma sobre sus bytes originales (`media_asset.sha256`). La razón social sale de la tabla `empresa`. El PDF solo se descarga en `GET /api/loans/{id}/responsiva.pdf` con sesión y participación. No es firma electrónica avanzada (RISKS #10).
- **Correo** (`mailer.py`, `notificaciones.py`): `smtplib` con STARTTLS por defecto, apagado por defecto (`NOTIF_ENABLED=false`, sin socket), texto plano, `notification_log` con UNIQUE préstamo+tipo+destinatario y 3 intentos como máximo. Cabecera Bcc opcional desde `SMTP_BCC`.
- **CSRF**: sin token propio; se apoya en `SameSite=Lax` y CORS por lista con credenciales (`auth-arquitectura.md` §4).
- **Inyección**: ORM de SQLAlchemy; `text()` solo en `folio.py` con parámetros enlazados; sin `subprocess`, `eval` ni `pickle` en `backend/app`. El fallback del SPA resuelve la ruta real y exige que caiga dentro de `frontend/dist` (`main.py`).
- **Pruebas**: 786 funciones de prueba en `backend/tests` (por búsqueda `def test_`; no se ejecutaron), 11 specs Playwright en `frontend/e2e`.
- **SIEM/EDR/XDR**: no implementado; solo existe `GET /api/health`. Sin `/ready`, `/metrics` ni `siem_events`.

## Gaps abiertos (verificados contra el código del 05/11/26)

| # | Gap | Evidencia | Pendiente en |
|---|---|---|---|
| 1 | Sin cabeceras de seguridad (CSP, HSTS, `nosniff`, `X-Frame-Options`, `Referrer-Policy`) | `main.py` sin middleware; búsqueda sin coincidencias | BACKLOG #8; diag. M5 |
| 2 | Límite de intentos en memoria de un solo proceso, sin limpieza de claves, solo por IP y cuenta logins exitosos; detrás del túnel falta confirmar qué IP ve | `security.py`, `auth.py` | BACKLOG #11; diag. M9 |
| 3 | Respaldos solo al desplegar, 7 copias, misma máquina, sin cifrar ni copia externa | `deploy-app.sh`; sin tarea programada en `docs/deploy` | BACKLOG #3; RISKS #3 |
| 4 | Comprobantes de ticket sin validar firma de bytes; el MIME lo declara el cliente | `upload_manager.py` | diag. M1 |
| 5 | Archivos leídos completos a memoria antes de aplicar el tope; miniaturas decodifican hasta 50 Mpx por request | `upload_manager.py`, `routers/loans.py`, `media_manager.py` | diag. M2, M3 |
| 6 | `must_change_password` solo lo exige la pantalla (`ProtectedRoute.jsx`); la API no lo bloquea | `dependencies.py`, `routers/auth.py` | diag. M7 |
| 7 | Mensaje distinto para cuenta bloqueada (confirma que el usuario existe); sin igualar tiempo de respuesta en login | `routers/auth.py` | diag. A2, M8 |
| 8 | Presupuestos fuera del RBAC del catálogo: `creators.py` y `tickets.py` con listas fijas que difieren del catálogo | `routers/creators.py`, `rbac_catalog.py` | diag. M4 |
| 9 | `JWT_SECRET_KEY` sin longitud mínima; `CORS_ORIGINS=*` con credenciales no se rechaza; `/docs` abierto si `ENV` falta | `security.py`, `main.py` | diag. B2, B3, B12 |
| 10 | `responsable_email` sin validar como correo y `_armar` fuera del `try` del envío | `schemas_loans.py`, `mailer.py` | diag. B11 |
| 11 | La huella SHA-256 se guarda y se usa como ETag, pero ningún endpoint la recalcula al servir; la del PDF admite `NULL` | `routers/media.py`, `responsivas.py`, `models_equipos.py` | Por confirmar con Damián |
| 12 | Hay copias de la base sin ignorar por git (`presupuesto.db.bak-*`) y correos reales en `seed_usuarios_mkt.py` | `git status`, `git ls-files` | diag. A3 |
| 13 | Falta `/cyber-neo` del módulo Equipos antes del piloto y repetir `pip-audit`/`npm audit` | sin reporte posterior al 18/08/26 | BACKLOG #9 |

## Por conciliar / Por confirmar

- Por conciliar con Damián: fecha de salida a producción. Observatorio (30/10/26): desde el 10/08/26. El repo prueba `gocreate.mx` con datos reales el 27/08/26 (`docs/deploy/migracion-macmini.md`) y la Mac mini el 01/09/26; `CLAUDE.md` dice 14/09/26 (fecha de la guía de deploy). `status.md` ya se corrigió el 05/11/26.
- Por confirmar con Damián: si se saneó el histórico de `audit_log` con contraseñas anteriores al arreglo del 18/08/26 (diag. C1); si producción ya define variables `SMTP_*` (el doc de migración decía que no).

## Revisión

| Fecha | Revisor | Hallazgos | Estado |
|---|---|---|---|
| 18/08/26 | Diagnóstico automatizado + verificación manual | 2 críticos y 1 alto corregidos; resto en `docs/seguridad/` | Parcial |
| 05/11/26 | Claude Code (lectura de código, sin ejecutar) | 13 gaps abiertos arriba | Pendiente de revisión humana |
