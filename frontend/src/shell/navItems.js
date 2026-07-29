/**
 * Items del nav de módulos (ModuleTabs). Equipos ya navega desde I4a.
 *
 * `isActive` es explícito porque "Presupuestos" vive en `to="/"` pero debe
 * marcarse activo en TODO su subárbol de rutas, no solo en la home exacta.
 */
export const MODULE_NAV_ITEMS = [
  {
    to: "/",
    label: "Presupuestos",
    isActive: (pathname) => !pathname.startsWith("/equipos"),
  },
  {
    to: "/equipos",
    label: "Equipos",
    isActive: (pathname) => pathname.startsWith("/equipos"),
  },
];
