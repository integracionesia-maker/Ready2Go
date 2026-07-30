import { NavLink, Link } from "react-router-dom";
import { usePermisos } from "../permisos/usePermisos";
import RequierePermiso from "../permisos/RequierePermiso";

const NAV_ITEMS = [
  {
    to: "/equipos",
    end: true,
    label: "Inicio",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
    permiso: ["equipos_inventario", "ver"],
  },
  {
    to: "/equipos/inventario",
    label: "Inventario",
    icon: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
    permiso: ["equipos_inventario", "ver"],
  },
  {
    to: "/equipos/nuevo",
    label: "Nuevo préstamo",
    icon: "M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_prestamos", "solicitar"],
  },
  {
    to: "/equipos/activos",
    label: "Activos",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_prestamos", "ver_propios"],
  },
  {
    to: "/equipos/aprobaciones",
    label: "Aprobaciones",
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    // OR: la pestaña se muestra si el usuario puede cualquiera de las tres
    // colas de Aprobaciones — dentro, cada cola ya se esconde por su cuenta.
    permiso: [
      ["equipos_aprobacion", "autorizar_entrega"],
      ["equipos_aprobacion", "confirmar_devolucion"],
      ["equipos_aprobacion", "cerrar_incidencia"],
    ],
  },
  {
    to: "/equipos/historial",
    label: "Historial",
    icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_prestamos", "ver_propios"],
  },
];

const PROFILE_ITEM = {
  to: "/perfil",
  label: "Mi Perfil",
  icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
};

/**
 * Sidebar de Equipos — estructuralmente idéntico al Sidebar de Presupuestos
 * (mismas dimensiones, mismo drawer móvil, mismo toggle de colapso).
 * Filtra por `usePermisos` en vez de `roles`: cada item lista su
 * (modulo, accion); "Aprobaciones" acepta un array de pares (OR).
 */
export default function EquiposSidebar({ collapsed, onToggle, mobileOpen, onCloseMobile }) {
  const { puede } = usePermisos();

  const labelClass = collapsed ? "md:hidden" : "";

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (Array.isArray(item.permiso[0])) {
      return item.permiso.some(([mod, acc]) => puede(mod, acc));
    }
    return puede(item.permiso[0], item.permiso[1]);
  });

  return (
    <>
      {/* ── Backdrop móvil ────────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 md:hidden"
          style={{ background: "var(--go-overlay)" }}
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`glass fixed left-0 top-16 z-40 flex h-[calc(100%-4rem)] w-60 flex-col border-r transition-all duration-300 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0 ${collapsed ? "md:w-16" : "md:w-60"}`}
        style={{ borderColor: "var(--go-border)" }}
      >
        <div className="veil absolute inset-0 -z-10" aria-hidden="true" />

        {/* ── Navigation ────────────────────────────────────────────────── */}
        <nav aria-label="Navegación de Equipos" className="relative z-10 flex-1 space-y-1 overflow-y-auto px-2.5 py-4">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={item.label}
              onClick={onCloseMobile}
              className="flex items-center gap-3 rounded-go px-3 py-3 md:py-2.5 font-display text-sm font-semibold tracking-wide transition-all duration-200"
              style={({ isActive }) => ({
                background: isActive ? "var(--go-surface-sunken)" : "transparent",
                color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)",
              })}
            >
              <svg
                className="h-5 w-5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.7}
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              <span className={`${labelClass} truncate flex-1`}>{item.label}</span>
            </NavLink>
          ))}

          <NavLink
            to={PROFILE_ITEM.to}
            title={PROFILE_ITEM.label}
            onClick={onCloseMobile}
            className="flex items-center gap-3 rounded-go px-3 py-3 font-display text-sm font-semibold tracking-wide transition-all duration-200 md:hidden"
            style={({ isActive }) => ({
              background: isActive ? "var(--go-surface-sunken)" : "transparent",
              color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)",
            })}
          >
            <svg
              className="h-5 w-5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.7}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d={PROFILE_ITEM.icon} />
            </svg>
            <span className="truncate">{PROFILE_ITEM.label}</span>
          </NavLink>
        </nav>

        {/* ── Nuevo préstamo ────────────────────────────────────────────── */}
        <div className="relative z-10 px-2.5 pb-3">
          <RequierePermiso modulo="equipos_prestamos" accion="solicitar">
            <Link
              to="/equipos/nuevo"
              title="Nuevo préstamo"
              className={`btn-go w-full ${collapsed ? "justify-center px-0" : "justify-center px-0 md:justify-start md:px-5"}`}
              onClick={onCloseMobile}
            >
              <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              <span className={labelClass}>Nuevo préstamo</span>
            </Link>
          </RequierePermiso>
        </div>

        {/* ── Collapse toggle (solo escritorio) ──────────────────────────── */}
        <button
          onClick={onToggle}
          title={collapsed ? "Expandir menú" : "Minimizar menú"}
          className="relative z-10 hidden items-center justify-center border-t py-3 transition-colors hover:bg-white/5 md:flex"
          style={{ borderColor: "var(--go-border)", color: "var(--go-text-secondary)" }}
        >
          <svg
            className={`h-4 w-4 transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </aside>
    </>
  );
}
