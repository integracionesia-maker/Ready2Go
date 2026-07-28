// Verificador de "pantalla pintada" (B-I05). Antes vivía como script suelto
// en el scratchpad de quien tomaba las capturas; formalizado aquí para que
// el criterio sea reproducible por cualquiera, no dependa de una máquina.
//
// DOM lleno no es pantalla pintada: un dashboard con datos en cero pinta el
// estado vacío sin montar un solo gráfico (R-I04) — por eso el conteo de
// `.apexcharts-canvas` es obligatorio en /dashboard, no opcional. El largo de
// texto y el alto de #root son la red gruesa que atrapa un fallo total de
// render (pantalla en blanco); no reemplazan el chequeo específico de Apex.

export const RUTAS = [
  "/login",
  "/",
  "/dashboard",
  "/creadores",
  "/transacciones",
  "/validacion",
  "/gastos-generales",
  "/administracion",
  "/perfil",
  "/403",
];

export const ANCHOS = [
  { width: 1280, height: 800, nombre: "1280x800" },
  { width: 390, height: 844, nombre: "390x844" },
];

const MIN_TEXT_LENGTH = 30;
const MIN_ROOT_HEIGHT = 150;

/** Mide la pantalla ya navegada en `page`: texto de #root, alto real, canvases de Apex. */
export async function medirPantalla(page) {
  return page.evaluate(() => {
    const root = document.getElementById("root");
    const text = root ? root.innerText || "" : "";
    const rect = root ? root.getBoundingClientRect() : { height: 0 };
    return {
      textLength: text.replace(/\s+/g, " ").trim().length,
      rootHeight: Math.round(rect.height),
      apexCanvasCount: document.querySelectorAll(".apexcharts-canvas").length,
    };
  });
}

/** true si la pantalla parece vacía (fallo total de render). */
export function pantallaVacia(medicion) {
  return medicion.textLength < MIN_TEXT_LENGTH || medicion.rootHeight < MIN_ROOT_HEIGHT;
}

/** true si, siendo /dashboard, no montó ni un gráfico Apex (R-I04). */
export function dashboardSinGraficos(ruta, medicion) {
  return ruta === "/dashboard" && medicion.apexCanvasCount === 0;
}
