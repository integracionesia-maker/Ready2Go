import { state } from "./state";
import { checkGlobalInjection } from "./errorInjection";
import { throwNotFound } from "./mockErrors";

export async function fetchEmpresas() {
  checkGlobalInjection();
  return state.empresas;
}

export async function createEmpresa(data) {
  checkGlobalInjection();
  const id = Math.max(0, ...state.empresas.map((e) => e.id)) + 1;
  const nueva = { id, is_active: true, direccion: null, ciudad: null, rfc: null, ...data };
  state.empresas.push(nueva);
  return nueva;
}

export async function updateEmpresa(id, data) {
  checkGlobalInjection();
  const idx = state.empresas.findIndex((e) => e.id === id);
  if (idx === -1) throwNotFound(`Empresa ${id} no encontrada.`);
  state.empresas[idx] = { ...state.empresas[idx], ...data };
  return state.empresas[idx];
}
