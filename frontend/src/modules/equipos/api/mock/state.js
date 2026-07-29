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

export const state = {
  equipos: clone(equiposFixture.items),
  loans: [clone(prestamoDemoFixture)],
  empresas: clone(empresasFixture),
  media: new Map(), // id -> { kind, dataUrl, sha256 }
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
