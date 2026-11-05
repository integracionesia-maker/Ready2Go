# BACKLOG — GOCreate (Presupuestos + Control de Equipos)

> Plataforma interna del area de marketing de Grupo Ortiz. Dos modulos, una app. Corte: 05/11/26.
> Fase actual: **8 Produccion** (Observatorio, 30/10/26) · en `https://gocreate.mx` · mejora continua en paralelo.
> Plan de referencia: `docs/equipos/plan-quirurgico.md` · Contrato congelado: `docs/equipos/contratos/`
> Seguridad: gaps abiertos en `SECURITY.md` (los #13-#19 de abajo salen de ahi).

---

## Cierres de fin de proyecto (con marketing)

Ya no bloquean nada: el sistema esta en produccion. Lo que sigue abierto se confirma con Damian.

| # | Pendiente | De quien | Estado al 05/11/26 |
|---|---|---|---|
| T1 | Nombres + correos GO del area | Emily | Por confirmar con Damian (hay usuarios reales: 27 al 27/08) |
| T2 | Inventario de camaras, luces y tripies | Emily / Betzabet | Por confirmar (9 equipos en produccion al 27/08) |
| T3 | Razon social emisora de la responsiva | Marketing / RH | Sale de la tabla `empresa` (3 al 27/08) |
| T4 | Nombre de dominio | Emily / Melisa | **Cerrado:** `gocreate.mx` |
| T6 | Credenciales SMTP | Jose / Sistemas | Por confirmar: el doc de migracion decia sin `SMTP_*` en produccion |
| T7 | Fuentes Blauer Nue / Conthic en woff2 | `context_desing_go` | Abierto: `frontend/src/design/fonts.css` usa pila de respaldo |

T5 (aprobacion del costo del dominio) — cerrado 27/07, Melisa aprobo por correo.

## Control de Equipos — mapa E1-E17 (plan original)

| # | Tarea | WP | Estado |
|---|---|---|---|
| E1-E2 | RBAC aditivo y sus pruebas | WP1 | Hecho — `app/rbac.py`, `tests/rbac/` |
| E3-E4 | Modelo de datos y seed del inventario | WP2 | Hecho — `models_equipos.py`, `migrate_equipos.py`, `seed_equipos.py` |
| E5-E7 | API inventario, prestamos y aprobacion | WP3-4 | Hecho — `routers/equipment.py`, `loans.py`, `approvals.py` |
| E8 | Carta responsiva PDF versionada con hash | WP5 | Hecho — `app/pdf/responsiva.py` |
| E9 | Mailer SMTP + log idempotente | WP6 | Hecho — `mailer.py`, `notificaciones.py`; BCC `25d432f` |
| E10 | Recordatorio diario de vencidos | WP6 | **Cancelado 14/09/26** (script eliminado; `docs/deploy/recordatorios_launchagent.md`). Reabrir si marketing lo pide |
| E11 | Shell liquid glass | WP7 | Parcial — `frontend/src/design/`; faltan fuentes de marca (T7) |
| E12 | Migrar vistas de Presupuestos al shell | WP7 | Hecho — `Glass*` usados en `modules/presupuestos` |
| E13-E16 | Frontend inventario, prestamo, activos/aprobaciones/historial, dashboard | WP8 | Hecho — `frontend/src/modules/equipos/pages/` |
| E17 | e2e del flujo completo | WP8 | Hecho — `frontend/e2e/equipos-flujo-completo.spec.js` |

## Pendientes

| # | Tarea | Prioridad | Estado |
|---|---|---|---|
| 3 | Respaldos **programados** de `presupuesto.db` y `uploads/` (hoy solo al desplegar: 7 copias, misma maquina, sin cifrar) | Alta | Pendiente |
| 4 | Tests de CRUD de creadores/marcas | Media | Pendiente |
| 8 | CSP + HSTS + `nosniff` y revisar `CORS_ORIGINS` (HTTPS ya lo da Cloudflare) | Alta | Pendiente |
| 9 | Auditoria `/cyber-neo` del modulo Equipos | Alta | Pendiente |
| 11 | Rate limit de login en almacen compartido (solo si hay varios workers) | Baja | Pendiente |
| 13 | Comprobantes de ticket: validar firma de bytes y leer por partes (diag. M1, M2) | Media | Pendiente |
| 14 | Exigir `must_change_password` en el backend (diag. M7) | Media | Pendiente |
| 15 | Correr `migrate_rbac_aditivo.py` en produccion (siembra `ADMIN_USUARIOS`) | Alta | Pendiente |
| 16 | Confirmar correo en produccion (`NOTIF_ENABLED`, SMTP) | Media | Por confirmar con Damian |
| 17 | Ignorar `backend/presupuesto.db.bak-*` en `.gitignore`; sanear PII de `seed_usuarios_mkt.py` (diag. A3) | Media | Pendiente |
| 18 | Saneo de `audit_log` anterior al 18/08/26 con contrasenas (diag. C1) | Media | Por confirmar con Damian |
| 19 | `react-router-dom` 6 a 7 (2 avisos moderados) | Baja | Pendiente |

## En progreso

_Ninguna registrada en el repo (ultimo commit 19/10/26)._

## Completados (recientes)

| # | Tarea | Completado | Evidencia |
|---|---|---|---|
| 5 | `SECURITY.md` con checklist formal | 05 Nov 2026 | `SECURITY.md` |
| 10 | Dominio + deploy en Mac mini | 2026 (fecha Por conciliar: 10/08 Observatorio; 27/08 y 01/09 en el repo) | `docs/deploy/`, `status.md` |
| 20 | Paquete `ADMIN_USUARIOS` y rol/perfil de creador | 19 Oct 2026 | `0676c64`, `4695ba2` |
| 21 | Reporte del dashboard en HTML autocontenido | 09 Oct 2026 | `a7cbdce` |
| 22 | Firma predeterminada del perfil | 06 Oct 2026 | `79ff3bd` |
| 23 | Fotos de entrega reemplazables; meta de gasto mensual y periodo unico | 15 Sep 2026 | `4c5ea3d`, `abf34cb` |
| 24 | Fecha de regreso editable, BCC en correos, auto-desbloqueo | 14 Sep 2026 | `4838ebc`, `25d432f`, `367de7f` |
| 25 | Diagnostico de seguridad y correcciones criticas | 18 Ago 2026 | `docs/seguridad/`, `f58edb9` |
| 1, 2, 6, 7, 12-14 | Repo, auth, owner, responsividad, plan quirurgico, renombre, tipografia (y gastos generales/borrado, antes #8) | Jul 2026 | ver `CHANGELOG.md` y `docs/` |
