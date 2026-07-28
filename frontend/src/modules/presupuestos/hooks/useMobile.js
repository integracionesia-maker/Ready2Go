import { useState, useEffect } from "react";

/**
 * Detecta viewport móvil (< breakpoint, por defecto 640px = `sm` de Tailwind).
 * Para responsividad puramente visual, preferir clases `sm:`/`md:` de
 * Tailwind — este hook existe para los casos que Tailwind no puede resolver
 * en CSS puro (ej. la prop `height` numérica de ApexCharts, ver
 * doc/responsividad-movil.md §A3).
 */
export function useMobile(breakpoint = 640) {
  const [isMobile, setIsMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth < breakpoint : false
  );

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpoint]);

  return isMobile;
}
