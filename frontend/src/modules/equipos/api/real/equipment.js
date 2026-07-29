import { request } from "@/api";

export function fetchEquipmentList({ q, categoria, condicion, disponible, limit, offset } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (categoria) params.set("categoria", categoria);
  if (condicion) params.set("condicion", condicion);
  if (disponible != null) params.set("disponible", String(disponible));
  if (limit != null) params.set("limit", String(limit));
  if (offset != null) params.set("offset", String(offset));
  const qs = params.toString();
  // /dashboard se declara antes de /{id:int} en el servidor real (§2) — el
  // cliente no lo necesita saber, solo no inventar una ruta que colisione.
  return request(`/equipment/${qs ? `?${qs}` : ""}`);
}

export function fetchEquipmentDashboard() {
  return request("/equipment/dashboard");
}

export function fetchEquipmentById(id) {
  return request(`/equipment/${id}`);
}

export function createEquipment(data) {
  return request("/equipment/", { method: "POST", body: JSON.stringify(data) });
}

export function updateEquipment(id, data) {
  return request(`/equipment/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export function auditEquipment(id, data) {
  return request(`/equipment/${id}/auditoria`, { method: "POST", body: JSON.stringify(data) });
}

// I8 lote 1 (mismo patrón que cancelLoan): `BajaRequest` es un cuerpo
// obligatorio en el router aunque `motivo` sea opcional. Sin `body`, un 422
// real por "Expecting value" en cuanto alguien de de baja un equipo.
export function dischargeEquipment(id, motivo) {
  return request(`/equipment/${id}/baja`, {
    method: "POST",
    body: JSON.stringify({ motivo: motivo ?? null }),
  });
}
