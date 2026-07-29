const backend = import.meta.env.VITE_EQUIPOS_MOCK === "1" ? import("./mock/permisos") : import("./real/permisos");

export async function fetchPermisosCatalogo() {
  return (await backend).fetchPermisosCatalogo();
}
export async function fetchAuthMeMock() {
  return (await backend).fetchAuthMeMock();
}
