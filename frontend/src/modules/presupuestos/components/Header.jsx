import { useEffect, useState } from "react";
import { useMobile } from "@/design/useMobile";
import ProfilePopover from "./ProfilePopover";
import ThemeToggle from "./ThemeToggle";
import BrandLogo from "./BrandLogo";

const HEADER_HEIGHT = 64; // h-16 = 4rem

/** Barra superior fija global (R1): logo + Grupo Ortiz, hamburguesa en móvil
 * (abre el drawer del Sidebar, R3), toggle de tema y popover de perfil.
 * Compartida entre módulos (Presupuestos/Equipos) — cada Layout pasa su
 * propio `subtitle`.
 *
 * Efecto liquid crystal:
 * - Desktop: brillo naranja radial que sigue al cursor en toda la banda
 *   superior (0–64px), trackeado a nivel `document` para que el switch
 *   Presupuestos/Equipos —que es un overlay separado en el DOM— no
 *   interrumpa el glow al pasar el mouse por encima.
 * - Móvil:   degradado naranja estático de izquierda a derecha. */
export default function Header({ onOpenMobileMenu, subtitle = "Ready2Go" }) {
  const isMobile = useMobile();
  const [glow, setGlow] = useState({ x: 0.5, visible: false });

  // Trackeo global: el glow se activa cuando el mouse está en los
  // primeros 64px del viewport, cubriendo header + ModuleTabs.
  useEffect(() => {
    if (isMobile) return;

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
  }, [isMobile]);

  return (
    <header
      className="glass fixed left-0 right-0 top-0 z-40 flex h-16 items-center justify-between border-b px-4 sm:px-6"
      style={{ borderColor: "var(--go-border)", borderRadius: 0, boxShadow: "none" }}
    >
      {/* Brillo liquid crystal detrás del header */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden"
        style={{ borderRadius: 0 }}
      >
        {/* Capa base: degradado naranja horizontal siempre visible */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to right, transparent 0%, rgba(251,103,11,0.10) 20%, rgba(251,103,11,0.05) 50%, rgba(251,103,11,0.10) 80%, transparent 100%)",
          }}
        />

        {/* Capa interactiva (solo desktop): brillo radial que sigue al mouse */}
        {!isMobile && (
          <div
            className="absolute inset-0 transition-opacity duration-500"
            style={{ opacity: glow.visible ? 1 : 0 }}
          >
            <div
              className="absolute top-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 blur-3xl"
              style={{
                left: `${glow.x * 100}%`,
                background:
                  "radial-gradient(circle, rgba(251,103,11,0.30) 0%, rgba(251,103,11,0.10) 40%, transparent 70%)",
              }}
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="-ml-1 flex h-9 w-9 items-center justify-center rounded-go transition-colors hover:bg-white/5 md:hidden"
          title="Abrir menú"
          aria-label="Abrir menú"
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

      <div className="relative z-10 flex items-center gap-2 sm:gap-3">
        <ThemeToggle />
        <ProfilePopover />
      </div>
    </header>
  );
}
