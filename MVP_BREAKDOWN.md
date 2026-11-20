# MVP Breakdown — GOCreate (Presupuestos + Control de Equipos)

> Formula: `% MVP = completados / total * 100`. Solo cuenta **Hecho**; Parcial y Pendiente valen 0. Corte: 2026-11-05.
> Alcance ampliado el 2026-07-27 (se absorbe Control de Equipos). Actualizado el 2026-11-05: el modulo B se construyo y se agrego el modulo C con lo entregado fuera del plan original.

---

## Modulo A — Presupuestos

| # | Entregable | Descripcion | Estado | Evidencia |
|---|---|---|---|---|
| A1 | CRUD creadores/marcas | Alta, listado, edicion | Hecho | `routers/creators.py`, `brands.py` |
| A2 | Tickets con comprobante | Gasto + archivos (PNG/JPG/PDF), varios por ticket | Hecho | `routers/tickets.py`; `35cca99` |
| A3 | Ciclos de presupuesto | Ciclos semanal/mensual, snapshot inmutable | Hecho | `docs/presupuestos/presupuestos-y-validacion.md` |
| A4 | Validacion de tickets | `pendiente → aprobado/rechazado`, cola de validacion | Hecho | `ValidationQueue.jsx`, `test_ticket_validation.py` |
| A5 | Gastos generales | Tabla independiente, por marca, soft/hard delete | Hecho | `routers/general_expenses.py`, `docs/presupuestos/gastos-generales-manual.md` |
| A6 | Borrado logico/fisico de tickets | Con reversion de ciclo si estaba aprobado | Hecho | `docs/presupuestos/borrado-tickets.md` |
| A7 | Dashboard analytics | KPIs ordenables, graficas variadas, top gastos | Hecho | `routers/dashboard.py`; `b6fcfb9`, `eedd026` |
| A8 | Responsividad movil | Usable desde 320px, `RowActions`, scroll de tablas | Hecho | `docs/presupuestos/responsividad-movil.md` |
| A9 | Control de versiones | Repo git con historial real | Hecho | `github.com/integracionesia-maker/Ready2Go` (211 commits) |
| A10 | Autenticacion y roles | JWT en cookie httpOnly, refresh rotativo, bloqueo y rate limit | Hecho | `docs/presupuestos/auth/auth-arquitectura.md`, `test_auth.py` |
| A11 | Tests automatizados | Cobertura backend | **Parcial** | 786 funciones `def test_`; sigue sin cobertura de CRUD puro de creadores/marcas (BACKLOG #4) |
| A12 | Migracion visual al shell nuevo | Presupuestos sobre las primitivas de cristal | Hecho | `frontend/src/design/Glass*.jsx` usadas en `modules/presupuestos`; fuentes de marca woff2 siguen pendientes (BACKLOG T7) |
| A13 | Deploy | Entorno accesible por el equipo (dominio + HTTPS) | Hecho | `https://gocreate.mx`; `docs/deploy/acceso-deploy-gocreate.md` |

**Modulo A: 12 de 13 (92%)**

---

## Modulo B — Control de Equipos

| # | Entregable | Descripcion | Estado | Evidencia |
|---|---|---|---|---|
| B1 | RBAC aditivo | Catalogo, motor deny-by-default, 503 en fallo de DB | Hecho | `app/rbac.py`, `rbac_catalog.py`, `tests/rbac/` |
| B2 | Modelo de datos de equipos | Inventario, prestamos, media, responsivas, folio, indice de disponibilidad | Hecho | `models_equipos.py`, `migrate_equipos.py` |
| B3 | API inventario | CRUD + auditorias de condicion + ficha con historial | Hecho | `routers/equipment.py`, `tests/equipos/test_api_inventario.py` |
| B4 | API prestamos | Borrador, items, media, confirmar, cancelar, devolucion, historial, fecha de regreso editable | Hecho | `routers/loans.py`; `4838ebc` |
| B5 | API aprobacion | Autorizar entrega, confirmar devolucion, cerrar incidencia | Hecho | `routers/approvals.py`, `tests/equipos/test_aprobacion.py` |
| B6 | Carta responsiva PDF | Servidor (reportlab), folio, firmas, versionado con sha256 | Hecho | `app/pdf/responsiva.py`, `tests/equipos/test_responsiva_pdf.py` |
| B7 | Notificaciones por correo | SMTP, log idempotente, BCC; recordatorio de vencimiento retirado el 14/09/26 | **Parcial** | `mailer.py`, `notificaciones.py`; `25d432f`; envio real en produccion Por confirmar con Damian |
| B8 | Shell liquid glass + tokens | Primitivas de cristal, dark/light; faltan fuentes de marca | **Parcial** | `frontend/src/design/`; BACKLOG T7 |
| B9 | Frontend inventario | Busqueda, filtros, ficha, alta/edicion, auditoria | Hecho | `modules/equipos/pages/InventarioPage.jsx` |
| B10 | Frontend prestamo | Wizard + firma en canvas + fotos frente/atras | Hecho | `modules/equipos/pages/NuevoPrestamoPage.jsx` |
| B11 | Frontend aprobaciones + historial | Bandeja, ficha del prestamo, historial, dashboard de equipos | Hecho | `AprobacionesPage.jsx`, `FichaPrestamoPage.jsx`, `HistorialPage.jsx` |
| B12 | Tests del modulo | pytest + e2e del flujo completo | Hecho | `backend/tests/equipos/`, `frontend/e2e/equipos-*.spec.js` |

**Modulo B: 10 de 12 (83%)**

---

## Modulo C — Agregados despues del plan (jul-oct 2026)

| # | Entregable | Descripcion | Estado | Evidencia |
|---|---|---|---|---|
| C1 | Gastos Operativos | Gastos por rubro, fusionados con generales en la UI | Hecho | `4d90cd3`, `1bec7a3` |
| C2 | Meta de gasto mensual y periodo unico | Dos metas por mes, sugerencia automatica, comparativo | Hecho | `abf34cb`, `docs/presupuestos/meta-gasto-mensual.md` |
| C3 | Reporte del dashboard en HTML | Archivo autocontenido, reemplaza al PDF | Hecho | `a7cbdce`, `docs/presupuestos/reporte-html-dashboard.md` |
| C4 | Firmas de la responsiva | Firma pendiente al confirmar, titular de la firma, firma guardada del perfil | Hecho | `1854905`, `79ff3bd` |
| C5 | Creadores como beneficiarios | Lista de creadores en el wizard, autoasignacion | Hecho | `1cc05b1` |
| C6 | Fotos de entrega reemplazables | Reemplazo en cualquier momento del ciclo con bitacora | Hecho | `4c5ea3d`, `docs/equipos/fotos-entrega-reemplazables.md` |
| C7 | Seguridad de cuentas | Diagnostico del 18/08, auto-desbloqueo con rompecabezas | Hecho | `f58edb9`, `367de7f` |
| C8 | Paquetes delegados | `ADMIN_USUARIOS`, `APROBADOR_PRESUPUESTOS` | Hecho | `0676c64`, `b33fd23`; `ADMIN_USUARIOS` pendiente de sembrar en produccion |

**Modulo C: 8 de 8 (100%)**

---

## Total

- **Completados:** 30 de 33
- **% MVP total:** **91%** (solo plan original A+B: 22/25 = 88%)
- **Ultimo cerrado:** C8 Paquete `ADMIN_USUARIOS` — 19 Oct 2026
- **Siguiente:** A11 / BACKLOG #4 (pruebas de CRUD) y B7 (confirmar correo en produccion)
- **Por conciliar con Damian:** el Observatorio (30/10/26) dice 100%; la diferencia son A11, B7 y B8. Decide Damian si cuentan para el MVP.

**Definition of Done:** codigo funciona + pruebas pasan + verificado en pantalla (desktop y 390px) + evidencia en `avances_diarios.md` + owner confirma.
