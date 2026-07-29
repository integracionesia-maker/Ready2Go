// Decide el transporte UNA vez por carga de módulo (la promesa se cachea):
// import.meta.env.VITE_EQUIPOS_MOCK es una constante conocida en build time,
// así que Rollup elimina la rama muerta — en un build de producción sin la
// variable, el import("./mock/...") ni siquiera entra al bundle.
const backend =
  import.meta.env.VITE_EQUIPOS_MOCK === "1" ? import("./mock/equipment") : import("./real/equipment");

export async function fetchEquipmentList(params) {
  return (await backend).fetchEquipmentList(params);
}
export async function fetchEquipmentDashboard() {
  return (await backend).fetchEquipmentDashboard();
}
export async function fetchEquipmentById(id) {
  return (await backend).fetchEquipmentById(id);
}
export async function createEquipment(data) {
  return (await backend).createEquipment(data);
}
export async function updateEquipment(id, data) {
  return (await backend).updateEquipment(id, data);
}
export async function auditEquipment(id, data) {
  return (await backend).auditEquipment(id, data);
}
export async function dischargeEquipment(id) {
  return (await backend).dischargeEquipment(id);
}
