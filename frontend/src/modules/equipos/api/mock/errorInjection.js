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

/** SIN_PERMISO truena en CUALQUIER acción — se llama al principio de cada
 * función del mock, sin excepción, antes de cualquier chequeo puntual. */
export function checkGlobalInjection() {
  if (getInjectedError() === "SIN_PERMISO") throwFixtureError("SIN_PERMISO");
}

/** Chequeo puntual: solo truena si el código inyectado es exactamente `codigo`. */
export function checkInjection(codigo) {
  if (getInjectedError() === codigo) throwFixtureError(codigo);
}
