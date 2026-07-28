import { NavLink, useLocation } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";

/**
 * Nav genérico de pastillas de cristal — usado por src/shell/ModuleTabs.jsx
 * para Presupuestos/Equipos. `ariaLabel` es obligatorio: el contrato de nav
 * es por etiqueta, no por componente (B-I01) — quien lo instancie decide el
 * aria-label exacto ("Navegacion principal" para el nav de módulos).
 *
 * `item.isActive(pathname)` es opcional: por defecto se usa el propio
 * `isActive` de NavLink, pero un item de módulo (p.ej. "Presupuestos" en
 * `to="/"`) necesita marcarse activo en TODO su subárbol de rutas
 * (/dashboard, /creadores, ...), no solo en el "/" exacto — de ahí el
 * matcher explícito en vez de confiar en el matching por defecto.
 *
 * La pastilla activa usa layoutId para la animación magnética; en
 * prefers-reduced-motion no se mueve, solo cambia de opacidad (requisito no
 * opcional de 01-I1-shell.md).
 */
export default function GlassNav({ items, ariaLabel, refract = true }) {
  const location = useLocation();
  const reduceMotion = useReducedMotion();

  return (
    <nav aria-label={ariaLabel} className={`glass ${refract ? "glass--refract" : ""} relative inline-flex items-center gap-1 p-1.5`}>
      <div className="veil absolute inset-0 -z-10" aria-hidden="true" />
      {items.map((item) => {
        const isActive = item.isActive
          ? item.isActive(location.pathname)
          : location.pathname === item.to;

        return (
          <NavLink
            key={item.to}
            to={item.disabled ? "#" : item.to}
            aria-disabled={item.disabled || undefined}
            aria-current={isActive ? "page" : undefined}
            tabIndex={item.disabled ? -1 : undefined}
            onClick={(e) => {
              if (item.disabled) e.preventDefault();
            }}
            className={`relative z-10 flex items-center gap-2 rounded-go px-4 py-2 font-display text-sm font-semibold transition-colors duration-200 ${
              item.disabled ? "pointer-events-none opacity-40" : ""
            }`}
          >
            {isActive &&
              (reduceMotion ? (
                <motion.span
                  key="pill"
                  className="absolute inset-0 -z-[1] rounded-go"
                  style={{ background: "var(--go-surface-sunken)" }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15 }}
                />
              ) : (
                <motion.span
                  layoutId="go-nav-pill"
                  className="absolute inset-0 -z-[1] rounded-go"
                  style={{ background: "var(--go-surface-sunken)" }}
                  transition={{ type: "spring", stiffness: 500, damping: 40 }}
                />
              ))}
            <span className="relative" style={{ color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)" }}>
              {item.label}
            </span>
          </NavLink>
        );
      })}
    </nav>
  );
}
