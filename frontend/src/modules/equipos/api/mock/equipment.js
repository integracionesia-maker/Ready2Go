import { state, equipoTieneAbiertoUnLoan } from "./state";
import { checkGlobalInjection } from "./errorInjection";
import { throwFixtureError, throwNotFound } from "./mockErrors";

/** `disponible` es SIEMPRE derivado (no existe `estado_operativo="prestado"`),
 * recalculado contra el estado vivo de los préstamos, no contra el valor
 * estático que trae el fixture. */
function withComputedDisponible(item) {
  const ocupado = equipoTieneAbiertoUnLoan(item.id);
  return { ...item, disponible: item.estado_operativo === "activo" && !ocupado };
}

export async function fetchEquipmentList({ q, categoria, condicion, disponible, limit = 50, offset = 0 } = {}) {
  checkGlobalInjection();
  let items = state.equipos.map(withComputedDisponible);
  if (q) {
    const needle = q.toLowerCase();
    items = items.filter((e) => e.nombre.toLowerCase().includes(needle));
  }
  if (categoria) items = items.filter((e) => e.categoria === categoria);
  if (condicion) items = items.filter((e) => e.condicion === condicion);
  if (disponible != null) {
    const wantDisponible = disponible === true || disponible === "true";
    items = items.filter((e) => e.disponible === wantDisponible);
  }
  const total = items.length;
  return { items: items.slice(offset, offset + limit), total };
}

export async function fetchEquipmentDashboard() {
  checkGlobalInjection();
  const items = state.equipos.map(withComputedDisponible);
  const prestados = state.loans.filter((l) => l.estado === "prestado").length;
  const atrasados = items.filter((e) => e.atrasado).length;
  const pendientesConfirmacion = state.loans.filter((l) => l.estado === "pendiente_confirmacion").length;
  const disponibles = items.filter((e) => e.disponible).length;
  const porEstado = state.loans.reduce((acc, l) => {
    acc[l.estado] = (acc[l.estado] || 0) + 1;
    return acc;
  }, {});
  const requiereAtencion = state.loans
    .filter((l) => l.atrasado)
    .map((l) => ({
      loan_id: l.id,
      folio: l.folio,
      motivo: `atrasado ${l.dias_atraso} dias`,
      responsable: l.responsable?.nombre,
      equipos: l.items.map((it) => it.equipo_nombre),
    }));
  return {
    prestados,
    atrasados,
    pendientes_confirmacion: pendientesConfirmacion,
    disponibles,
    por_estado: porEstado,
    requiere_atencion: requiereAtencion,
  };
}

export async function fetchEquipmentById(id) {
  checkGlobalInjection();
  const item = state.equipos.find((e) => e.id === id);
  if (!item) throwNotFound(`Equipo ${id} no encontrado.`);
  return withComputedDisponible(item);
}

export async function createEquipment(data) {
  checkGlobalInjection();
  const id = Math.max(0, ...state.equipos.map((e) => e.id)) + 1;
  const nuevo = {
    id,
    disponible: true,
    atrasado: false,
    dias_atraso: 0,
    tenedor_actual: null,
    fecha_regreso_esperada: null,
    ...data,
  };
  state.equipos.push(nuevo);
  return nuevo;
}

export async function updateEquipment(id, data) {
  checkGlobalInjection();
  const idx = state.equipos.findIndex((e) => e.id === id);
  if (idx === -1) throwNotFound(`Equipo ${id} no encontrado.`);
  state.equipos[idx] = { ...state.equipos[idx], ...data };
  return state.equipos[idx];
}

export async function auditEquipment(id, data) {
  checkGlobalInjection();
  const idx = state.equipos.findIndex((e) => e.id === id);
  if (idx === -1) throwNotFound(`Equipo ${id} no encontrado.`);
  state.equipos[idx] = {
    ...state.equipos[idx],
    condicion: data.condicion ?? state.equipos[idx].condicion,
    estado_fisico: data.estado_fisico ?? state.equipos[idx].estado_fisico,
    comentario_auditoria: data.comentario_auditoria ?? state.equipos[idx].comentario_auditoria,
    fecha_auditoria: data.fecha_auditoria ?? new Date().toISOString().slice(0, 10),
  };
  return state.equipos[idx];
}

export async function dischargeEquipment(id) {
  checkGlobalInjection();
  if (equipoTieneAbiertoUnLoan(id)) throwFixtureError("EQUIPO_OCUPADO");
  const idx = state.equipos.findIndex((e) => e.id === id);
  if (idx === -1) throwNotFound(`Equipo ${id} no encontrado.`);
  state.equipos[idx].estado_operativo = "baja";
  return state.equipos[idx];
}
