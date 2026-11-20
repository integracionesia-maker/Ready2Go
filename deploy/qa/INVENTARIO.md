# Inventario del entorno QA de GOCreate

> Paso 1 y 2 de la receta del documento `08-entorno-qa-aislado.md` (carpeta de funciones reutilizables, `AVANCES/optimizacion`). Escrito el 20/11/2026. Describe **lo que hay en el código y en la Mac mini**, y qué decisiones se tomaron por defecto mientras Damián confirma las abiertas.

## 1. Dependencias de GOCreate (lo que el QA debe aislar)

| Tema | Qué usa GOCreate | Cómo queda en el QA |
|---|---|---|
| Base de datos | SQLite (WAL), `sqlite:///./presupuesto.db`, **relativa al directorio de trabajo**. Sin Alembic: `create_all` + scripts `migrate_*.py` | Archivo propio `/opt/go/gocreate-qa/shared/data/presupuesto.db`, enlazado a cada release por symlink (igual que producción) |
| Archivos subidos | `./uploads/` (`tickets`, `equipos`, `responsivas`, `firmas_usuario`), relativo al cwd | `/opt/go/gocreate-qa/shared/data/uploads`, propio |
| Variables de entorno | `ENV`, `JWT_SECRET_KEY`, `JWT_*_EXPIRE_*`, `CORS_ORIGINS`, `DATABASE_URL`, `RBAC_MODO`, `NOTIF_ENABLED`, `SMTP_HOST/PORT/USER/PASSWORD/FROM/STARTTLS/BCC`, `APP_PUBLIC_URL`; nuevas del QA: `QA_MODE` | `.env` propio, permisos 600, secreto nuevo. Plantilla: `env.qa.example` |
| Servicios externos | **Solo SMTP** (`smtplib`). No hay ERP, IA, mensajería, pagos ni publicación a terceros | SMTP ausente y `NOTIF_ENABLED=false` |
| Tareas programadas / jobs | Ninguna. Hay un consumidor de la cola de auditoría **dentro** del proceso (`audit_queue`). El recordatorio de vencimiento se retiró el 14/09/2026 | Nada que apagar |
| Llaves de cifrado | Solo `JWT_SECRET_KEY` (no hay cifrado de datos en reposo) | Secreto nuevo generado con `openssl rand` en el servidor |
| Estado en memoria | Rate limit de login y rompecabezas de desbloqueo (por proceso) | Proceso propio: no se comparte con producción |
| Frontend | Lo sirve el mismo backend (`frontend/dist`) | Se compila en el QA con `VITE_APP_ENV=qa` |

## 2. Versión a evaluar (paso 2)

Rama **`qa`** de `integracionesia-maker/Ready2Go`. Arranca igual a `master` (`git push origin master:qa`), de modo que Dafnne audita lo mismo que usan las personas en producción. Para validar un arreglo **antes** de producción: `git push origin dami-branch:qa` y `./actualizar.sh`. Cambiar la rama no requiere root (solo `push`).

> Los cambios de código de esta tarjeta (banner QA, título `[QA]`, `QA_MODE`, `/robots.txt`) tienen que estar en la rama `qa`; llegan ahí por merge desde `master`/`dami-branch`. En producción son inertes: sin `QA_MODE` ni host `qa.*` ni `VITE_APP_ENV=qa` no hacen nada.

## 3. Interruptores obligatorios (sección 7 del documento)

| Efecto externo | Valor en QA | Dónde |
|---|---|---|
| Correo saliente | **Apagado**: `NOTIF_ENABLED=false`, sin `SMTP_*` ni `SMTP_BCC`. El sistema solo registra el aviso en `notification_log` (queda `pendiente`) | `env.qa.example`; `sembrar_datos.py` lo fuerza además por código; `verificar_aislamiento.sh` (#6) lo comprueba |
| Mensajería / push / IA / ERP / pagos / publicación a terceros | No existen en GOCreate | — |
| Tareas programadas | No hay | — |
| Secretos | Distintos a producción, generados en el servidor | `alta_host.sh` |
| Datos personales | Solo ficticios (correos `@qa.gocreate.example`, nombres inventados) | `sembrar_datos.py`; verificación #7 |

**Fase 2 opcional — ver los correos sin que salgan:** instalar Mailpit local en la mini (SMTP en `127.0.0.1:1025`, solo escucha en loopback) y apuntar `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_STARTTLS=false`, `NOTIF_ENABLED=true`. Así Dafnne auditaría también el contenido de los correos. Requiere un segundo hostname protegido por Access para su interfaz web. No está incluido en esta entrega.

## 4. Usuarios QA (un usuario por rol base y por paquete aditivo)

Las contraseñas son aleatorias, se generan al sembrar y quedan **solo** en `/opt/go/gocreate-qa/shared/env/credenciales_qa.txt` (600). Aquí no hay ninguna.

| Usuario | Rol base (+ paquete) | Para qué sirve en la auditoría |
|---|---|---|
| `qa.superadmin` | superadmin | Todo: usuarios, roles, auditoría, empresas |
| `qa.admin` | admin | Presupuestos y equipos completos, sin gestión de usuarios |
| `qa.mkt.presupuestos` | marketing_presupuestos | Solo presupuestos |
| `qa.mkt.equipos` | marketing_equipos | Solo equipos |
| `qa.mkt.admin` | marketing_admin | Presupuestos y equipos de marketing |
| `qa.mkt.basico` | marketing_basico | Vista básica |
| `qa.colaborador` | colaborador_mkt | Pide equipo y ve lo propio |
| `qa.usuario` | usuario | Solo inicio y perfil |
| `qa.creador.1` … `.4` | creador | Sube tickets, ve lo suyo; beneficiario de préstamos |
| `qa.aprobadora` | colaborador_mkt + APROBADOR_EQUIPO + TITULAR_FIRMA_EQUIPO | Autoriza entregas, confirma devoluciones, firma de entrega (el papel de Melisa) |
| `qa.custodio` | usuario + CUSTODIO_EQUIPO | Inventario |
| `qa.auditor` | usuario + AUDITOR | Solo lectura global |
| `qa.aprobador.presupuestos` | usuario + APROBADOR_PRESUPUESTOS | Valida tickets sin ser admin |
| `qa.admin.usuarios` | admin + ADMIN_USUARIOS | Administra cuentas por delegación |

**Datos sembrados:** 8 marcas, 8 creadores, ~120 tickets de 6 meses (aprobados, pendientes, rechazados, con comprobante de imagen ficticia), 24 gastos generales, 18 gastos operativos, 12 equipos y **9 préstamos reales por la API**: completados (2), prestado en plazo, prestado con atraso, con firma/autorización pendientes, devuelto por confirmar, con incidencia (equipo dañado en revisión), borrador y cancelado. Los folios, eventos, firmas y cartas responsivas PDF son los que genera el sistema.

## 5. Estado de los requisitos QA-01 a QA-15

| ID | Requisito | Cómo se cumple | Estado |
|---|---|---|---|
| QA-01 | BD distinta | Symlink a `shared/data` del QA; verificación #1, #2 | Preparado; falta host |
| QA-02 | Archivos propios | Symlink `uploads`; verificación #3 | Preparado; falta host |
| QA-03 | `.env` y secretos propios | `alta_host.sh` + verificación #4 | Preparado; falta host |
| QA-04 | Proceso propio en `127.0.0.1` y puerto exclusivo | plist con `--host 127.0.0.1`, puerto **8010**; verificación #5 | Preparado; falta host |
| QA-05 | Servicio launchd propio | `com.go.gocreate-qa.api` y `.tunnel` (LaunchDaemons, como producción) | Preparado; falta host |
| QA-06 | Solo por Cloudflare Tunnel, con regla final 404 | Túnel **propio** administrado en el panel (ver README). Desviación del documento: no se puede usar `cloudflared tunnel ingress validate` en un túnel remoto; se valida con `curl` | Pendiente (panel Cloudflare) |
| QA-07 | Acceso restringido | Cloudflare Access con lista de correos; verificación #8 | Pendiente (D2) |
| QA-08 | Un usuario por rol | `sembrar_datos.py`; verificación #7 | Hecho y probado en local |
| QA-09 | Integraciones simuladas | Sección 3; verificación #6 | Hecho |
| QA-10 | Solo datos ficticios | `sembrar_datos.py` es la única fuente; se niega a correr sin `QA_MODE` o sobre la ruta de producción | Hecho y probado en local |
| QA-11 | Señales de QA | Banner, título `[QA]`, `X-Robots-Tag`, `/robots.txt`, `qa:true` en `/api/health`; verificación #9 | Hecho |
| QA-12 | Despliegue controlado | `actualizar.sh` (rama `qa`) y `reiniciar_datos.sh` | Hecho; falta probar en host |
| QA-13 | Producción intacta | Ningún script escribe en `/opt/go/gocreate`; verificación #10 (huella antes/después) | Preparado |
| QA-14 | Registro del día de la creación | Fila en el runbook y `status.md` al ejecutar el alta | Pendiente (al ejecutar) |
| QA-15 | Encender/apagar | `encender.sh` y `apagar.sh` | Hecho; falta probar en host |

## 6. Hallazgos sobre producción y el host (leídos hoy, sin modificar nada)

1. **Permisos de producción demasiado abiertos.** En `/opt/go/gocreate/shared/`: el directorio es `drwxr-xrwx`, `shared/env/.env` es `-rw----rw-` (otros pueden leerlo **y escribirlo**), `presupuesto.db` es `-rw-r--rw-` y el raíz `/opt/go/gocreate` es `drwx---r-x`. Por esos modos, cualquier otro usuario de servicio del host (`_requis`, `_plazamadero` y el futuro `_gocreateqa`) podría leer el `JWT_SECRET_KEY` de producción y escribir su base. **No lo probé como otro usuario;** lo deduzco de los modos. La última comprobación de `verificar_aislamiento.sh` («`_gocreateqa` no lee su .env ni escribe su base») lo prueba de verdad; si la deducción es correcta, saldrá en FAIL hasta que se corrija. **Confirmado y corregido el 20/11/2026:** la comprobación final lo dio en FAIL con el QA ya desplegado (`_gocreateqa` leía el `.env` de producción y escribía su base). Con autorización de Damián se aplicó `chmod 700 /opt/go/gocreate` (era 705) como `_gocreate`; producción siguió respondiendo 200 y la comprobación pasó a PASS. Es reversible con `chmod 705`. **Sigue abierto, como defensa en profundidad:** dentro de esa carpeta, `shared/env/.env` es `rw----rw-`, `presupuesto.db` es `rw-r--rw-` y `shared/` y `shared/data` son `rwxr-xrwx`; conviene `chmod 600` a esos dos archivos y `700` a esos dos directorios. Lo mismo revisar en `/opt/go/plazamadero` y `/opt/go/requis` (no los inspeccioné).
2. **`integraciones` tiene `sudo` completo con contraseña** (`(ALL) ALL`); solo los comandos de gocreate y plazamadero van sin contraseña. El alta del QA necesita esa contraseña **una vez**.
3. **Capacidad:** la mini tiene 24 GB de RAM, ~380 GB libres y carga baja; cada app ocupa ~100–150 MB. Sobra para el QA (D3 resuelta). Puertos ocupados: 8000 (gocreate), 8001, 8003 (requis), 8004 (plazamadero), 3040–3042, 5432. El QA usa **8010**.

## 7. Limitaciones conocidas del QA

- Arranca con `create_all`: **no ejercita los scripts `migrate_*.py`** que sí corren sobre la base real de producción. Una migración con un fallo solo se vería con una copia de producción (no se hace: QA-10).
- Si una versión nueva agrega una columna, `create_all` no la crea en una base existente: usar `./actualizar.sh --reiniciar`.
- Los préstamos sembrados se reubican en el pasado cambiando sus fechas, pero los **eventos** del préstamo conservan la hora real del sembrado.
- Sin correo real no se auditan los correos (ver fase 2 en §3).
- El QA comparte la mini con producción: si la mini se cae, caen las dos. Es el trade-off de no duplicar infraestructura (D3).

## 8. Decisiones abiertas y el valor por defecto usado

| ID | Tema | Default de esta entrega | Quién decide |
|---|---|---|---|
| D1 | Dominio | `qa.gocreate.mx` (zona existente, sin costo) | José / Damián |
| D2 | Cloudflare Access (plan y lista de correos) | Se asume disponible; sin él, solo el login de la app | Damián |
| D4 | Quién ejecuta el alta con root | `alta_host.sh` lo hace de un tiro con `sudo` | Damián / Gerardo |
| — | Rama | `qa` | Damián |
| — | Correo | Apagado | Damián |
| — | Roles para Dafnne | Todos | Damián |
