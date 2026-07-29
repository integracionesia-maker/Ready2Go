const backend = import.meta.env.VITE_EQUIPOS_MOCK === "1" ? import("./mock/loans") : import("./real/loans");

export async function createLoan(data) {
  return (await backend).createLoan(data);
}
export async function fetchLoans(params) {
  return (await backend).fetchLoans(params);
}
export async function fetchLoanById(id) {
  return (await backend).fetchLoanById(id);
}
export async function fetchLoanByFolio(folio) {
  return (await backend).fetchLoanByFolio(folio);
}
export async function addLoanItem(loanId, data) {
  return (await backend).addLoanItem(loanId, data);
}
export async function removeLoanItem(loanId, itemId) {
  return (await backend).removeLoanItem(loanId, itemId);
}
export async function confirmLoan(loanId) {
  return (await backend).confirmLoan(loanId);
}
export async function cancelLoan(loanId) {
  return (await backend).cancelLoan(loanId);
}
export async function returnLoan(loanId, data) {
  return (await backend).returnLoan(loanId, data);
}
export async function authorizeDelivery(loanId) {
  return (await backend).authorizeDelivery(loanId);
}
export async function confirmReturnDecision(loanId, decisiones) {
  return (await backend).confirmReturnDecision(loanId, decisiones);
}
export async function closeIncident(loanId, nota) {
  return (await backend).closeIncident(loanId, nota);
}
export async function loanResponsivaUrl(loanId) {
  return (await backend).loanResponsivaUrl(loanId);
}
