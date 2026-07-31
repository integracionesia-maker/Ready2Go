import { Link } from "react-router-dom";
import GlassPanel from "./GlassPanel";

/**
 * Tarjeta de acceso rápido navegable — compartida entre las páginas de
 * Inicio de Presupuestos y Equipos (extraída de HomePage.jsx, C2). Si `to`
 * viene, navega con `Link`; si no, actúa como botón (`onClick`).
 */
export default function SectionCard({ to, onClick, title, description, icon }) {
  const Tag = to ? Link : "button";
  return (
    <Tag
      {...(to ? { to } : { type: "button", onClick })}
      className="group w-full text-left transition-all duration-200 hover:-translate-y-0.5"
      style={{ textDecoration: "none" }}
    >
      <GlassPanel className="h-full p-5 sm:p-6">
        <div
          className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-go-lg transition-colors duration-200 group-hover:bg-[var(--go-orange-tint)]"
          style={{ background: "var(--go-surface-sunken)" }}
        >
          <svg
            className="h-5 w-5 sm:h-6 sm:w-6 transition-colors duration-200 group-hover:text-[var(--go-orange)]"
            style={{ color: "var(--go-text-secondary)" }}
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
          </svg>
        </div>
        <h3
          className="mt-4 font-display text-base font-bold uppercase tracking-[0.06em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          {title}
        </h3>
        <p className="mt-1.5 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          {description}
        </p>
      </GlassPanel>
    </Tag>
  );
}
