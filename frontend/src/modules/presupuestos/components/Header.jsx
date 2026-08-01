import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import ProfilePopover from "./ProfilePopover";
import ThemeToggle from "./ThemeToggle";
import BrandLogo from "./BrandLogo";
import ModuleTabs from "../../../shell/ModuleTabs";

const HEADER_HEIGHT = 80; // top-3 (12px) + h-14 (56px) + holgura

// En táctil no hay hover — el glow queda estático (degradado base).
const SOPORTA_HOVER_FINO =
  typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

/** Barra superior fija global (R1): logo + Grupo Ortiz, hamburguesa en móvil
 * (abre el drawer del Sidebar, R3), toggle de tema y popover de perfil.
 * Compartida entre módulos (Presupuestos/Equipos) — cada Layout pasa su
 * propio `subtitle`.
 *
 * Efecto liquid crystal:
 * - Capa base: degradado naranja horizontal siempre visible.
 * - Capa interactiva (solo hover/pointer): brillo radial que sigue al cursor
 *   en toda la banda superior (0–64px), trackeado a nivel `document` para
 *   que el switch Presupuestos/Equipos no interrumpa el glow.
 * - `prefers-reduced-motion`: brillo fijo al centro, sin fade. */
export default function Header({ onToggleMobileMenu, mobileMenuOpen = false, subtitle = "Ready2Go" }) {
  const headerRef = useRef(null);
  const reduceMotion = useReducedMotion();
  const interactive = SOPORTA_HOVER_FINO && !reduceMotion;
  const [glow, setGlow] = useState({ x: 0.5, visible: false });

  // Trackeo global: el glow se activa cuando el mouse está en los
  // primeros 64px del viewport, cubriendo header + ModuleTabs.
  useEffect(() => {
    if (!interactive) return;

    const onMove = (e) => {
      setGlow({
        x: e.clientX / window.innerWidth,
        visible: e.clientY <= HEADER_HEIGHT,
      });
    };

    const onLeave = () => setGlow((p) => ({ ...p, visible: false }));

    document.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeave);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
    };
  }, [interactive]);

  const GLOW_COLOR = "rgba(251,103,11,0.30)"; // --go-orange con opacidad

  const glowGradient = `radial-gradient(circle, ${GLOW_COLOR} 0%, color-mix(in srgb, ${GLOW_COLOR} 40%, transparent) 40%, transparent 70%)`;

  const glowStyle = reduceMotion
    ? {
        opacity: 1,
        background: `radial-gradient(circle at 50% 50%, ${GLOW_COLOR} 0%, color-mix(in srgb, ${GLOW_COLOR} 40%, transparent) 40%, transparent 70%)`,
      }
    : {
        opacity: glow.visible ? 1 : 0,
        transitionDuration: "var(--go-duration-slow, 500ms)",
        background: glowGradient,
      };

  return (
    <header
      ref={headerRef}
      className="glass fixed left-2 right-2 top-2 sm:left-3 sm:right-3 sm:top-3 z-40 flex h-14 items-center justify-between px-3 sm:px-5"
      style={{
        borderColor: "var(--go-border)",
        background: "color-mix(in srgb, var(--veil-bg) 68%, transparent)",
      }}
    >
      {/* Brillo liquid crystal detrás del header */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
        style={{ borderRadius: "inherit" }}
      >
        {/* Capa base: degradado naranja horizontal siempre visible */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to right, transparent 0%, rgba(251,103,11,0.10) 20%, rgba(251,103,11,0.05) 50%, rgba(251,103,11,0.10) 80%, transparent 100%)",
          }}
        />

        {/* Capa interactiva: brillo radial (sigue al mouse o fijo si reduced-motion) */}
        {interactive || reduceMotion ? (
          <div className="absolute inset-0 transition-opacity" style={glowStyle}>
            {interactive && !reduceMotion && (
              <div
                className="absolute top-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 blur-3xl"
                style={{
                  left: `${glow.x * 100}%`,
                  background: glowGradient,
                }}
              />
            )}
          </div>
        ) : null}
      </div>

      <div className="relative z-10 flex items-center gap-3">
        <button
          onClick={onToggleMobileMenu}
          className="-ml-1 flex h-10 w-10 items-center justify-center rounded-go transition-colors hover:bg-white/5 md:hidden"
          title={mobileMenuOpen ? "Cerrar menú" : "Abrir menú"}
          aria-label={mobileMenuOpen ? "Cerrar menú" : "Abrir menú"}
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" style={{ color: "var(--go-text-secondary)" }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <BrandLogo variant="isotipo" className="h-8 w-auto flex-shrink-0" />
        {/* El texto se oculta en movil (<640px) y lleva max-width progresivo para
             no chocar con el switch Presupuestos/Equipos centrado en el header.
             Subtitulo visible solo desde md (768px) porque es lo que mas empuja. */}
        <div className="hidden min-w-0 sm:block max-w-[100px] md:max-w-[180px] lg:max-w-none">
          <h1 className="truncate font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
            Grupo Ortiz
          </h1>
          <p className="truncate font-body text-[10px] tracking-wide hidden md:block" style={{ color: "var(--go-text-secondary)" }}>
            {subtitle}
          </p>
        </div>
      </div>

      {/* ── Module switch (center) ──────────────────────────────────── */}
      <div className="relative z-10 hidden sm:block">
        <ModuleTabs />
      </div>

      <div className="relative z-10 flex items-center gap-2 sm:gap-3">
        <ThemeToggle />
        <ProfilePopover onBeforeToggle={() => { if (mobileMenuOpen) onToggleMobileMenu(); }} />
      </div>
    </header>
  );
}
