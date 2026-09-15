/** Modo "periodo único" del Dashboard (I11): la detección de CUÁNDO un rango
 * es un solo mes/año vive en el backend (`crud.detectar_periodo_unico`,
 * fuente de verdad única para pantalla y PDF) — este archivo solo formatea
 * lo que ya viene resuelto en `PeriodComparisonResponse`. */

const LABELS = { mes: "el mes pasado", anio: "el año pasado" };

/** "+12.3% vs el mes pasado" — signo según si el gasto subió o bajó (más
 * gasto = número más alto, no es "bueno" ni "malo" per se, solo el dato).
 * Sin `anterior` (rango que no calificó) regresa null. */
export function formatearComparacion(actual, anterior, tipo) {
  if (anterior == null || tipo == null) return null;
  const label = LABELS[tipo] ?? "el periodo pasado";
  if (anterior > 0) {
    const pct = ((actual - anterior) / anterior) * 100;
    const signo = pct >= 0 ? "+" : "";
    return { texto: `${signo}${pct.toFixed(1)}% vs ${label}`, subio: actual >= anterior };
  }
  if (actual > 0) {
    return { texto: `antes $0.00 vs ${label}`, subio: true };
  }
  return null;
}
