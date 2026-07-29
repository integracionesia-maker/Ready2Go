import { ApiError } from "@/api";
import { state, equipoTieneAbiertoUnLoan, clone } from "./state";
import { checkGlobalInjection, checkInjection } from "./errorInjection";
import { throwFixtureError, throwNotFound } from "./mockErrors";

// Referencia VIVA a propósito (nunca clonada aquí): las funciones públicas
// de abajo llaman a `findLoan` y LUEGO mutan el resultado esperando que esa
// mutación se refleje en `state.loans` — clonar aquí dejaría cada mutación
// escribiendo sobre una copia desechable que nunca vuelve a `state`. El
// clon vive solo en la frontera pública (cada `export async function`
// abajo clona justo antes de devolver, no antes).
function findLoan(id) {
  const loan = state.loans.find((l) => l.id === id);
  if (!loan) throwNotFound(`Préstamo ${id} no encontrado.`);
  return loan;
}

function ahora() {
  return new Date().toISOString();
}

export async function fetchLoans({ estado, q, desde, hasta, limit = 50, offset = 0 } = {}) {
  checkGlobalInjection();
  let items = state.loans;
  if (estado) items = items.filter((l) => l.estado === estado);
  // `mios`: el mock no resuelve un usuario "actual" real todavía (no hay
  // sesión propia de Equipos) — I4 decide cómo filtrar por responsable
  // cuando construya el wizard; por ahora se ignora sin romper la llamada.
  if (q) {
    const needle = q.toLowerCase();
    items = items.filter(
      (l) =>
        l.folio?.toLowerCase().includes(needle) ||
        l.motivo?.toLowerCase().includes(needle) ||
        l.responsable?.nombre?.toLowerCase().includes(needle)
    );
  }
  // `desde`/`hasta` (I4f, Historial): el contrato no dice contra qué campo
  // de fecha filtran — se decidió `fecha_entrega` (cuándo arrancó el
  // préstamo de verdad, no cuándo se creó el borrador). Comparación de
  // strings "YYYY-MM-DD" en vez de `new Date()`: el orden lexicográfico de
  // ese formato ya es cronológico, sin el riesgo de zona horaria que
  // prohíbe la regla dura del módulo. Un préstamo sin `fecha_entrega`
  // (`borrador`/`cancelado` antes de confirmar) no matchea ningún rango.
  if (desde) items = items.filter((l) => l.fecha_entrega && l.fecha_entrega >= desde);
  if (hasta) items = items.filter((l) => l.fecha_entrega && l.fecha_entrega <= hasta);
  const total = items.length;
  return { items: items.slice(offset, offset + limit).map(clone), total };
}

export async function fetchLoanById(id) {
  checkGlobalInjection();
  return clone(findLoan(id));
}

export async function fetchLoanByFolio(folio) {
  checkGlobalInjection();
  const loan = state.loans.find((l) => l.folio === folio);
  if (!loan) throwNotFound(`Folio ${folio} no encontrado.`);
  return clone(loan);
}

export async function createLoan(data = {}) {
  checkGlobalInjection();
  const id = ++state.loanIdCounter;
  // I8 lote 2: `LoanCreate` real exige las tres claves de responsable PLANAS
  // (`responsable_user_id/nombre/email`, fix de I8 lote 1.2 en
  // `NuevoPrestamoPage.jsx`) — el mock seguía leyendo un `data.responsable`
  // anidado que el caller ya no manda desde ese fix, así que todo préstamo
  // nuevo en modo mock quedaba con `responsable: null` en silencio.
  const responsable =
    data.responsable_user_id != null
      ? { user_id: data.responsable_user_id, nombre: data.responsable_nombre, email: data.responsable_email }
      : (data.responsable ?? null);
  const loan = {
    id,
    folio: null,
    estado: "borrador",
    responsable,
    area: data.area ?? null,
    empresa: data.empresa ?? null,
    motivo: data.motivo ?? null,
    notas_responsiva: data.notas_responsiva ?? null,
    entregado_por: null,
    fecha_entrega: null,
    fecha_regreso_esperada: data.fecha_regreso_esperada ?? null,
    fecha_regreso_real: null,
    atrasado: false,
    dias_atraso: 0,
    entrega_autorizada: false,
    entrega_autorizada_por: null,
    fecha_autorizacion_entrega: null,
    confirmada_por: null,
    fecha_confirmacion: null,
    items: [],
    firmas: { firma_entrega: null, firma_responsable: null },
    responsiva: null,
    eventos: [
      { id: Date.now(), tipo: "creado", actor: responsable?.nombre || "—", detalle: "Borrador creado.", created_at: ahora() },
    ],
  };
  state.loans.push(loan);
  return clone(loan);
}

export async function addLoanItem(loanId, { equipmentId, accesoriosSeleccionados, accesoriosOtros, cargadorCon } = {}) {
  checkGlobalInjection();
  checkInjection("EQUIPO_OCUPADO");
  const loan = findLoan(loanId);
  // Índice único parcial del servidor real (§3): un equipo no puede estar en
  // dos préstamos abiertos a la vez. El mock replica la invariante en memoria.
  if (equipoTieneAbiertoUnLoan(equipmentId, loanId)) throwFixtureError("EQUIPO_OCUPADO");

  const itemId = state.loans.reduce((max, l) => Math.max(max, 0, ...l.items.map((it) => it.id)), 0) + 1;
  const equipo = state.equipos.find((e) => e.id === equipmentId);
  const item = {
    id: itemId,
    equipment_id: equipmentId,
    equipo_nombre: equipo?.nombre ?? `Equipo ${equipmentId}`,
    accesorios_seleccionados: accesoriosSeleccionados ?? [],
    accesorios_otros: accesoriosOtros ?? null,
    cargador_con: cargadorCon ?? null,
    devuelto_at: null,
    no_devuelto: false,
    nota_devolucion: null,
    decision: null,
    nota_decision: null,
    media: { foto_entrega_frente: null, foto_entrega_atras: null, foto_dev_frente: null, foto_dev_atras: null },
  };
  loan.items.push(item);
  return clone(item);
}

export async function removeLoanItem(loanId, itemId) {
  checkGlobalInjection();
  const loan = findLoan(loanId);
  loan.items = loan.items.filter((it) => it.id !== itemId);
  return { ok: true };
}

export async function confirmLoan(loanId) {
  checkGlobalInjection();
  // 401 a mitad del wizard, paso 4 (confirmar con firmas ya puestas).
  checkInjection("SESION_EXPIRADA");
  const loan = findLoan(loanId);
  if (loan.estado !== "borrador") throwFixtureError("TRANSICION_INVALIDA");

  const faltaAlgo =
    loan.items.length === 0 ||
    loan.items.some((it) => !it.media.foto_entrega_frente || !it.media.foto_entrega_atras) ||
    !loan.firmas.firma_entrega ||
    !loan.firmas.firma_responsable;
  if (faltaAlgo) throwFixtureError("TRANSICION_INVALIDA");

  loan.estado = "prestado";
  loan.folio = `CE-${String(++state.folioCounter).padStart(4, "0")}`;
  loan.fecha_entrega = new Date().toISOString().slice(0, 10);
  loan.responsiva = { version: 1, url: `/api/loans/${loan.id}/responsiva.pdf` };
  loan.eventos.push({
    id: Date.now(),
    tipo: "confirmado",
    actor: loan.responsable?.nombre || "—",
    detalle: "Préstamo confirmado. Carta responsiva firmada por ambas partes.",
    created_at: ahora(),
  });
  return clone(loan);
}

export async function cancelLoan(loanId) {
  checkGlobalInjection();
  const loan = findLoan(loanId);
  if (loan.estado !== "borrador") throwFixtureError("TRANSICION_INVALIDA");
  loan.estado = "cancelado";
  return clone(loan);
}

// I8 lote 1.3: "el mock deja de mentir" — las llaves son snake_case
// (`loan_item_id`/`no_devuelto`/`nota_devolucion`), igual que
// `DevolucionItem` del servidor real, y `loan_item_id` es obligatorio: si
// falta, 422 con el mismo sobre de error del contrato ({detail}), no un
// `continue` silencioso. El mock viejo aceptaba `itemId` (camelCase) sin
// quejarse — coincidía con lo que el caller viejo mandaba, así que el par
// mock+caller funcionaba consistente entre sí. El bug real vivía
// exclusivamente en `real/loans.js` (serializaba ese mismo camelCase al
// JSON que el servidor real rechaza): los 48/48 nunca tocaron esa costura.
// Ahora que el caller manda snake_case, el mock valida la MISMA forma que
// exige el servidor, para que un futuro regreso a camelCase sí truene aquí.
export async function returnLoan(loanId, { decisionesPorItem = [] } = {}) {
  checkGlobalInjection();
  const loan = findLoan(loanId);
  if (loan.estado !== "prestado") throwFixtureError("TRANSICION_INVALIDA");

  for (const d of decisionesPorItem) {
    if (d.loan_item_id == null) {
      throw new ApiError("loan_item_id es obligatorio en cada item de la devolución.", {
        status: 422,
        detail: "loan_item_id es obligatorio en cada item de la devolución.",
      });
    }
    const item = loan.items.find((it) => it.id === d.loan_item_id);
    if (!item) throwNotFound(`El renglon ${d.loan_item_id} no pertenece a este préstamo.`);
    if (d.no_devuelto) {
      if (!d.nota_devolucion) throwFixtureError("TRANSICION_INVALIDA");
      item.no_devuelto = true;
      item.nota_devolucion = d.nota_devolucion;
    } else if (!item.media.foto_dev_frente || !item.media.foto_dev_atras) {
      throwFixtureError("TRANSICION_INVALIDA");
    }
    item.devuelto_at = ahora();
  }
  loan.estado = "pendiente_confirmacion";
  loan.fecha_regreso_real = new Date().toISOString().slice(0, 10);
  return clone(loan);
}

export async function authorizeDelivery(loanId) {
  checkGlobalInjection();
  const loan = findLoan(loanId);
  loan.entrega_autorizada = true;
  // I8 lote 2: `entrega_autorizada_por` es `Optional[PersonaRef]` en el
  // contrato real (objeto, no string) — igual que `entregado_por` de
  // `prestamo_demo.json`. Antes era un string plano y sobrevivió invisible
  // porque CE-0007 siempre lo trae null; el mismo id=4 que ya usa ese fixture.
  loan.entrega_autorizada_por = { user_id: 4, nombre: "Melisa Avendano" };
  loan.fecha_autorizacion_entrega = ahora();
  return clone(loan);
}

export async function confirmReturnDecision(loanId, decisiones = []) {
  checkGlobalInjection();
  const loan = findLoan(loanId);
  if (loan.estado !== "pendiente_confirmacion") throwFixtureError("TRANSICION_INVALIDA");

  // Nota obligatoria si la decisión no es "ok" (422) — el contrato no da un
  // código estable para este 422 puntual (solo lo tiene MEDIA_INVALIDA con
  // otro significado), así que no se inventa uno: se deja el detail
  // explícito y sin `codigo`, tal como haría un 422 de validación genérico.
  for (const d of decisiones) {
    if (d.decision !== "ok" && !d.nota) {
      throw new ApiError("La nota es obligatoria si la decisión no es 'ok'.", { status: 422, detail: "La nota es obligatoria si la decisión no es 'ok'." });
    }
  }
  if (!loan.entrega_autorizada) throwFixtureError("TRANSICION_INVALIDA");

  for (const d of decisiones) {
    const item = loan.items.find((it) => it.id === d.loan_item_id);
    if (!item) continue;
    item.decision = d.decision;
    item.nota_decision = d.nota || null;
    if (d.decision !== "ok") {
      const equipo = state.equipos.find((e) => e.id === item.equipment_id);
      if (equipo) equipo.estado_operativo = "revision";
    }
  }

  const todasOk = decisiones.every((d) => d.decision === "ok");
  loan.estado = todasOk ? "completado" : "incompleto";
  // Mismo hallazgo que `entrega_autorizada_por` arriba: `confirmada_por`
  // también es `PersonaRef`, no string.
  loan.confirmada_por = { user_id: 4, nombre: "Melisa Avendano" };
  loan.fecha_confirmacion = ahora();
  return clone(loan);
}

export async function closeIncident(loanId, nota) {
  checkGlobalInjection();
  if (!nota) throw new ApiError("La nota es obligatoria.", { status: 422, detail: "La nota es obligatoria." });
  const loan = findLoan(loanId);
  if (loan.estado !== "incompleto") throwFixtureError("TRANSICION_INVALIDA");

  for (const item of loan.items) {
    const equipo = state.equipos.find((e) => e.id === item.equipment_id);
    if (equipo && equipo.estado_operativo === "revision") equipo.estado_operativo = "activo";
  }
  loan.estado = "completado";
  loan.eventos.push({ id: Date.now(), tipo: "incidencia_cerrada", actor: "Melisa Avendano", detalle: nota, created_at: ahora() });
  return clone(loan);
}

function csvEscape(valor) {
  const texto = valor == null ? "" : String(valor);
  return /[",\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

const COLUMNAS_EXPORT = [
  ["folio", "Folio"],
  ["estado", "Estado"],
  ["responsable", "Responsable"],
  ["motivo", "Motivo"],
  ["fecha_entrega", "Fecha de entrega"],
  ["fecha_regreso_esperada", "Fecha de regreso esperada"],
  ["atrasado", "Atrasado"],
  ["dias_atraso", "Días de atraso"],
];

/** `equipos_prestamos:exportar` — mismo filtrado que `fetchLoans`, sin
 * paginar (el CSV completo). El mock no genera un archivo real en disco;
 * arma el mismo Blob `text/csv` que produciría el endpoint real, para que
 * el cliente (`real/loans.js` y esta función) compartan el mismo camino
 * de "fetch → blob → descarga". */
export async function fetchLoansExport({ estado, q, desde, hasta } = {}) {
  checkGlobalInjection();
  let items = state.loans;
  if (estado) items = items.filter((l) => l.estado === estado);
  if (q) {
    const needle = q.toLowerCase();
    items = items.filter(
      (l) =>
        l.folio?.toLowerCase().includes(needle) ||
        l.motivo?.toLowerCase().includes(needle) ||
        l.responsable?.nombre?.toLowerCase().includes(needle)
    );
  }
  if (desde) items = items.filter((l) => l.fecha_entrega && l.fecha_entrega >= desde);
  if (hasta) items = items.filter((l) => l.fecha_entrega && l.fecha_entrega <= hasta);

  const encabezado = COLUMNAS_EXPORT.map(([, etiqueta]) => csvEscape(etiqueta)).join(",");
  const filas = items.map((l) =>
    COLUMNAS_EXPORT.map(([campo]) => csvEscape(campo === "responsable" ? l.responsable?.nombre : l[campo])).join(",")
  );
  const csv = [encabezado, ...filas].join("\r\n");
  return new Blob([csv], { type: "text/csv" });
}

export function loanResponsivaUrl(loanId) {
  // El mock no genera un PDF real; solo respeta la forma de la URL del contrato.
  return `/api/loans/${loanId}/responsiva.pdf`;
}
