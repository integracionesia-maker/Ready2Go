import { request, BASE, fetchWithAuthRetry, throwApiError } from "@/api";

// R-I14 (docs/riesgos/interfaz.md): el contrato ejemplifica la RESPUESTA de
// GET /loans/{id} pero no el BODY de escritura de createLoan/addLoanItem/
// authorizeDelivery. Los nombres de campo de abajo (snake_case, calcados
// del ejemplo de lectura) son una asunción razonable, no confirmada — el
// primer lugar a revisar si el body no calza cuando el servidor real
// aterrice.

export function createLoan(data) {
  return request("/loans/", { method: "POST", body: JSON.stringify(data) });
}

export function fetchLoans({ estado, mios, q, desde, hasta, limit, offset } = {}) {
  const params = new URLSearchParams();
  if (estado) params.set("estado", estado);
  if (mios != null) params.set("mios", mios ? "1" : "0");
  if (q) params.set("q", q);
  if (desde) params.set("desde", desde);
  if (hasta) params.set("hasta", hasta);
  if (limit != null) params.set("limit", String(limit));
  if (offset != null) params.set("offset", String(offset));
  const qs = params.toString();
  return request(`/loans/${qs ? `?${qs}` : ""}`);
}

export function fetchLoanById(id) {
  return request(`/loans/${id}`);
}

export function fetchLoanByFolio(folio) {
  return request(`/loans/by-folio/${folio}`);
}

// Quien tiene hoy el paquete singleton TITULAR_FIRMA_EQUIPO — `firma_entrega`
// es identidad, no permiso (ver backend/app/routers/loans.py:subir_media), así
// que el botón "Firmar" del aprobador solo se pinta para `soy_titular`.
export function fetchTitularFirmaEquipo() {
  return request("/loans/titular-firma-equipo");
}

export function addLoanItem(loanId, { equipmentId, accesoriosSeleccionados, accesoriosOtros, cargadorCon }) {
  return request(`/loans/${loanId}/items`, {
    method: "POST",
    body: JSON.stringify({
      equipment_id: equipmentId,
      accesorios_seleccionados: accesoriosSeleccionados,
      accesorios_otros: accesoriosOtros,
      cargador_con: cargadorCon,
    }),
  });
}

export function removeLoanItem(loanId, itemId) {
  return request(`/loans/${loanId}/items/${itemId}`, { method: "DELETE" });
}

export function confirmLoan(loanId) {
  return request(`/loans/${loanId}/confirmar`, { method: "POST" });
}

// I8 lote 1 (hallazgo adicional, mismo patrón que 1.1/1.2 pero no nombrado
// en el prompt): `CancelarRequest` es un parámetro de cuerpo obligatorio en
// `routers/loans.py:415` aunque su único campo (`motivo`) sea opcional —
// FastAPI exige que llegue *algún* JSON, y sin `body` el fetch no manda
// nada. Sin este fix, descartar un borrador recuperado (wizard) responde
// 422 contra el servidor real.
export function cancelLoan(loanId, motivo) {
  return request(`/loans/${loanId}/cancelar`, {
    method: "POST",
    body: JSON.stringify({ motivo: motivo ?? null }),
  });
}

// I8 lote 1: la FORMA exterior que R-I13 adivinó (`{items: [...]}`) resultó
// correcta contra el servidor real (`DevolucionRequest`) — acertó la
// estructura. Lo que fallaba eran las LLAVES de cada item: el caller mandaba
// camelCase (`itemId`/`noDevuelto`/`notaDevolucion`) y `DevolucionItem`
// exige snake_case (`loan_item_id`/`no_devuelto`/`nota_devolucion`, el
// primero sin default → 422 en cuanto faltaba). Reproducido contra el
// servidor real antes de arreglarlo (ver docs/avances/interfaz.md, I8).
// Sin conversión aquí a propósito — mismo patrón que `confirmReturnDecision`
// (abajo): el caller ya manda las llaves reales de la API (ver
// `RegistrarDevolucionModal.jsx`), este archivo solo hace el POST.
export function returnLoan(loanId, { decisionesPorItem }) {
  return request(`/loans/${loanId}/devolucion`, {
    method: "POST",
    body: JSON.stringify({ items: decisionesPorItem }),
  });
}

export function authorizeDelivery(loanId) {
  return request(`/loans/${loanId}/autorizar-entrega`, { method: "POST" });
}

export function confirmReturnDecision(loanId, decisiones) {
  return request(`/loans/${loanId}/confirmar-devolucion`, {
    method: "POST",
    body: JSON.stringify({ decisiones }),
  });
}

export function closeIncident(loanId, nota) {
  return request(`/loans/${loanId}/cerrar-incidencia`, {
    method: "POST",
    body: JSON.stringify({ nota }),
  });
}

// Bug de I3 corregido en I4f: esto usaba `request()`, que siempre hace
// `res.json()` — un CSV no es JSON. `fetch → blob → descarga` (I4f):
// si el servidor responde 403/503, `throwApiError` parsea el sobre de
// error real y lo lanza como ApiError, en vez de dejar que el navegador
// descargue un archivo .csv cuyo contenido es el cuerpo del error.
export async function fetchLoansExport({ estado, q, desde, hasta } = {}) {
  const params = new URLSearchParams();
  if (estado) params.set("estado", estado);
  if (q) params.set("q", q);
  if (desde) params.set("desde", desde);
  if (hasta) params.set("hasta", hasta);
  const qs = params.toString();
  const res = await fetchWithAuthRetry(`/loans/export${qs ? `?${qs}` : ""}`);
  if (!res.ok) await throwApiError(res);
  return res.blob();
}

export function loanResponsivaUrl(loanId) {
  return `${BASE}/loans/${loanId}/responsiva.pdf`;
}
