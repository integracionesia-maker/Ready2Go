/**
 * Formateadores compartidos (lote de calidad 2026-08-18).
 *
 * Antes, 10 componentes definían cada uno su propio `formatCurrency` con
 * un Intl.NumberFormat("es-MX", ...) idéntico: 10 copias del mismo
 * formateador de moneda, con el riesgo de que una cambiara y las demás no
 * (o de que cada nueva pantalla reinventara la rueda con una variante).
 *
 * La salida es byte-idéntica a la de las copias anteriores, incluido el
 * guard `|| 0` que algunas tenían: un valor nulo muestra $0.00 en vez de
 * "NaN".
 */
export function formatMXN(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount || 0);
}
