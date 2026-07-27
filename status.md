# status.md — Ready2Go (Presupuestos + Control de Equipos)

- Fase: **5 Build** (modulo Control de Equipos, arranca 27/07) · Presupuestos sigue en Fase 5
- Clasificacion: Herramienta interna — desarrollo activo
- Owner: Damian (marketing) · Supervision: Jose Aguilar
- Carriles: servidor y datos (`dami-branch`) · interfaz (`BeniBranch`) · integracion (`jose-branch`)
- Semaforo: Verde
- Fecha de corte: 27/07/26
- Ultima auditoria de docs: 27/07/26
- En produccion: no

## Estado

Repo renombrado de `presupuesto_creadores` a **Ready2Go** (remote `github.com/integracionesia-maker/Ready2Go`, rama `jose-branch` creada para supervision). El proyecto absorbe el sistema de **Control de Prestamo de Equipo** pedido por marketing en la reunion del 27/07 (Emily Perez, Betzabet Fuentes; Melisa aprueba).

Plan quirurgico completo entregado el mismo dia: `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` — RBAC aditivo estilo Bruckner, modelo de datos de 11 tablas nuevas, maquina de estados del prestamo, PDF de responsiva en servidor versionado, notificaciones SMTP con log e idempotencia, y direccion visual liquid glass para toda la app. Incluye 22 hallazgos de revision adversarial (5 criticos) resueltos en el diseno antes de escribir codigo.

**Build autorizado el mismo dia.** El trabajo se partio en dos carriles con **interseccion de codigo cero**: la frontera es el contrato HTTP, no un archivo. Un carril vive dentro de `backend/`, el otro dentro de `frontend/`. De 47 archivos que se habrian disputado, 41 quedan con dueno unico por pertenencia de capa y los 6 restantes (documentos de gobernanza de la raiz) los toca solo la integracion. El contrato congelado v1 esta publicado en `docs/contratos/` y cada carril tiene su asignacion en su propia rama.

Modulo Presupuestos sin cambios funcionales esta semana: sigue operando local con auth, roles, ciclos, validacion de tickets, gastos generales, borrado logico/fisico y responsividad movil.

## Bloqueo principal

**Ninguno.** Build autorizado el 27/07. Los dos carriles pueden trabajar desde hoy sin depender de nadie.

Pendientes de marketing que se cierran al final y **no detienen codigo**: nombres+correos del area (se siembran usuarios de prueba), inventario de camaras/luces/tripies (se siembra con los 8 equipos ya auditados), razon social emisora (sale de la tabla `empresa`), credenciales SMTP (`NOTIF_ENABLED=false`), fuentes de marca (pila de respaldo con `font-display: swap`). Dominio: diferido por decision de Jose, no es necesario para desarrollo. Costo del dominio: aprobado por Melisa por correo el 27/07.

## Siguiente accion

1. Los dos carriles arrancan por su tarea 0 (mecanica, aislada, sin logica).
2. Generar `openapi_equipos_v1.json` en cuanto existan los primeros endpoints y congelarlo; hasta entonces la prueba guardia va en `skip`.
3. Primer punto de integracion: inventario real contra el servidor (ensayo temprano y barato de la deriva de contrato).

## Stack

FastAPI + SQLAlchemy + SQLite (backend) · Vite 6 + React 18.3.1 + Tailwind 3 + ApexCharts (frontend)
Deploy: ninguno — local `127.0.0.1:8000` (backend) / `127.0.0.1:5173` (frontend)

## Metricas tecnicas

| Metrica | Valor |
|---|---|
| % MVP (dos modulos) | 40% — ver `MVP_BREAKDOWN.md` |
| % MVP (solo Presupuestos) | 77% (10/13) |
| Creadores activos | 6 |
| Marcas activas | 8 |
| Tickets totales | 89 |
| Historial de datos | 12 meses (Ago 2025 - Jul 2026) |
| Equipos listos para seed | 8 (auditoria fisica del 10/06/26) |
| Pruebas backend | 167 pytest |
| Suites e2e | 3 (Playwright) |
| Control de versiones | Si — `github.com/integracionesia-maker/Ready2Go` |

## Metricas de impacto (esperado del modulo Equipos)

| Metrica | Antes (hoy) | Despues (objetivo) |
|---|---|---|
| Saber quien tiene un equipo | Nadie sabe: memoria y mensajes | Consulta en pantalla, con fecha de regreso |
| Carta responsiva | Papel, se persigue firma de Melisa | PDF con folio, firmado en pantalla, por correo a ambas partes |
| Evidencia del estado del equipo | Ninguna, o fotos sueltas en Drive | Foto frente+atras obligatoria en entrega y devolucion, con hash |
| Autorizacion de prestamo | Verbal / papel | Registrada por rol, con usuario real y fecha |
| Deteccion de atrasos | Ninguna | Recordatorio diario automatico |

## Seguridad

Sin `SECURITY.md` formal todavia (BACKLOG). Gaps abiertos: HTTPS/CSP/HSTS, backups automaticos de DB y `uploads/`, rate limit de login en memoria de un solo proceso. El plan de Equipos agrega requisitos duros de subida de archivos (magic bytes, limites) y de autorizacion en media/PDF (evitar el IDOR que ya se corrigio una vez en comprobantes de tickets).

## KPI History

| Semana | Semaforo | Bloqueo |
|---|---|---|
| Sem 29 (15 Jul 2026) | Verde | ninguno |
| Sem 31 (27 Jul 2026) | Verde | esperando luz verde de build del modulo Equipos |
