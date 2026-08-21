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
 * Transacciones (listado de tickets): los 4 roles de Presupuestos más
 * `creador` (ve solo los suyos) y `marketing_basico` (ve solo lo que subió).
 * Espejo de `ROLES_CON_TICKETS` en `backend/app/routers/tickets.py` — roles sin
 * acceso a Presupuestos (usuario, colaborador_mkt) no deben abrir la pantalla
 * ni por URL directa.
 */
export const TICKETS_ROLES = [...PRESUPUESTOS_ROLES, "creador", "marketing_basico"];

/**
 * Administración: gestión de creadores y marcas (pantalla /administracion).
 * admin, superadmin y `marketing_admin`. El backend (`creators.py`/`brands.py`)
 * ya acepta a marketing_admin en el CRUD, así que esto solo abre la vista que
 * lo refleja. `marketing_presupuestos` NO se incluye (decisión: solo el rol
 * administrador de marketing gestiona el catálogo).
 */
export const ADMINISTRACION_ROLES = ["admin", "superadmin", "marketing_admin"];

/**
 * Validación de tickets (y borrado): exclusiva de admin/superadmin. Espejo de
 * aprobar/rechazar/borrar en `tickets.py`, que son admin/superadmin.
 */
export const ADMIN_ROLES = ["admin", "superadmin"];

/** Gestión de usuarios y RBAC (R4). */
export const SUPERADMIN_ONLY = ["superadmin"];
