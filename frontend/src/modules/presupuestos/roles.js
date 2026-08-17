/**
 * Conjuntos de roles del módulo de Presupuestos.
 *
 * Fuente única para las tres capas que tienen que coincidir o el menú miente:
 * las rutas (`PresupuestosLayout.jsx`), el menú lateral (`Sidebar.jsx`) y las
 * tarjetas de la portada (`pages/HomePage.jsx`). Si un item aparece en el menú
 * para un rol que la ruta manda a /403, el usuario ve una puerta que no abre.
 *
 * Espejo de los `require_role` del backend — si aquí se agrega un rol que allá
 * no está, la pantalla carga y luego revienta en 403 al pedir los datos:
 *
 * - `PRESUPUESTOS_ROLES` → `dashboard.py`, `creators.py`, `general_expenses.py`
 * - `ADMIN_ROLES`        → aprobar/rechazar/borrar de `tickets.py`
 */

/**
 * Consulta y gestión: Dashboard, Creadores, Gastos Generales.
 *
 * Los dos roles de marketing entran por la misma puerta y con el mismo alcance
 * — es literalmente la lista de `require_role` de esos tres routers. La
 * diferencia entre ambos no está en Presupuestos sino en Equipos:
 * `marketing_admin` lo tiene completo y `marketing_presupuestos` no lo tiene
 * en absoluto (ver `rbac_catalog.py`).
 */
export const PRESUPUESTOS_ROLES = [
  "admin",
  "superadmin",
  "marketing_admin",
  "marketing_presupuestos",
];

/**
 * Administración (creadores/marcas del sistema) y Validación de tickets.
 * Exclusivas de admin/superadmin: los dos roles de marketing quedan
 * deliberadamente fuera de las dos.
 *
 * Validación coincide con el backend (aprobar/rechazar/borrar en `tickets.py`
 * son admin/superadmin). Administración es **más estricta que el backend** a
 * propósito: `creators.py` y `brands.py` sí dejarían crear/editar a los roles
 * de marketing, pero la vista no se les ofrece por decisión de producto.
 */
export const ADMIN_ROLES = ["admin", "superadmin"];

/** Gestión de usuarios y RBAC (R4). */
export const SUPERADMIN_ONLY = ["superadmin"];
