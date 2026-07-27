# status.md — Ready2Go (Presupuestos + Control de Equipos)

- Fase: **3.5 Planeacion Quirurgica** (modulo Control de Equipos) · Presupuestos sigue en Fase 5
- Clasificacion: Herramienta interna — desarrollo activo
- Owner: Damian (marketing) · Supervision: Jose Aguilar
- Semaforo: Verde
- Fecha de corte: 27/07/26
- Ultima auditoria de docs: 27/07/26
- En produccion: no

## Estado

Repo renombrado de `presupuesto_creadores` a **Ready2Go** (remote `github.com/integracionesia-maker/Ready2Go`, rama `jose-branch` creada para supervision). El proyecto absorbe el sistema de **Control de Prestamo de Equipo** pedido por marketing en la reunion del 27/07 (Emily Perez, Betzabet Fuentes; Melisa aprueba).

Plan quirurgico completo entregado el mismo dia: `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` — RBAC aditivo estilo Bruckner, modelo de datos de 11 tablas nuevas, maquina de estados del prestamo, PDF de responsiva en servidor versionado, notificaciones SMTP con log e idempotencia, y direccion visual liquid glass para toda la app. Incluye 22 hallazgos de revision adversarial (5 criticos) resueltos en el diseno antes de escribir codigo.

Modulo Presupuestos sin cambios funcionales esta semana: sigue operando local con auth, roles, ciclos, validacion de tickets, gastos generales, borrado logico/fisico y responsividad movil.

## Bloqueo principal

**Esperando luz verde de Jose para construir.** El plan esta aprobado como diseno, no como orden de build.

Dependencias de marketing (bloquean fases, no el plan): tabla de nombres+correos GO del area, inventario de camaras/luces/tripies, confirmacion de la razon social emisora de la responsiva, nombre de dominio, y aprobacion firmada de Melisa para el costo del dominio (~11 USD/ano).

## Siguiente accion

1. Revision del plan por Jose.
2. Con luz verde: WP1 — RBAC aditivo (pruebas primero, luego motor `rbac.py`, luego migracion idempotente).

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
