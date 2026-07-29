import equiposFixture from "./fixtures/equipos.json";
import prestamoDemoFixture from "./fixtures/prestamo_demo.json";
import empresasFixture from "./fixtures/empresas.json";

// Copia profunda: las mutaciones del mock no deben tocar el objeto importado
// del fixture (Vite puede compartirlo por referencia entre módulos/HMR), Y
// (uso más amplio, ver loans.js) todo lo que el mock DEVUELVE a un
// consumidor debe ser una copia, nunca la referencia viva de `state` — un
// backend real siempre deserializa una respuesta fresca; si el mock
// entrega la misma referencia dos veces, un `setState(freshLoan)` en React
// puede ser un no-op silencioso (misma identidad de objeto) aunque el
// contenido ya haya cambiado por otra mutación mientras tanto.
export function clone(x) {
  return JSON.parse(JSON.stringify(x));
}

// `fixtures/prestamo_demo.json` referencia media ids 39-42 (firmas del
// préstamo confirmado + fotos de entrega) como si ya existieran — son el
// criterio de aceptación de la ficha (I4g), pero ningún archivo real viaja
// con el mock. Sin sembrar estas 4 entradas, `mediaUrl()` truena con
// "no encontrada" en cuanto la ficha intenta pintar sus miniaturas: el
// préstamo demo quedaría con las únicas 4 fotos/firmas que el contrato
// promete que siempre tiene, pero ninguna se vería. Placeholder SVG (sin
// dependencias, sin canvas) — no pretende ser una foto real, solo darle
// al mock algo que `mediaUrl()` pueda resolver.
function placeholderDataUrl(etiqueta, color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="${color}"/><text x="100" y="104" font-family="sans-serif" font-size="16" fill="#fff" text-anchor="middle">${etiqueta}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

const MEDIA_DEMO_SEED = [
  [39, "firma_entrega", "Firma (demo)", "#535353"],
  [40, "firma_responsable", "Firma (demo)", "#535353"],
  [41, "foto_entrega_frente", "Foto (demo)", "#FB670B"],
  [42, "foto_entrega_atras", "Foto (demo)", "#FB670B"],
];

export const state = {
  equipos: clone(equiposFixture.items),
  loans: [clone(prestamoDemoFixture)],
  empresas: clone(empresasFixture),
  media: new Map(
    MEDIA_DEMO_SEED.map(([id, kind, etiqueta, color]) => [
      id,
      { kind, loanId: 7, dataUrl: placeholderDataUrl(etiqueta, color), sha256: `demo-seed-${id}` },
    ])
  ),
  folioCounter: 7, // el demo ya trae CE-0007
  mediaIdCounter: 100,
  loanIdCounter: 100,
};

const ESTADOS_ABIERTOS = ["borrador", "prestado", "pendiente_confirmacion", "incompleto"];

/** No existe `estado = "prestado"` en el equipo (regla dura del contrato):
 * la disponibilidad se deriva de si hay un préstamo abierto que lo incluya. */
export function equipoTieneAbiertoUnLoan(equipmentId, excludeLoanId) {
  return state.loans.some(
    (loan) =>
      loan.id !== excludeLoanId &&
      ESTADOS_ABIERTOS.includes(loan.estado) &&
      loan.items.some((it) => it.equipment_id === equipmentId)
  );
}
