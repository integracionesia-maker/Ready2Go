import { request, BASE } from "@/api";

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

export function cancelLoan(loanId) {
  return request(`/loans/${loanId}/cancelar`, { method: "POST" });
}

// El contrato (§3) describe la REGLA de /devolucion (2 fotos por equipo o
// no_devuelto+nota) pero no da un ejemplo de body JSON como sí hace con
// /confirmar-devolucion — a diferencia de ahí, aquí se está adivinando la
// forma (`items: [...]`). Reportado como riesgo nuevo (R-I13); si el
// servidor espera otra forma, este es el primer lugar a revisar cuando
// llegue el servidor real.
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

export function fetchLoansExport(params) {
  return request(`/loans/export${params ? `?${new URLSearchParams(params)}` : ""}`);
}

export function loanResponsivaUrl(loanId) {
  return `${BASE}/loans/${loanId}/responsiva.pdf`;
}
