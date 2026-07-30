# Sistema de Borrado de Tickets y Gastos Generales (R12)

> Feature del paquete R12 (`docs/historico/plan-gastos-generales-y-borrado-tickets.md`). Complementa `docs/presupuestos/presupuestos-y-validacion.md` (estados de ticket, ciclos) y `docs/presupuestos/gastos-generales-manual.md`.

## Por qué dos niveles de borrado

Un ticket (o gasto general) puede haberse subido por error, duplicado, o corresponder a un comprobante inválido. Borrarlo de inmediato y sin rastro sería arriesgado (pérdida de auditoría, imposible de revertir); nunca poder borrarlo tampoco sirve (basura acumulada en reportes). Por eso hay dos niveles, cada uno con su propio endpoint y su propia confirmación en la UI.

## Borrado lógico (soft delete)

- El registro se marca `is_deleted = True`, `deleted_at = ahora`, `deleted_by_user_id = quién lo hizo`.
- Ya **no** aparece en: listados (Transacciones, Validación, historial de Gastos Generales), el Dashboard (KPIs, gráficas, desglose por marca/creador), ni en ninguna exportación.
- Si el ticket estaba **aprobado**, su monto se **revierte** del ciclo de presupuesto asignado: `cycle.spent = max(0, cycle.spent - amount)` — nunca queda negativo por esta operación. Si estaba `pendiente` o `rechazado`, no hay nada que revertir (nunca descontó).
- El archivo comprobante se **conserva** en disco.
- El registro permanece en la base de datos — sigue siendo auditable (quién y cuándo lo borró).
- Los gastos generales no tienen ciclo, así que su borrado lógico nunca revierte nada — solo deja de contar.

Endpoints: `POST /api/tickets/{id}/soft-delete`, `POST /api/general-expenses/{id}/soft-delete`.

## Borrado físico (hard delete)

- El registro se **elimina** de la base de datos.
- El archivo comprobante se **borra** del disco.
- Si el ticket estaba aprobado y **no** había sido soft-deleted previamente, también revierte el monto del ciclo (misma regla `max(0, ...)`). Si ya estaba soft-deleted, el ciclo ya se revirtió antes — no se revierte una segunda vez.
- ⚠️ **Irreversible** — no hay forma de recuperar el registro ni el archivo. La UI exige un paso adicional de confirmación con una advertencia en rojo antes de llamar a este endpoint (nunca se ejecuta con un solo click).

Endpoints: `DELETE /api/tickets/{id}/permanent`, `DELETE /api/general-expenses/{id}/permanent`.

## Permisos

Solo `admin` y `superadmin` pueden borrar (lógica o físicamente) tickets o gastos generales. Un `creador` no ve ningún botón de eliminar en Transacciones (aunque comparte esa vista con admin/superadmin) y recibe `403` si intenta llamar a estos endpoints directamente.

## Impacto en el estado y en los cálculos

El borrado **no cambia** el `status` del ticket (`pendiente`/`aprobado`/`rechazado`) — es una dimensión independiente (`is_deleted`). Un ticket puede seguir marcado `aprobado` en la base de datos y a la vez estar `is_deleted=True`; para todo propósito práctico de la app, un ticket borrado simplemente deja de existir en cualquier lugar donde se lean tickets.

| Estado del ticket al borrarlo | Soft delete | Hard delete |
|---|---|---|
| Pendiente | No revierte (nunca descontó) | No revierte |
| Aprobado | Revierte descuento del ciclo | Revierte descuento del ciclo (si no se había revertido ya por un soft delete previo) |
| Rechazado | No revierte (nunca descontó) | No revierte |

Un ticket o gasto general ya borrado (lógica o físicamente) no puede aprobarse ni rechazarse ni descargarse — los endpoints `aprobar`, `rechazar` y `file` devuelven `404` (se trata como si no existiera).

## Auditoría

Cada operación registra una entrada en `audit_log`: `ticket.soft-delete`, `ticket.hard-delete`, `general-expense.soft-delete`, `general-expense.hard-delete`, con el usuario que la ejecutó.

## Pruebas que cubren estas reglas

- `backend/tests/test_ticket_soft_delete.py`: reversión de ciclo en soft/hard delete de un ticket aprobado, sin reversión si estaba pendiente/rechazado, que un soft delete seguido de un hard delete no revierta el ciclo dos veces, exclusión de listados/dashboard/brand-spend, que un ticket borrado no pueda aprobarse/rechazarse/descargarse, permisos (403 para creador).
- `backend/tests/test_general_expenses.py`: creación, listado con y sin filtro de fecha, exclusión de borrados en listado/gráfica mensual/exportación, soft/hard delete, permisos.
- `backend/tests/test_budget_cycles.py`: `test_soft_delete_reverts_cycle_spent` (a nivel de `crud`, complementa las pruebas de endpoint de `test_ticket_soft_delete.py`).
- `backend/tests/test_ticket_validation.py`: `test_soft_deleted_pending_ticket_not_in_validation_queue`.
- `frontend/e2e/gastos-generales.spec.js`: flujo completo desde la UI (crear, exportar, soft/hard delete con advertencia, reflejo en Dashboard y Transacciones).
