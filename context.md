# Contexto — Ready2Go (Plataforma de Marketing: Presupuestos + Control de Equipos)

> Conexiones pool: [[CLAUDE]] | [[context_proyectos]] | [[framework_operative_enforcement/CLAUDE]] | [[framework_operative_enforcement/PLAYBOOK]] | [[framework_operative_enforcement/FRAMEWORK]]
> Recursos: [[IDENTIDAD DE MARCA/context_design]] (visual)
> Archivos del proyecto: [[CLAUDE]] | [[status]] | [[BACKLOG]] | [[RISKS]] | [[MVP_BREAKDOWN]] | [[DESIGN_SYSTEM]] | [[CHANGELOG]] | [[avances_diarios]] | [[docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26]]

## 1. Resumen

- Proyecto: **Ready2Go** — plataforma interna del area de marketing (antes `presupuesto_creadores`, renombrado 2026-07-27)
- Departamento: Inteligencia Operativa / Marketing (Grupo Ortiz)
- Owner: Damian (marketing) — supervision: Jose Aguilar
- Repo: `github.com/integracionesia-maker/Ready2Go` · ramas: `master`, `dami-branch`, `jose-branch`, `BeniBranch`
- Estado: modulo Presupuestos en Fase 5 (uso interno local); modulo Control de Equipos en **Fase 3.5 (plan aprobado, sin construir)**
- Ultima actualizacion: 2026-07-27 (integracion de Control de Equipos: plan quirurgico, RBAC aditivo, direccion visual liquid glass)
- Clasificacion: Herramienta interna — desarrollo activo

## 2. Problema

Dos problemas del mismo area, hasta hoy sin sistema:

1. **Presupuestos.** El equipo necesita controlar el presupuesto asignado a cada creador de contenido: cuanto se le asigno por ciclo, cuanto gasto (por ticket con comprobante), cuanto le queda, por marca y periodo.
2. **Prestamo de equipo.** Marketing presta equipo de grabacion (celulares, micros RODE y DJI, estabilizadores Osmo, camaras, luces, tripies) sin control real: no hay registro de quien tiene que equipo, ni responsiva digital, ni evidencia del estado en que salio y volvio, ni flujo de autorizacion. Hoy se persigue a la aprobadora con un formulario en papel para que lo firme.

## 3. Objetivo

Una sola plataforma, un login, dos modulos:

**Presupuestos** (existente): creadores + ciclos semanal/mensual, tickets con comprobante y validacion, gastos generales por marca, borrado logico/fisico, dashboard con KPIs y graficos, reporte PDF.

**Control de Equipos** (plan aprobado): inventario con ficha e historial de auditorias de condicion, prestamo con seleccion de equipos y accesorios, foto frente+atras obligatoria por equipo en entrega y devolucion, firma digital de quien entrega y quien recibe, carta responsiva en PDF generada en servidor con folio, autorizacion de entrega y confirmacion de devolucion por la aprobadora, notificacion por correo, historial exportable.

## 4. Usuarios

| Perfil | Quien | Que hace |
|---|---|---|
| `superadmin` | Damian, Jose | Todo, incluida gestion de usuarios y roles |
| `admin` | Marketing (presupuestos) | Presupuestos completo + operacion de equipos. Sin gestion de usuarios (R4) |
| `creador` | Creadores de contenido | Sube sus tickets, ve solo lo propio |
| `colaborador_mkt` (nuevo) | Area de marketing | Pide equipo, ve su propio historial. Nada de presupuestos |
| `APROBADOR_EQUIPO` (aditivo) | Melisa | Autoriza entregas, confirma devoluciones, cierra incidencias |
| `CUSTODIO_EQUIPO` (aditivo) | A definir con el area | Alta/edicion/auditoria/baja de inventario |

Roles aditivos: se suman al rol base, no lo reemplazan. Matriz completa: §3 del plan quirurgico.

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

- Backend: FastAPI + SQLAlchemy + SQLite (`backend/presupuesto.db`), routers `auth users creators brands tickets dashboard general_expenses` (+ `equipment loans approvals notifications` por construir)
- Frontend: Vite 6 + React 18.3.1 + Tailwind 3 + ApexCharts. 100% React (cero HTML/JS suelto)
- Auth: JWT en cookie httpOnly + refresh token rotativo, rate limit de login, 167 pruebas
- PDF: cliente (`jspdf` + `html2canvas`, reporte de dashboard) y servidor (`reportlab`, carta responsiva — por construir)
- Correo: SMTP corporativo GO (por construir)
- Sin deploy — local `127.0.0.1:8000` / `127.0.0.1:5173`

## 7. Tabla de fases

| Fase | Presupuestos | Control de Equipos |
|---|---|---|
| 0 Intake | Hecho | Hecho (reunion mkt 27/07) |
| 1 Descubrimiento | Hecho | Hecho (transcript + maqueta HTML) |
| 2 Clasificacion | Hecho | Hecho (herramienta interna) |
| 3 Diseno operativo | Hecho | Hecho (flujo y roles en el plan) |
| 3.5 Planeacion Quirurgica | n/a | **Hecho — plan aprobado 27/07, esperando luz verde de build** |
| 4 Diseno tecnico | Hecho | Hecho (modelo de datos + API + RBAC en el plan) |
| 5 Build | En curso | No iniciado |
| 6 Revision critica | Pendiente | Pendiente |
| 7 Piloto | Pendiente | Pendiente (Emily, Betzabet, Melisa) |
| 8 Produccion | Pendiente (falta dominio + HTTPS) | Pendiente |
| 9 Mejora continua | — | — |

## 8. Dependencias

- Ninguna API externa hoy. Por agregar: cuenta SMTP corporativa GO.
- `reportlab` (PDF servidor), `motion` (animacion) — por agregar en el build.
- Fuentes de marca Blauer Nue / Conthic en woff2 desde `context_desing_go`.
- Pendientes de marketing que bloquean fases (no el plan): tabla de nombres+correos del area, inventario de camaras/luces/tripies, confirmacion de la razon social emisora de la responsiva, nombre de dominio, aprobacion firmada del costo del dominio (~11 USD/ano).

## 9. Riesgos

Ver `RISKS.md`. Top 3 hoy:
1. Sin HTTPS/CSP/HSTS — bloquea exponer la app fuera de `127.0.0.1`, y el modulo de equipos no sirve en local: los colaboradores lo usan desde su celular.
2. La superficie de datos sensibles crece: fotos de equipo, firmas y cartas responsivas son evidencia; un IDOR ahi filtra documentos firmados de personas (ya paso una vez con comprobantes de tickets, corregido).
3. Sin backups automaticos de `presupuesto.db` ni de `uploads/` — y con el modulo de equipos, `uploads/` pasa a contener las responsivas firmadas.

## 10. Metricas

- MVP total (dos modulos): ver `MVP_BREAKDOWN.md` — 40% (el porcentaje baja porque el alcance crecio, no porque se perdiera trabajo)
- Semaforo: Verde (plan cerrado el mismo dia de la reunion, sin bloqueos internos)
- Pruebas: 167 pytest (auth, permisos, ciclos, validacion, borrado, gastos generales) + 3 suites e2e Playwright
- Datos: 6 creadores, 8 marcas, 89 tickets, 12 meses de historial. Inventario: 8 equipos ya auditados (10/06/2026) listos para seed

## 11. Seguridad

`SECURITY.md` sigue pendiente de crear (BACKLOG). Gaps: sin HTTPS/CSP/HSTS, sin backups automaticos, rate limit de login en memoria de un solo proceso. El plan de equipos suma requisitos: validacion de subidas por magic bytes, media y PDF servidos solo por endpoint autenticado con autorizacion por participacion, y PDF de responsiva versionado con hash (nunca sobrescrito).

## 12. Diseno visual

- Aplica `context_desing_go`: si (colores). Tipografia oficial: decidida 27/07, se implementa en WP7.
- Direccion: liquid glass dark-first, naranja `#FB670B` como unico acento. Ver `DESIGN_SYSTEM.md`.

## 13. Automatizacion

Hoy manual (levantar servidores, seed). Por agregar: recordatorio diario de prestamos vencidos como LaunchAgent del Mac mini (mismo patron que `doc/deploy-runbook.md`), no cron dentro de uvicorn.

## 14. Estado actual

Presupuestos funciona local con auth, roles, ciclos, validacion, gastos generales, borrado logico/fisico, dashboard y responsividad movil. Control de Equipos tiene plan quirurgico completo (modelo de datos, API, RBAC aditivo, PDF, correo, frontend liquid glass) con 22 hallazgos adversariales documentados y mitigados en el diseno. Cero codigo del modulo nuevo escrito: espera luz verde.

## 15. Siguiente paso

1. Jose revisa `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` y da (o no) luz verde de build.
2. Marketing entrega los pendientes de §14 del plan (usuarios, inventario, razon social, dominio, aprobacion del gasto).
3. Con luz verde: WP1 (RBAC aditivo) — primero pruebas, luego motor, luego migracion.
