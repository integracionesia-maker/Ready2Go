import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * Sube al inicio de la página en cada cambio de ruta (lote de calidad
 * 2026-08-18). Con `BrowserRouter` + `<Routes>` clásico, react-router no
 * restaura el scroll: al navegar entre pantallas largas (tablas de
 * transacciones, historial de préstamos) quedabas a mitad del scroll de
 * la pantalla anterior.
 *
 * `behavior: "instant"` a propósito: el CSS global define
 * `scroll-behavior: smooth`, y un desplazamiento animado en cada cambio
 * de ruta se siente como un bug, no como un adorno.
 */
export default function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);

  return null;
}
