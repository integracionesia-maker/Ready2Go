import { useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import ProfilePopover from "./ProfilePopover";
import ThemeToggle from "./ThemeToggle";
import BrandLogo from "./BrandLogo";

// Mismo patrón que EquipmentCard.jsx (tilt 3D): el tipo de puntero no cambia
// a media sesión, se calcula una sola vez por montaje del módulo. En táctil
// el glow no monta listeners ni estado — sin hover no hay posición de mouse
// que seguir, y el efecto se queda inactivo (CSS ya lo deja en opacity 0).
const SOPORTA_HOVER_FINO =
  typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

/** Barra superior fija global (R1): logo + Grupo Ortiz, hamburguesa en móvil
 * (abre el drawer del Sidebar, R3), toggle de tema y popover de perfil.
 * Compartida entre módulos (Presupuestos/Equipos) — cada Layout pasa su
 * propio `subtitle`.
 *
 * Glow de cristal (C1): radial-gradient sutil que sigue al cursor, simulando
 * una fuente de luz detrás del vidrio. Con `prefers-reduced-motion` se queda
 * fijo al centro (sin seguimiento, sin fade). Nunca lleva `overflow-hidden`
 * — el dropdown de ProfilePopover se renderiza `absolute` dentro de este
 * `<header>` y necesita desbordarlo.
 */
export default function Header({ onOpenMobileMenu, subtitle = "Ready2Go" }) {
  const headerRef = useRef(null);
  const reduceMotion = useReducedMotion();
  const interactive = SOPORTA_HOVER_FINO && !reduceMotion;
  const [glowPos, setGlowPos] = useState({ x: 0.5, y: 0.5, active: false });

  function handleMouseMove(e) {
    const rect = headerRef.current.getBoundingClientRect();
    setGlowPos({
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
      active: true,
    });
  }

  function handleMouseLeave() {
    setGlowPos((prev) => ({ ...prev, active: false }));
  }

  const glowGradient = `radial-gradient(circle at ${glowPos.x * 100}% ${glowPos.y * 100}%, var(--go-glow) 0%, color-mix(in srgb, var(--go-glow) 40%, transparent) 40%, transparent 70%)`;

  const glowStyle = reduceMotion
    ? {
        opacity: 1,
        background: `radial-gradient(circle at 50% 50%, var(--go-glow) 0%, color-mix(in srgb, var(--go-glow) 40%, transparent) 40%, transparent 70%)`,
      }
    : {
        opacity: glowPos.active ? 1 : 0,
        transitionDuration: "var(--go-duration-slow)",
        background: glowGradient,
      };

  return (
    <header
      ref={headerRef}
      onMouseMove={interactive ? handleMouseMove : undefined}
      onMouseLeave={interactive ? handleMouseLeave : undefined}
      className="glass fixed left-0 right-0 top-0 z-40 flex h-16 items-center justify-between border-b px-4 sm:px-6"
      style={{ borderColor: "var(--go-border)", borderRadius: 0, boxShadow: "none" }}
    >
      <div className="pointer-events-none absolute inset-0 transition-opacity" style={glowStyle} aria-hidden="true" />

      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="-ml-1 flex h-10 w-10 items-center justify-center rounded-go transition-colors hover:bg-white/5 md:hidden"
          title="Abrir menú"
          aria-label="Abrir menú"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" style={{ color: "var(--go-text-secondary)" }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <BrandLogo variant="isotipo" className="h-8 w-auto flex-shrink-0" />
        <div className="hidden min-w-0 sm:block">
          <h1 className="truncate font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
            Grupo Ortiz
          </h1>
          <p className="truncate font-body text-[10px] tracking-wide" style={{ color: "var(--go-text-secondary)" }}>
            {subtitle}
          </p>
        </div>
      </div>

      <div className="relative z-10 flex items-center gap-2 sm:gap-3">
        <ThemeToggle />
        <ProfilePopover />
      </div>
    </header>
  );
}
