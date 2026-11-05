# Contexto — GOCreate (Plataforma de Marketing: Presupuestos + Control de Equipos)

> Conexiones pool: [[CLAUDE]] | [[context_proyectos]] | [[framework_operative_enforcement/CLAUDE]] | [[framework_operative_enforcement/PLAYBOOK]] | [[framework_operative_enforcement/FRAMEWORK]]
> Recursos: [[IDENTIDAD DE MARCA/context_design]] (visual)
> Archivos del proyecto: [[CLAUDE]] | [[status]] | [[BACKLOG]] | [[RISKS]] | [[MVP_BREAKDOWN]] | [[DESIGN_SYSTEM]] | [[CHANGELOG]] | [[avances_diarios]] | [[SECURITY]] | [[docs/equipos/plan-quirurgico]]

## 1. Resumen

- Proyecto: **GOCreate** — plataforma interna del area de marketing (antes `presupuesto_creadores` → `Ready2Go` el 2026-07-27 → **GOCreate** el 2026-08-04; repo de GitHub sigue en `Ready2Go`, sin renombrar)
- Departamento: Inteligencia Operativa / Marketing (Grupo Ortiz)
- Owner: Damian (marketing) — supervision: Jose Aguilar
- Repo: `github.com/integracionesia-maker/Ready2Go` · ramas: `master`, `dami-branch`, `jose-branch`, `BeniBranch`
- Estado: **Fase 8 Produccion** (Observatorio, 30/10/26) en `https://gocreate.mx`; Presupuestos y Control de Equipos construidos y operando
- Ultima actualizacion: 2026-11-05 (puesta al dia: produccion, Equipos construido, pruebas, riesgos). Antes: 2026-07-27
- Clasificacion: Herramienta interna — en produccion

## 2. Problema

Dos problemas del mismo area, hasta hoy sin sistema:

1. **Presupuestos.** El equipo necesita controlar el presupuesto asignado a cada creador de contenido: cuanto se le asigno por ciclo, cuanto gasto (por ticket con comprobante), cuanto le queda, por marca y periodo.
2. **Prestamo de equipo.** Marketing presta equipo de grabacion (celulares, micros RODE y DJI, estabilizadores Osmo, camaras, luces, tripies) sin control real: no hay registro de quien tiene que equipo, ni responsiva digital, ni evidencia del estado en que salio y volvio, ni flujo de autorizacion. Hoy se persigue a la aprobadora con un formulario en papel para que lo firme.

## 3. Objetivo

Una sola plataforma, un login, dos modulos:

**Presupuestos** (existente): creadores + ciclos semanal/mensual, tickets con comprobante y validacion, gastos generales por marca, borrado logico/fisico, dashboard con KPIs y graficos, reporte PDF.

**Control de Equipos** (construido; plan en `docs/equipos/plan-quirurgico.md`): inventario con ficha e historial de auditorias de condicion, prestamo con seleccion de equipos y accesorios, foto frente+atras obligatoria por equipo en entrega y devolucion, firma digital de quien entrega y quien recibe, carta responsiva en PDF generada en servidor con folio, autorizacion de entrega y confirmacion de devolucion por la aprobadora, notificacion por correo, historial exportable.

## 4. Usuarios

| Perfil | Quien | Que hace |
|---|---|---|
| `superadmin` | Damian, Jose | Todo, incluida gestion de usuarios y roles |
| `admin` | Marketing (presupuestos) | Presupuestos completo + operacion de equipos. Sin gestion de usuarios (R4) |
| `creador` | Creadores de contenido | Sube sus tickets, ve solo lo propio |
| `marketing_presupuestos`, `marketing_equipos`, `marketing_admin`, `marketing_basico` | Area de marketing | Presupuestos y/o Equipos segun el rol (`app/rbac_catalog.py`) |
| `colaborador_mkt` (legado), `usuario` | Area de marketing / empleados | Pide equipo y ve lo propio; `usuario` solo inicio y perfil |
| `APROBADOR_EQUIPO` (aditivo) | Melisa | Autoriza entregas, confirma devoluciones, cierra incidencias |
| `CUSTODIO_EQUIPO`, `AUDITOR`, `APROBADOR_PRESUPUESTOS` (aditivos) | A definir con el area | Inventario; solo lectura global; aprobar tickets sin ser admin |
| `TITULAR_FIRMA_EQUIPO`, `ADMIN_USUARIOS` (aditivos) | Una persona / un admin | Firma de entrega en la responsiva; administrar cuentas sin ser superadmin |

Roles aditivos: se suman al rol base, no lo reemplazan. 9 roles base y 6 paquetes aditivos en `app/rbac_catalog.py`; matriz original: §3 del plan quirurgico.

## 5. Proceso objetivo (Control de Equipos)

1. Colaborador crea el prestamo: datos, area, razon social, quien entrega, motivo, fechas.
2. Selecciona equipos disponibles; declara accesorios por equipo y quien se queda con el cargador.
3. Toma foto frente y atras de cada equipo (obligatorio; se comprime en el navegador antes de subir).
4. Firman quien entrega y quien recibe (canvas). Se asigna folio `CE-000N` y se genera el PDF de la responsiva en servidor.
5. Correo automatico: PDF al responsable y a la aprobadora, con aviso de autorizacion pendiente.
6. La aprobadora autoriza la entrega en la plataforma (no en papel).
7. Al regresar el equipo: se registran fotos de devolucion (o se marca "no devuelto" con nota obligatoria).
8. La aprobadora confirma equipo por equipo: `ok` / `danado` / `faltante` → prestamo `completado` o `incompleto`. Un equipo con incidencia queda en `revision` hasta que se cierre la incidencia con nota.

## 6. Sistema / stack

- Backend: FastAPI + SQLAlchemy + SQLite (`backend/presupuesto.db`), routers `auth users creators brands tickets dashboard general_expenses operational_expenses rubros roles user_roles empresas equipment loans approvals media responsivas notifications audit_logs firma_guardada`
- Frontend: Vite 6 + React 18.3.1 + Tailwind 3 + ApexCharts (v1.1.0). 100% React (cero HTML/JS suelto)
- Auth: JWT en cookie httpOnly + refresh token rotativo, bloqueo por cuenta, rate limit de login por IP; detalle en `SECURITY.md`
- Reportes: carta responsiva PDF en servidor (`reportlab`, versionada con sha256); reporte del dashboard como HTML autocontenido (el PDF del dashboard se reemplazo el 09/10/26)
- Correo: SMTP por `smtplib` con copia oculta `SMTP_BCC`; apagado por defecto (`NOTIF_ENABLED=false`). Estado real en produccion: Por confirmar con Damian
- Produccion: `https://gocreate.mx` en la Mac mini (tunel Cloudflare, uvicorn `127.0.0.1:8000`, un worker); local `127.0.0.1:8000` / `127.0.0.1:5173`

## 7. Tabla de fases

| Fase | Presupuestos | Control de Equipos |
|---|---|---|
| 0 Intake | Hecho | Hecho (reunion mkt 27/07) |
| 1 Descubrimiento | Hecho | Hecho (transcript + maqueta HTML) |
| 2 Clasificacion | Hecho | Hecho (herramienta interna) |
| 3 Diseno operativo | Hecho | Hecho (flujo y roles en el plan) |
| 3.5 Planeacion Quirurgica | n/a | Hecho — plan aprobado 27/07 |
| 4 Diseno tecnico | Hecho | Hecho (modelo de datos + API + RBAC en el plan) |
| 5 Build | Hecho | Hecho (construido jul-sep 2026; 786 funciones de prueba) |
| 6 Revision critica | Parcial (diagnostico de seguridad 18/08/26; falta `/cyber-neo` de Equipos) | Parcial |
| 7 Piloto | Sin registro en el repo | Sin registro en el repo (Por confirmar con Damian) |
| 8 Produccion | **En curso — fase actual (Observatorio, 30/10/26)**; `gocreate.mx` | En produccion (mismo despliegue) |
| 9 Mejora continua | Activa (meta mensual, reporte HTML, paquetes delegados) | Activa (fotos reemplazables, fecha de regreso editable, firma guardada) |

Fecha de produccion: Observatorio dice desde el 10/08/26; el repo prueba `gocreate.mx` con datos reales el 27/08/26 y la Mac mini el 01/09/26 (ver `status.md`, «Por conciliar con Damian»).

## 8. Dependencias

- Servicios: Cloudflare (dominio `gocreate.mx` y tunel), Tailscale (acceso SSH de deploy). Correo SMTP corporativo GO: implementado, estado en produccion Por confirmar.
- `reportlab` y `pillow` (PDF y validacion de imagen) ya estan en `backend/requirements.txt`.
- Fuentes de marca Blauer Nue / Conthic en woff2 desde `context_desing_go`: **siguen pendientes** (`frontend/src/design/fonts.css` usa pila de respaldo).
- Dominio y su costo: resueltos (BACKLOG T4/T5). Siguen abiertos con marketing: nombres+correos del area, inventario de camaras/luces/tripies y razon social emisora (BACKLOG T1-T3), segun lo ya sembrado en produccion Por confirmar.

## 9. Riesgos

Ver `RISKS.md`. Top 3 al 05/11/26:
1. Respaldos solo en cada deploy (7 copias, misma maquina, sin cifrar); `uploads/` guarda las responsivas firmadas.
2. Sin cabeceras de seguridad (CSP, HSTS, `nosniff`) en la app; HTTPS ya lo da Cloudflare. Ver `SECURITY.md`.
3. Datos sensibles de Equipos (fotos, firmas, responsivas): hoy protegidos por endpoint con sesion y participacion; la firma no es firma electronica avanzada.

## 10. Metricas

- MVP total: 91% (30/33) segun `MVP_BREAKDOWN.md`; plan original A+B 88% (22/25). Observatorio (Damian, 30/10/26): 100% — Por conciliar con Damian
- Semaforo: Verde (Observatorio, 30/10/26)
- Pruebas: 786 funciones `def test_` en `backend/tests` (conteo por busqueda) + 11 specs e2e Playwright. Otras cifras en docs (680, 801, 871+) son de otras fechas
- Datos de produccion al 27/08/26 (droplet): 27 usuarios, 7 creadores, 26 tickets, 9 equipos, 3 razones sociales. Cifras actuales Por confirmar con Damian

## 11. Seguridad

`SECURITY.md` existe desde el 05/11/26 (describe lo que hace el codigo y 13 gaps abiertos). Diagnostico previo: `docs/seguridad/diagnostico-seguridad-2026-08-18.md`. Resumen: cookies httpOnly, refresh rotativo, RBAC deny-by-default, subidas de Equipos por firma de bytes, media y PDF solo por endpoint con participacion, responsiva versionada con sha256. Abiertos: cabeceras de seguridad, respaldos programados, rate limit en memoria, comprobantes de ticket sin validar firma de bytes.

## 12. Diseno visual

- Aplica `context_desing_go`: si (colores). Tipografia oficial: decidida 27/07, se implementa en WP7.
- Direccion: liquid glass dark-first, naranja `#FB670B` como unico acento. Ver `DESIGN_SYSTEM.md`.

## 13. Automatizacion

Deploy por releases en la Mac mini: `sudo /opt/go/bin/deploy-app.sh gocreate` (respaldo de DB y `uploads/`, health check y rollback automatico; `docs/deploy/deploy-app.sh`). El recordatorio diario de prestamos vencidos se **retiro el 14/09/26** (`docs/deploy/recordatorios_launchagent.md`); no hay tareas programadas.

## 14. Estado actual (05/11/26)

Presupuestos y Control de Equipos estan construidos y en produccion. Presupuestos: ciclos, tickets con varias fotos, validacion, gastos generales y operativos, dashboard con graficas, meta de gasto mensual y reporte HTML. Equipos: inventario, prestamos con fotos reemplazables y fecha de regreso editable, firmas (pendiente al confirmar, titular, firma guardada), responsiva PDF versionada, aprobaciones, creadores como beneficiarios, correo con copia oculta. Administracion: roles y paquetes aditivos, auditoria, auto-desbloqueo, `ADMIN_USUARIOS`. Ultimo commit: 19/10/26.

## 15. Siguiente paso

1. Sembrar `ADMIN_USUARIOS` en produccion (`migrate_rbac_aditivo.py`).
2. Cabeceras de seguridad y respaldos programados (BACKLOG #8 y #3).
3. Confirmar con Damian: fecha de produccion, estado del correo y fuentes de marca.
