/**
 * Items del nav de módulos (ModuleTabs): Presupuestos / Equipos.
 *
 * `isActive` es explícito porque "Presupuestos" vive en `to="/"` pero debe
 * marcarse activo en TODO su subárbol de rutas, no solo en la home exacta.
 *
 * Las rutas compartidas del sistema (/perfil, /administracion-sistema,
 * /auditoria, /403) NO pertenecen a ningún módulo — ningún tab se activa.
 *
 * `moduleKey` lo usa ModuleTabs para decidir a qué tabs tiene acceso el usuario
 * según sus permisos.
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

/**
 * Ruta de inicio del usuario según sus permisos: la primera pantalla a la que
 * SÍ puede entrar. Se usa al iniciar sesión para no aterrizar a alguien en un
 * módulo que no puede ver. Prioridad: Presupuestos (default histórico y de
 * admins) → Equipos → perfil (piso: siempre accesible, último recurso).
 */
export function rutaInicioDe(permisos = {}) {
  if ((permisos.presupuestos || []).length > 0) return "/";
  if (Object.keys(permisos).some((m) => m.startsWith("equipos_") && permisos[m].length > 0)) {
    return "/equipos";
  }
  return "/perfil";
}

export const MODULE_NAV_ITEMS = [
  {
    to: "/",
    label: "Presupuestos",
    moduleKey: "presupuestos",
    isActive: (pathname) =>
      !isSystemPath(pathname) && !isEquiposActive(pathname) ? isPresupuestosActive(pathname) : false,
  },
  {
    to: "/equipos",
    label: "Equipos",
    moduleKey: "equipos",
    isActive: (pathname) => !isSystemPath(pathname) && isEquiposActive(pathname),
  },
];
