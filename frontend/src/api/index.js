/**
 * Barril público de la API: todo el resto de la app importa de `@/api`.
 * Aquí viven las funciones por dominio; el transporte (fetch, refresh de
 * sesión, reintento por 401) vive en `./client.js`.
 * Todas las llamadas devuelven JSON parseado; los errores lanzan con mensaje.
 */

import { BASE, fetchWithAuthRetry, request, throwApiError } from "./client";

// Re-exportados para que los consumidores sigan importando de `@/api` y no
// necesiten conocer `./client`: `isNetworkError` lo usan App.jsx y las vistas,
// `setAuthFailureHandler` lo usa AuthContext, y `request`/`fetchWithAuthRetry`
// los va a necesitar el cliente de API del modulo de equipos (JSON y multipart).
// `ApiError`/`esCodigo` (R-I09): el módulo de Equipos los necesita para
// distinguir los cinco códigos feos del contrato sin parsear `message` a mano.
// `refreshSession` NO se re-exporta a proposito: es interno del reintento por
// 401 y ningun consumidor debe dispararlo a mano.
export { isNetworkError, setAuthFailureHandler, fetchWithAuthRetry, request, ApiError, esCodigo, BASE, throwApiError } from "./client";

/* ── Auth ────────────────────────────────────────────────────────────────── */

export function login(identificador, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ identificador, password }),
  });
}

export function logout() {
  return request("/auth/logout", { method: "POST" });
}

export function fetchMe() {
  return request("/auth/me");
}

export function updateMe(data) {
  return request("/auth/me", { method: "PUT", body: JSON.stringify(data) });
}

export function changePassword(currentPassword, newPassword) {
  return request("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

/* ── Usuarios (Administración) ──────────────────────────────────────────── */

export function fetchUsers(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request(`/users/${suffix}`);
}

export function createUser(data) {
  return request("/users/", { method: "POST", body: JSON.stringify(data) });
}

export function updateUser(id, data) {
  return request(`/users/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export function resetUserPassword(id) {
  return request(`/users/${id}/reset-password`, { method: "POST" });
}

// Reset de contraseña ENTRE superadmins (2026-08-19): la única operación
// permitida sobre la cuenta superadmin; nunca aplica sobre uno mismo.
export function resetSuperadminPassword(id) {
  return request(`/users/${id}/reset-password-superadmin`, { method: "POST" });
}

export function setUserActive(id, isActive) {
  return request(`/users/${id}/estado`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: isActive }),
  });
}

/* ── Roles y permisos (RBAC aditivo, solo superadmin) ───────────────────── */

export function fetchRoles() {
  return request("/roles/");
}

export function fetchUserRoles(userId) {
  return request(`/users/${userId}/roles`);
}

export function grantUserRole(userId, roleName) {
  return request(`/users/${userId}/roles`, {
    method: "POST",
    body: JSON.stringify({ role_name: roleName }),
  });
}

export function revokeUserRole(userId, roleName) {
  return request(`/users/${userId}/roles/${roleName}`, { method: "DELETE" });
}

/* ── Auditoría (solo superadmin) ─────────────────────────────────────────── */

export function fetchAuditLogs(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request(`/audit-logs/${suffix}`);
}

export function fetchAuditLogDetail(id) {
  return request(`/audit-logs/${id}`);
}

export function fetchAuditStats() {
  return request("/audit-logs/stats");
}

/* ── Creators ────────────────────────────────────────────────────────────── */

export function fetchCreators(activeOnly = false) {
  const qs = activeOnly ? "?active_only=true" : "";
  return request(`/creators/${qs}`);
}

export function fetchCreatorsKpi() {
  return request("/creators/kpi");
}

export function createCreator(data) {
  return request("/creators/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateCreator(id, data) {
  return request(`/creators/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function fetchCreatorCycles(id) {
  return request(`/creators/${id}/ciclos`);
}

/* ── Brands ──────────────────────────────────────────────────────────────── */

export function fetchBrands(activeOnly = true) {
  const qs = activeOnly ? "?active_only=true" : "";
  return request(`/brands/${qs}`);
}

export function createBrand(data) {
  return request("/brands/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateBrand(id, data) {
  return request(`/brands/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/* ── Tickets ─────────────────────────────────────────────────────────────── */

export function fetchTickets({ creatorName, brandName, status } = {}) {
  const params = new URLSearchParams();
  if (creatorName) params.set("creator_name", creatorName);
  if (brandName) params.set("brand_name", brandName);
  if (status) params.set("status", status);
  const qs = params.toString();
  return request(`/tickets/${qs ? `?${qs}` : ""}`);
}

export function approveTicket(id) {
  return request(`/tickets/${id}/aprobar`, { method: "POST" });
}

export function rejectTicket(id, reason) {
  return request(`/tickets/${id}/rechazar`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function fetchBrandSpendBreakdown(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/tickets/brand-spend${qs ? `?${qs}` : ""}`, { signal });
}

export async function uploadTicket({ creatorId, brandId, amount, notes, file }) {
  const formData = new FormData();
  formData.append("creator_id", creatorId);
  formData.append("brand_id", brandId);
  formData.append("amount", amount);
  if (notes) formData.append("notes", notes);
  formData.append("file", file);

  const res = await fetchWithAuthRetry("/tickets/", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) await throwApiError(res);

  return res.json();
}

export function ticketFileUrl(ticketId) {
  return `${BASE}/tickets/file/${ticketId}`;
}

export function softDeleteTicket(id) {
  return request(`/tickets/${id}/soft-delete`, { method: "POST" });
}

export function hardDeleteTicket(id) {
  return request(`/tickets/${id}/permanent`, { method: "DELETE" });
}

/* ── Gastos Generales ────────────────────────────────────────────────────── */

export function fetchGeneralExpenses({ startDate, endDate } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/general-expenses/${qs ? `?${qs}` : ""}`);
}

export async function createGeneralExpense({ brandId, amount, description, file }) {
  const formData = new FormData();
  formData.append("brand_id", brandId);
  formData.append("amount", amount);
  formData.append("description", description);
  formData.append("file", file);

  const res = await fetchWithAuthRetry("/general-expenses/", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) await throwApiError(res);

  return res.json();
}

export function softDeleteGeneralExpense(id) {
  return request(`/general-expenses/${id}/soft-delete`, { method: "POST" });
}

export function hardDeleteGeneralExpense(id) {
  return request(`/general-expenses/${id}/permanent`, { method: "DELETE" });
}

export function generalExpenseFileUrl(id) {
  return `${BASE}/general-expenses/${id}/file`;
}

export function fetchGeneralExpensesExport(months) {
  const params = new URLSearchParams();
  params.set("months", months.join(","));
  return request(`/general-expenses/export?${params.toString()}`);
}

/* ── Gastos Operativos (fusionados en UI con Gastos Generales) ──────────────
 * Tabla y endpoints propios (rubro + fecha_gasto, solo borrado lógico) — la
 * fusión es de UI, no de esquema. `startDate`/`endDate` ya vienen formateadas
 * (`YYYY-MM-DD`) por quien llama, igual que el resto de este archivo.
 */

export function listRubros(activeOnly = false) {
  return request(`/rubros/${activeOnly ? "?active_only=true" : ""}`);
}

export function createRubro(nombre) {
  return request("/rubros/", { method: "POST", body: JSON.stringify({ nombre }) });
}

export function updateRubro(id, data) {
  return request(`/rubros/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export function listOperationalExpenses({ rubroId, startDate, endDate } = {}) {
  const params = new URLSearchParams();
  if (rubroId) params.set("rubro_id", rubroId);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/operational-expenses/${qs ? `?${qs}` : ""}`);
}

export async function createOperationalExpense({ rubroId, amount, description, fechaGasto, file }) {
  const formData = new FormData();
  formData.append("rubro_id", rubroId);
  formData.append("amount", amount);
  formData.append("description", description);
  formData.append("fecha_gasto", fechaGasto);
  formData.append("file", file);

  const res = await fetchWithAuthRetry("/operational-expenses/", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) await throwApiError(res);

  return res.json();
}

export function softDeleteOperationalExpense(id) {
  return request(`/operational-expenses/${id}/soft-delete`, { method: "POST" });
}

export function operationalExpenseFileUrl(id) {
  return `${BASE}/operational-expenses/${id}/file`;
}

export function fetchOperationalExpensesExport(months) {
  const params = new URLSearchParams();
  params.set("months", months.join(","));
  return request(`/operational-expenses/export?${params.toString()}`);
}

export function fetchOperationalDashboard(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/operational-expenses/dashboard${qs ? `?${qs}` : ""}`, { signal });
}

/* ── Dashboard ─────────────────────────────────────────────────────────────── */

export function fetchDashboardSummary(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/dashboard/summary${qs ? `?${qs}` : ""}`, { signal });
}

export function fetchMonthlySpend(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/dashboard/monthly-spend${qs ? `?${qs}` : ""}`, { signal });
}

export function fetchCreatorUsage(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/dashboard/creator-usage${qs ? `?${qs}` : ""}`, { signal });
}

export function fetchGeneralExpensesMonthly(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/dashboard/general-expenses-monthly${qs ? `?${qs}` : ""}`, { signal });
}

export function fetchTicketsPerDay(startDate, endDate, { signal } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/dashboard/tickets-per-day${qs ? `?${qs}` : ""}`, { signal });
}

/** Reporte del dashboard generado en backend (reportlab, vectores nativos —
 * ver backend/app/pdf/dashboard_reporte.py). Descarga directa: a diferencia
 * del resto del archivo, esta función no devuelve JSON, dispara un archivo. */
export async function downloadDashboardReportPdf(startDate, endDate) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  const res = await fetchWithAuthRetry(`/dashboard/report.pdf${qs ? `?${qs}` : ""}`);
  if (!res.ok) await throwApiError(res);
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] || "reporte-presupuesto.pdf";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
