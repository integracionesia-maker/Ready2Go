/**
 * Items del nav de módulos (ModuleTabs). Equipos ya navega desde I4a.
 *
 * `isActive` es explícito porque "Presupuestos" vive en `to="/"` pero debe
 * marcarse activo en TODO su subárbol de rutas, no solo en la home exacta.
 *
 * Las rutas compartidas del sistema (/perfil, /administracion-sistema,
 * /auditoria, /403) NO pertenecen a ningún módulo — ningún tab se activa.
 */

/** Rutas del módulo de Presupuestos (incluye la raíz "/"). */
const PRESUPUESTOS_PATHS = [
  "/dashboard",
  "/creadores",
  "/transacciones",
  "/administracion",
  "/validacion",
  "/gastos-generales",
];

/** Rutas compartidas del sistema — no activan ningún tab de módulo. */
const SYSTEM_PATHS = [
  "/perfil",
  "/administracion-sistema",
  "/auditoria",
  "/403",
];

function isPresupuestosActive(pathname) {
  if (pathname === "/") return true;
  return PRESUPUESTOS_PATHS.some((p) => pathname.startsWith(p));
}

function isEquiposActive(pathname) {
  return pathname.startsWith("/equipos");
}

function isSystemPath(pathname) {
  return SYSTEM_PATHS.some((p) => pathname.startsWith(p));
}

export const MODULE_NAV_ITEMS = [
  {
    to: "/",
    label: "Presupuestos",
    isActive: (pathname) =>
      !isSystemPath(pathname) && !isEquiposActive(pathname)
        ? isPresupuestosActive(pathname)
        : false,
  },
  {
    to: "/equipos",
    label: "Equipos",
    isActive: (pathname) =>
      !isSystemPath(pathname) && isEquiposActive(pathname),
  },
];
