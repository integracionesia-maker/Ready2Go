/**
 * Compresión de imágenes en el navegador, compartida por los dos módulos.
 *
 * Extraído de `modules/equipos/components/PhotoCapture.jsx`, que ya la usaba
 * para las fotos de equipo, porque la subida por cámara de Presupuestos
 * necesita exactamente lo mismo por tres razones distintas:
 *
 * 1. **Tamaño.** Una foto de celular actual pesa 4-8 MB contra un tope de 10 MB
 *    en el servidor, subiendo por datos móviles.
 * 2. **HEIC.** El iPhone guarda en HEIC. Safari suele convertir a JPEG al
 *    entregar el archivo, pero no siempre, y `upload_manager.py` valida por
 *    extensión y MIME: un `.heic` que se cuele es un 400 seco.
 * 3. **Nombre.** Varias cámaras de Android entregan el archivo sin extensión.
 *    Aquí se le pone una siempre.
 *
 * Los valores por defecto (1600px / 0.85) son más conservadores que los de
 * Equipos (900px / 0.72) a propósito: un comprobante es texto y quien valida el
 * ticket tiene que poder leer el monto. Equipos fotografía objetos y conserva
 * sus propios parámetros.
 */

const MAX_DIM_POR_DEFECTO = 1600;
const CALIDAD_POR_DEFECTO = 0.85;

function nombreDeFoto() {
  // Nombre legible y ordenable, sin los dos puntos de la hora ISO (ilegales en
  // nombres de archivo de Windows).
  const sello = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  return `foto-${sello}.jpg`;
}

/**
 * Reescala y recodifica a JPEG. Devuelve un `File` (no un `Blob`) para que
 * quien lo reciba siga viendo `.name` y `.type` — las validaciones de
 * Presupuestos dependen de los dos.
 *
 * @param {File|Blob} archivo
 * @param {{maxDim?: number, calidad?: number, nombre?: string}} opciones
 * @returns {Promise<File>}
 */
export async function comprimirImagen(archivo, opciones = {}) {
  const {
    maxDim = MAX_DIM_POR_DEFECTO,
    calidad = CALIDAD_POR_DEFECTO,
    nombre,
  } = opciones;

  let bitmap;
  try {
    bitmap = await createImageBitmap(archivo);
  } catch {
    // El mensaje nativo del navegador ("The source image could not be
    // decoded") no le dice nada a quien está subiendo un ticket.
    throw new Error(
      "No se pudo leer la imagen. Puede estar dañada o venir en un formato que este navegador no abre."
    );
  }

  const escala = Math.min(1, maxDim / Math.max(bitmap.width, bitmap.height));
  const ancho = Math.max(1, Math.round(bitmap.width * escala));
  const alto = Math.max(1, Math.round(bitmap.height * escala));

  const lienzo = document.createElement("canvas");
  lienzo.width = ancho;
  lienzo.height = alto;
  lienzo.getContext("2d").drawImage(bitmap, 0, 0, ancho, alto);
  bitmap.close?.();

  const blob = await new Promise((resolve) =>
    lienzo.toBlob(resolve, "image/jpeg", calidad)
  );
  if (!blob) throw new Error("No se pudo procesar la imagen.");

  return new File([blob], nombre || nombreDeFoto(), { type: "image/jpeg" });
}
