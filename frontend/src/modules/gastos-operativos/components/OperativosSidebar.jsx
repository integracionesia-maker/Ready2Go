import { NavLink } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

/**
 * Sidebar del módulo Gastos Operativos. Misma estructura/dimensiones que el de
 * Presupuestos/Equipos (drawer en móvil, colapsable en escritorio). Rubros solo
 * aparece si el usuario tiene `gastos_operativos:gestionar_rubros`.
 */
const ICON = {
  registro:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  dashboard:
    "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
  rubros:
    "M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z",
};

export default function OperativosSidebar({ collapsed, onToggle, mobileOpen, onCloseMobile }) {
  const { user } = useAuth();
  const permisos = user?.permisos?.gastos_operativos || [];
  const puedeGestionarRubros = permisos.includes("gestionar_rubros");

  const items = [
    { to: "/gastos-operativos", end: true, label: "Registro", icon: ICON.registro },
    { to: "/gastos-operativos/dashboard", label: "Dashboard", icon: ICON.dashboard },
    ...(puedeGestionarRubros
      ? [{ to: "/gastos-operativos/rubros", label: "Rubros", icon: ICON.rubros }]
      : []),
  ];

  const labelClass = collapsed ? "md:hidden" : "";

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 md:hidden"
          style={{ background: "var(--go-overlay)" }}
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`glass fixed left-2 md:left-3 bottom-2 md:bottom-3 top-[72px] md:top-[76px] z-40 flex h-[calc(100%-80px)] md:h-[calc(100%-88px)] w-60 flex-col transition-all duration-300 ${
          mobileOpen ? "translate-x-0" : "-translate-x-[calc(100%+0.5rem)]"
        } md:translate-x-0 ${collapsed ? "md:w-16" : "md:w-60"}`}
        style={{
          borderColor: "var(--go-border)",
          background: "color-mix(in srgb, var(--veil-bg) 68%, transparent)",
        }}
      >
        <nav aria-label="Navegacion de Gastos Operativos" className="flex-1 space-y-1 overflow-y-auto px-2.5 py-4">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={item.label}
              onClick={onCloseMobile}
              className="relative flex items-center gap-3 rounded-go px-3 py-3 md:py-2.5 font-display text-sm font-semibold tracking-wide transition-all duration-200"
              style={({ isActive }) => ({
                background: isActive ? "var(--go-surface-sunken)" : "transparent",
                color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)",
              })}
            >
              <svg className="h-5 w-5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              <span className={`${labelClass} truncate flex-1`}>{item.label}</span>
            </NavLink>
          ))}
        </nav>

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
