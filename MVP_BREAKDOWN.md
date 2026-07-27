# MVP Breakdown — Ready2Go (Presupuestos + Control de Equipos)

> Formula: `% MVP = completados / total * 100`
> Alcance ampliado el 2026-07-27: el proyecto absorbe el modulo Control de Equipos. El % total **baja** porque el denominador crecio, no porque se haya perdido trabajo.

---

## Modulo A — Presupuestos (Fase 5)

| # | Entregable | Descripcion | Estado | Evidencia |
|---|---|---|---|---|
| A1 | CRUD creadores/marcas | Alta, listado, edicion | Hecho | `routers/creators.py`, `brands.py` |
| A2 | Tickets con comprobante | Gasto + archivo (PNG/JPG/PDF) por creador y marca | Hecho | `routers/tickets.py`, `UploadTicketModal.jsx` |
| A3 | Ciclos de presupuesto | Ciclos semanal/mensual, snapshot inmutable | Hecho | `doc/presupuestos-y-validacion.md` |
| A4 | Validacion de tickets | `pendiente → aprobado/rechazado`, cola de validacion | Hecho | `ValidationQueue.jsx`, `test_ticket_validation.py` |
| A5 | Gastos generales | Tabla independiente, por marca, soft/hard delete | Hecho | `routers/general_expenses.py`, `doc/gastos-generales-manual.md` |
| A6 | Borrado logico/fisico de tickets | Con reversion de ciclo si estaba aprobado | Hecho | `doc/borrado-tickets.md` |
| A7 | Dashboard analytics | Endpoints + KPIs + 4 graficos ApexCharts + PDF | Hecho | `routers/dashboard.py`, `components/charts/*` |
| A8 | Responsividad movil | Usable desde 320px, `RowActions`, scroll de tablas | Hecho | `doc/responsividad-movil.md` |
| A9 | Control de versiones | Repo git con historial real | Hecho | `github.com/integracionesia-maker/Ready2Go` |
| A10 | Autenticacion y roles | JWT cookie httpOnly, refresh rotativo, rate limit, 3 roles | Hecho | `doc/auth-arquitectura.md`, 167 pruebas |
| A11 | Tests automatizados | Cobertura backend | **Parcial** | 167 pytest (auth/permisos/ciclos/validacion/borrado). Sin cobertura de CRUD puro de creadores/marcas — ver RISKS #4 |
| A12 | Migracion visual al shell nuevo | Presupuestos sobre el design system liquid glass | Pendiente | WP7 del plan |
| A13 | Deploy | Entorno accesible por el equipo (dominio + HTTPS) | Pendiente | WP9 del plan |

**Modulo A: 10 de 13 (77%)**

---

## Modulo B — Control de Equipos (Fase 3.5, plan aprobado)

| # | Entregable | Descripcion | Estado | WP |
|---|---|---|---|---|
| B1 | RBAC aditivo | `roles` + `role_permissions` + `user_role_grants`, motor deny-by-default, 503 en fallo de DB | Pendiente | WP1 |
| B2 | Modelo de datos de equipos | 11 tablas, indice unico parcial de disponibilidad, seeds (8 equipos + 2 razones sociales) | Pendiente | WP2 |
| B3 | API inventario | CRUD + auditorias de condicion + ficha con historial | Pendiente | WP3 |
| B4 | API prestamos | Borrador, items, media, confirmar, cancelar, devolucion, historial, export | Pendiente | WP4 |
| B5 | API aprobacion | Autorizar entrega, confirmar devolucion por equipo, cerrar incidencia | Pendiente | WP4 |
| B6 | Carta responsiva PDF | Generacion en servidor (reportlab), folio, firmas, texto legal, versionado con hash | Pendiente | WP5 |
| B7 | Notificaciones por correo | SMTP GO, log con idempotencia, reintentos, recordatorio de vencimiento | Pendiente | WP6 |
| B8 | Shell liquid glass + tokens | Primitivas de cristal, fuentes de marca, animacion con `motion`, dark/light | Pendiente | WP7 |
| B9 | Frontend inventario | Busqueda, filtros, ficha, alta/edicion, auditoria de condicion | Pendiente | WP8 |
| B10 | Frontend prestamo | Wizard 4 pasos + firma en canvas + captura de fotos frente/atras | Pendiente | WP8 |
| B11 | Frontend aprobaciones + historial | Bandeja de la aprobadora, fotos antes/despues, bitacora, export | Pendiente | WP8 |
| B12 | Tests del modulo | pytest (maquina de estados, permisos, invariantes) + e2e del flujo completo | Pendiente | WP8/WP9 |

**Modulo B: 0 de 12 (0%)**

---

## Total

- **Completados:** 10 de 25
- **% MVP total:** **40%**
- **Ultimo cerrado:** A8 Responsividad movil — 23 Jul 2026
- **Siguiente:** B1 RBAC aditivo (bloqueado por luz verde de build)

**Definition of Done:** codigo funciona + pruebas pasan + verificado en pantalla (desktop y 390px) + evidencia en `avances_diarios.md` + owner confirma.
