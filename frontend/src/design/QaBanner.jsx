import { esEntornoQA } from "./buildInfo";

/**
 * Banner permanente del entorno QA (requisito QA-11 de `deploy/qa/`).
 *
 * Solo se pinta cuando `esEntornoQA()` es verdadero; en producción devuelve
 * `null` y no deja rastro en el DOM. Es una etiqueta fija arriba al centro, con
 * `pointer-events: none` para no tapar clics del header, y no usa cristal (ver
 * DESIGN_SYSTEM.md: nada de cristal sobre texto): fondo sólido naranja GO.
 */
export default function QaBanner() {
  if (!esEntornoQA()) return null;
  return (
    <div
      role="status"
      aria-label="Entorno de pruebas"
      className="pointer-events-none fixed left-1/2 top-0 z-[9999] -translate-x-1/2 rounded-b-lg bg-[#FB670B] px-3 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white shadow"
    >
      Entorno de pruebas · QA · datos ficticios
    </div>
  );
}
