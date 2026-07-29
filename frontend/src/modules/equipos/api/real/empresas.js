import { request } from "@/api";

export function fetchEmpresas() {
  return request("/empresas/");
}

export function createEmpresa(data) {
  return request("/empresas/", { method: "POST", body: JSON.stringify(data) });
}

export function updateEmpresa(id, data) {
  return request(`/empresas/${id}`, { method: "PUT", body: JSON.stringify(data) });
}
