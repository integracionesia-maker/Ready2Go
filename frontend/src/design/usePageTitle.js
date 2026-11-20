import { useEffect } from "react";
import { prefijoTituloQA } from "./buildInfo";

/**
 * Título del documento por ruta: "Dashboard · GOCreate".
 *
 * Sin esto, todas las rutas comparten el título estático de index.html y,
 * con varias pestañas abiertas, es imposible distinguir pantallas (lote de
 * calidad 2026-08-18). `usePageTitle()` sin argumentos restaura el título
 * base de la app.
 */
export default function usePageTitle(titulo) {
  useEffect(() => {
    // En QA el título lleva "[QA] " para no confundir pestañas con producción.
    document.title =
      prefijoTituloQA() + (titulo ? `${titulo} · GOCreate` : "GOCreate — Grupo Ortiz");
  }, [titulo]);
}
