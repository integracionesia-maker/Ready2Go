import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

const GLOW_COLOR = "rgba(251,103,11,0.30)"; // --go-orange con opacidad

// En táctil no hay hover — el brillo queda en el degradado base.
const SOPORTA_HOVER_FINO =
  typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

/**
 * Brillo "liquid crystal" que sigue al cursor dentro de un contenedor —
 * el mismo efecto del Header, compartido para los sidebars de ambos
 * módulos (2026-08-19).
 *
 * - `containerRef`: ref del contenedor que define los límites del brillo.
 * - `pinX`: si true, el brillo no sigue el eje X (sidebar colapsado: el
 *   ratón solo lo mueve verticalmente).
 * - `size`: diámetro del resplandor en px.
 *
 * `prefers-reduced-motion`: brillo estático centrado, sin seguimiento.
 * En táctil (sin hover fino) no se renderiza nada: queda el degradado base.
 */
export default function LiquidGlow({ containerRef, pinX = false, size = 300 }) {
  const reduceMotion = useReducedMotion();
  const interactive = SOPORTA_HOVER_FINO && !reduceMotion;
  const [pos, setPos] = useState({ x: 0.5, y: 0.5, visible: false });

  useEffect(() => {
    if (!interactive) return;

    const onMove = (e) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect || rect.width === 0 || rect.height === 0) return;
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      const dentro = x >= 0 && x <= 1 && y >= 0 && y <= 1;
      setPos({
        x: dentro ? (pinX ? 0.5 : x) : 0.5,
        y: dentro ? y : 0.5,
        visible: dentro,
      });
    };

    const onLeave = () => setPos((p) => ({ ...p, visible: false }));

    document.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeave);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
    };
  }, [interactive, pinX, containerRef]);

  if (!interactive && !reduceMotion) return null;

  const gradient = `radial-gradient(circle, ${GLOW_COLOR} 0%, color-mix(in srgb, ${GLOW_COLOR} 40%, transparent) 40%, transparent 70%)`;

  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 transition-opacity"
      style={{
        opacity: reduceMotion ? 1 : pos.visible ? 1 : 0,
        transitionDuration: "var(--go-duration-slow, 500ms)",
      }}
    >
      <div
        className="absolute -translate-x-1/2 -translate-y-1/2 blur-3xl"
        style={{
          left: `${(reduceMotion ? 0.5 : pos.x) * 100}%`,
          top: `${(reduceMotion ? 0.5 : pos.y) * 100}%`,
          width: size,
          height: size,
          background: gradient,
        }}
      />
    </div>
  );
}
