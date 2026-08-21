/**
 * API del módulo Gastos Operativos. Usa el transporte compartido de `@/api`
 * (cookies de sesión, reintento por 401). Multipart para el alta de gastos:
 * nunca fijar Content-Type a mano (el navegador pone el boundary).
 */
import { BASE, request, fetchWithAuthRetry, throwApiError } from "@/api";

function fmtDate(d) {
  if (!d) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function qs(params) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.append(k, v);
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/* ── Rubros ─────────────────────────────────────────────────────────────── */

export function listRubros(activeOnly = false) {
  return request(`/rubros/${activeOnly ? "?active_only=true" : ""}`);
}

export function createRubro(nombre) {
  return request("/rubros/", { method: "POST", body: JSON.stringify({ nombre }) });
}

export function updateRubro(id, data) {
  return request(`/rubros/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

/* ── Gastos ─────────────────────────────────────────────────────────────── */

export function listOperationalExpenses({ rubroId, startDate, endDate } = {}) {
  return request(
    `/operational-expenses/${qs({
      rubro_id: rubroId,
      start_date: fmtDate(startDate),
      end_date: fmtDate(endDate),
    })}`
  );
}

export function operationalDashboard({ startDate, endDate } = {}) {
  return request(
    `/operational-expenses/dashboard${qs({
      start_date: fmtDate(startDate),
      end_date: fmtDate(endDate),
    })}`
  );
}

export function exportOperationalExpenses(months) {
  return request(`/operational-expenses/export${qs({ months })}`);
}

export function operationalExpenseFileUrl(id) {
  return `${BASE}/operational-expenses/${id}/file`;
}

export async function createOperationalExpense({ rubroId, amount, description, fechaGasto, file }) {
  const fd = new FormData();
  fd.append("rubro_id", rubroId);
  fd.append("amount", amount);
  fd.append("description", description);
  fd.append("fecha_gasto", fmtDate(fechaGasto instanceof Date ? fechaGasto : new Date(fechaGasto + "T00:00:00")));
  fd.append("file", file);
  const res = await fetchWithAuthRetry("/operational-expenses/", { method: "POST", body: fd });
  if (!res.ok) await throwApiError(res);
  return res.json();
}

export function softDeleteOperationalExpense(id) {
  return request(`/operational-expenses/${id}/soft-delete`, { method: "POST" });
}
