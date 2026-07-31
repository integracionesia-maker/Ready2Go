import { NavLink } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const NAV_ITEMS = [
  {
    to: "/",
    end: true,
    label: "Inicio",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
    roles: null,
  },
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
    roles: ["admin", "superadmin"],
  },
  {
    to: "/creadores",
    label: "Creadores",
    icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z",
    roles: ["admin", "superadmin"],
  },
  {
    to: "/transacciones",
    label: "Transacciones",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    roles: null,
  },
  {
    to: "/validacion",
    label: "Validación",
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    roles: ["admin", "superadmin"],
    badgeKey: "pendingCount",
  },
  {
    to: "/gastos-generales",
    label: "Gastos Generales",
    icon: "M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z",
    roles: ["admin", "superadmin"],
  },
  {
    to: "/administracion",
    label: "Administración",
    icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z",
    roles: ["admin", "superadmin"],
  },
];

const PROFILE_ITEM = {
  to: "/perfil",
  label: "Mi Perfil",
  icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
};

/**
 * Sidebar (R1/R3): en escritorio (≥md) es la barra colapsable de siempre,
 * fija bajo el Header. En móvil (<md) es un drawer oculto que se abre con la
 * hamburguesa del Header, con backdrop, y se cierra al navegar/click afuera.
 */
export default function Sidebar({ collapsed, onToggle, onNewTicket, pendingCount = 0, mobileOpen, onCloseMobile }) {
  const { user } = useAuth();

  const labelClass = collapsed ? "md:hidden" : "";

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role))
  );

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
        style={{ borderColor: "var(--go-border)", borderRadius: 0 }}
      >
        {/* Brillo liquid crystal estático */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 overflow-hidden"
          style={{ borderRadius: 0 }}
        >
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(0deg, rgba(251,103,11,0.10) 0%, rgba(251,103,11,0.05) 30%, transparent 60%, rgba(251,103,11,0.03) 100%)",
            }}
          />
        </div>

        {/* ── Navigation ────────────────────────────────────────────────── */}
        <nav aria-label="Navegacion de Presupuestos" className="flex-1 space-y-1 overflow-y-auto px-2.5 py-4">
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
              {item.badgeKey === "pendingCount" && pendingCount > 0 && (
                <span
                  className="flex h-5 min-w-[1.25rem] flex-shrink-0 items-center justify-center rounded-full px-1 font-display text-[10px] font-bold text-white"
                  style={{ background: "var(--go-orange)" }}
                >
                  {pendingCount}
                </span>
              )}
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

        {/* ── Nuevo Ticket ──────────────────────────────────────────────── */}
        <div className="relative z-10 px-2.5 pb-3">
          <button
            onClick={onNewTicket}
            title="Nuevo Ticket"
            className={`btn-go w-full ${collapsed ? "justify-center px-0" : "justify-center px-0 md:justify-start md:px-5"}`}
          >
            <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span className={labelClass}>Nuevo Ticket</span>
          </button>
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
