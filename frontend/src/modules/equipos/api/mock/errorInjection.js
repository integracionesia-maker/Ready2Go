import { throwFixtureError } from "./mockErrors";

const STORAGE_KEY = "equipos-mock-error";

/** Conmutador en runtime (no hace falta reiniciar Vite, y un e2e lo puede
 * manejar): localStorage[STORAGE_KEY] = uno de los códigos de
 * fixtures/errores.json, o ausente para el camino feliz. */
export function getInjectedError() {
  try {
    return typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
  } catch {
    return null;
  }
}

export function setInjectedError(codigo) {
  try {
    if (codigo) localStorage.setItem(STORAGE_KEY, codigo);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* localStorage no disponible: no-op, el mock sigue funcionando sin inyección */
  }
}

const GLOBALES = ["SIN_PERMISO", "PERMISOS_NO_DISPONIBLES"];

/** SIN_PERMISO y PERMISOS_NO_DISPONIBLES truenan en CUALQUIER acción — se
 * llama al principio de cada función del mock, sin excepción, antes de
 * cualquier chequeo puntual. Ambos son fallos de la capa de autorización
 * (403: "no tienes el permiso" / 503: "no pudimos ni resolver que permisos
 * tienes"), no de un endpoint en particular — el contrato los describe como
 * fallos generales, no acotados a una sola ruta. */
export function checkGlobalInjection() {
  const codigo = getInjectedError();
  if (GLOBALES.includes(codigo)) throwFixtureError(codigo);
}

/** Chequeo puntual: solo truena si el código inyectado es exactamente `codigo`. */
export function checkInjection(codigo) {
  if (getInjectedError() === codigo) throwFixtureError(codigo);
}
