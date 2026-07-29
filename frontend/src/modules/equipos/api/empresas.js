const backend = import.meta.env.VITE_EQUIPOS_MOCK === "1" ? import("./mock/empresas") : import("./real/empresas");

export async function fetchEmpresas() {
  return (await backend).fetchEmpresas();
}
export async function createEmpresa(data) {
  return (await backend).createEmpresa(data);
}
export async function updateEmpresa(id, data) {
  return (await backend).updateEmpresa(id, data);
}
