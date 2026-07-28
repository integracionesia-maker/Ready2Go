// Formula de contraste WCAG 2.x (relative luminance + (L1+0.05)/(L2+0.05)).
// Acepta "#rgb"/"#rrggbb" y también "rgb(r,g,b)"/"rgba(r,g,b,a)" — esto
// último es literalmente lo que devuelve getComputedStyle() en el navegador,
// que es como pantallas.spec.js usa esta función.

function parseColor(color) {
  const hexMatch = color.trim().match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hexMatch) {
    let hex = hexMatch[1];
    if (hex.length === 3) {
      hex = hex
        .split("")
        .map((c) => c + c)
        .join("");
    }
    const int = parseInt(hex, 16);
    return { r: (int >> 16) & 255, g: (int >> 8) & 255, b: int & 255, a: 1 };
  }

  const rgbMatch = color.trim().match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i);
  if (rgbMatch) {
    return {
      r: Number(rgbMatch[1]),
      g: Number(rgbMatch[2]),
      b: Number(rgbMatch[3]),
      a: rgbMatch[4] !== undefined ? Number(rgbMatch[4]) : 1,
    };
  }

  throw new Error(`No se pudo interpretar el color: "${color}"`);
}

function channelLuminance(c) {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function relativeLuminance({ r, g, b }) {
  return 0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b);
}

/** Ratio de contraste WCAG entre dos colores (hex o rgb()/rgba()). */
export function ratio(colorA, colorB) {
  const la = relativeLuminance(parseColor(colorA));
  const lb = relativeLuminance(parseColor(colorB));
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

/** Alpha del color computado (para verificar que un velo es sólido: alpha === 1). */
export function alphaDe(color) {
  return parseColor(color).a;
}
