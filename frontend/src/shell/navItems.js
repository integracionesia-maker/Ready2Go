/**
 * Items del nav de módulos (ModuleTabs). Equipos existe pero no navega
 * todavía (I4) — visible y deshabilitado con aria-disabled, no oculto:
 * así queda documentado en pantalla que el módulo llega después, en vez
 * de desaparecer sin explicación.
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
    disabled: true,
    isActive: (pathname) => pathname.startsWith("/equipos"),
  },
];
