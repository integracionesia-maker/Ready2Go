import zlib from "node:zlib";

// Genera PNG/JPEG con bytes REALES — el contrato de media valida por magic
// bytes (§5 de API_EQUIPOS_v1.md), no por Content-Type. El truco de los
// specs actuales de Presupuestos (`Buffer.from("%PDF-1.4...")`) pasa ahí
// porque el endpoint de tickets no valida magic bytes, pero fallaría aquí
// con 422 MEDIA_INVALIDA. Sin dependencias nuevas: solo `node:zlib`.

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

// Tabla CRC32 estándar (IEEE 802.3 / Anexo D de la especificación PNG).
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const typeBuf = Buffer.from(type, "ascii");
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

function pngFromPixels(ancho, alto, pixelFn) {
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(ancho, 0);
  ihdrData.writeUInt32BE(alto, 4);
  ihdrData.writeUInt8(8, 8); // bit depth
  ihdrData.writeUInt8(2, 9); // color type: RGB truecolor
  ihdrData.writeUInt8(0, 10); // compression
  ihdrData.writeUInt8(0, 11); // filtro (a nivel de método)
  ihdrData.writeUInt8(0, 12); // interlace

  const raw = Buffer.alloc((1 + ancho * 3) * alto);
  for (let y = 0; y < alto; y++) {
    const rowStart = y * (1 + ancho * 3);
    raw[rowStart] = 0; // filtro de scanline "none"
    for (let x = 0; x < ancho; x++) {
      const [r, g, b] = pixelFn(x, y);
      const px = rowStart + 1 + x * 3;
      raw[px] = r;
      raw[px + 1] = g;
      raw[px + 2] = b;
    }
  }
  const idatData = zlib.deflateSync(raw);

  return Buffer.concat([
    PNG_SIGNATURE,
    pngChunk("IHDR", ihdrData),
    pngChunk("IDAT", idatData),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

/** PNG RGB truecolor válido de verdad — firma, IHDR, IDAT (zlib real), IEND,
 * con CRC32 correctos. Color sólido: pasa magic bytes y comprime a pocos KB
 * (adecuado para fotos/firmas normales, NO para fotoGrande — ver abajo). */
export function pngReal(ancho = 64, alto = 64, color = [251, 103, 11]) {
  return pngFromPixels(ancho, alto, () => color);
}

/** JPEG mínimo válido (1x1 px) — constante base64 de un encoder real: un
 * JPEG no se puede sintetizar a mano byte a byte como el PNG sin
 * implementar DCT + codificación Huffman completas. */
const JPEG_1X1_BASE64 =
  "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=";

export function jpegReal() {
  return Buffer.from(JPEG_1X1_BASE64, "base64");
}

/** > 3 MB para provocar 413 MEDIA_MUY_GRANDE. Ruido, NO color sólido: un
 * PNG de color plano comprime a unos cuantos KB sin importar el lienzo
 * (deflate ama la repetición) y jamás dispararía el límite real de 3 MB —
 * el ruido es incompresible por diseño. */
export function fotoGrande() {
  return pngFromPixels(1400, 900, () => [
    Math.floor(Math.random() * 256),
    Math.floor(Math.random() * 256),
    Math.floor(Math.random() * 256),
  ]);
}

/** PNG de firma, pensado para quedar bajo 250 KB (color sólido, chico). */
export function firmaPng() {
  return pngReal(300, 120, [38, 38, 38]);
}
