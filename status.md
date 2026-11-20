# status.md — GOCreate (Presupuestos + Control de Equipos)

- Fase: **8 Produccion** (Observatorio, Damian, 30/10/26). Presupuestos y Control de Equipos operando; mejora continua en paralelo
- Clasificacion: Herramienta interna — en produccion
- Owner: Damian (marketing) · Supervision: Jose Aguilar
- Carriles: servidor y datos (`dami-branch`) · interfaz (`BeniBranch`) · integracion (`jose-branch`)
- Semaforo: Verde (Observatorio, 30/10/26; sin bloqueo en el repo)
- Fecha de corte: 05/11/26
- Ultima auditoria de docs: 05/11/26
- En produccion: **Si** — `https://gocreate.mx`, Mac mini de marketing, tunel Cloudflare hacia uvicorn `127.0.0.1:8000`, un worker (`docs/deploy/migracion-macmini.md`, `docs/deploy/acceso-deploy-gocreate.md`)

## Fecha de produccion (Por conciliar con Damian)

| Fuente | Dice |
|---|---|
| Observatorio (Damian, 30/10/26) | En produccion desde el **10/08/26** |
| Repo — lo demostrable mas antiguo | `gocreate.mx` servido desde un droplet con datos reales el **27/08/26** (inventario de `migracion-macmini.md`: 27 usuarios, 26 tickets, 9 equipos) |
| Repo — Mac mini | Ya sirve produccion el **01/09/26** (`despliegue-continuo-multi-app.md`); guia de acceso y deploy continuo el **14/09/26** |
| `CLAUDE.md` | «desde el 14/09» — es la fecha de la guia de deploy, no del primer despliegue |

El repo no tiene un despliegue fechado el 10/08; tampoco lo contradice. Se conserva el 10/08 como fecha del Observatorio y el 27/08 como la mas antigua que prueba el repo.

## Estado

Control de Equipos esta **construido y en uso** (el plan quirurgico del 27/07 ya se ejecuto): RBAC aditivo, inventario, prestamos con fotos y firmas, carta responsiva PDF versionada con hash, aprobaciones, correo con copia oculta. Presupuestos: ciclos, tickets con varias fotos, gastos generales y operativos, dashboard.

Mejoras recientes (git log, mas nueva primero):
- 19/10: paquete `ADMIN_USUARIOS` (administrar cuentas sin ser superadmin) y cambio de rol a/desde `creador` conserva el perfil. **Pendiente correr `migrate_rbac_aditivo.py` en produccion.**
- 09/10: reporte del dashboard como HTML autocontenido (reemplaza al PDF) · 06/10: firma predeterminada del perfil.
- 25/09: correo de confirmacion solo a los involucrados directos · 15/09: fotos de entrega reemplazables y **meta de gasto mensual** con modo periodo unico del dashboard.
- 14/09: **fecha de regreso editable** en prestamos, **copia oculta (BCC)** en todo correo, auto-desbloqueo con rompecabezas. 08/09: dashboard con graficas variadas.
- 07/09: creadores como beneficiarios de prestamos · 04/09: rediseno de firmas y titular de la firma de entrega.

Detalle: `CHANGELOG.md` (hasta 19/10/26). Reglas vigentes: `CLAUDE.md`.

## Bloqueo principal

**Ninguno** (Observatorio). Pendientes que no detienen operacion: ver `BACKLOG.md`.

## Siguiente accion

1. Cabeceras de seguridad (CSP, HSTS, `nosniff`) y su verificacion en el borde; ver `SECURITY.md` gaps 1-2.
2. Respaldos programados de DB y `uploads/` (hoy solo en cada deploy); BACKLOG #3.
3. Correr `migrate_rbac_aditivo.py` en produccion para sembrar `ADMIN_USUARIOS`.
4. Confirmar con Damian el estado real del correo en produccion (`NOTIF_ENABLED`, SMTP).

## Stack

FastAPI + SQLAlchemy + SQLite (backend) · Vite 6 + React 18.3.1 + Tailwind 3 + ApexCharts (frontend v1.1.0)
Deploy: produccion `https://gocreate.mx` (Mac mini); local `127.0.0.1:8000` (backend) / `127.0.0.1:5173` (frontend)

## Metricas tecnicas

| Metrica | Valor |
|---|---|
| % MVP (con modulo C) | 91% (30/33) — ver `MVP_BREAKDOWN.md`. Observatorio: 100% (Por conciliar con Damian) |
| % MVP (plan original, A+B) | 88% (22/25) |
| Pruebas backend | 786 funciones `def test_` en `backend/tests` (conteo por busqueda, no ejecutadas) |
| Suites e2e | 11 specs Playwright en `frontend/e2e` |
| Control de versiones | Si — `github.com/integracionesia-maker/Ready2Go`, 211 commits, ultimo 19/10/26 |
| Datos de produccion (27/08/26, droplet) | 27 usuarios, 7 creadores, 26 tickets, 9 equipos, 3 razones sociales |

## Metricas de impacto (Control de Equipos)

| Metrica | Antes | Despues (implementado; adopcion Por confirmar con Damian) |
|---|---|---|
| Saber quien tiene un equipo | Memoria y mensajes | Consulta en pantalla con fecha de regreso (editable) |
| Carta responsiva | Papel | PDF con folio, firmas en pantalla, version nueva por cada firma |
| Evidencia del estado | Fotos sueltas | Fotos frente+atras con sha256, reemplazables en entrega |
| Autorizacion | Verbal / papel | Registrada por rol, con usuario y fecha |
| Deteccion de atrasos | Ninguna | Recordatorio diario **retirado** el 14/09/26; solo hay correo al confirmar |

## Seguridad

`SECURITY.md` creado el 05/11/26 con 13 gaps abiertos. Los principales: sin cabeceras de seguridad en la app, respaldos solo al desplegar, rate limit de login en memoria de un proceso, comprobantes de ticket sin validar firma de bytes.

## KPI History

| Semana | Semaforo | Bloqueo |
|---|---|---|
| Sem 29 (15 Jul 2026) | Verde | ninguno |
| Sem 31 (27 Jul 2026) | Verde | esperando luz verde de build del modulo Equipos |
| Sem 44 (30 Oct 2026) | Verde | ninguno (Observatorio: fase 8) |
| Sem 45 (05 Nov 2026) | Verde | ninguno |
