/**
 * Transporte HTTP compartido contra el backend FastAPI.
 * Cookies de sesión (access/refresh) viajan en cada request; un 401 dispara
 * un intento de refresh automático y reintenta la petición original una vez.
 *
 * Aquí vive SOLO el transporte. Las funciones por dominio (auth, tickets,
 * creadores, gastos generales, dashboard) viven en `./index.js`, que es el
 * barril público del módulo: el resto de la app importa de `@/api`, nunca
 * de este archivo.
 */

export const BASE = "/api";
const NO_RETRY_PATHS = ["/auth/login", "/auth/refresh"];

/**
 * Distingue una falla de RED (el fetch nunca obtuvo respuesta — servidor
 * caído, sin internet) de un error HTTP normal (el servidor respondió con
 * un status de error, manejado por `request()` abajo con `body.detail`).
 * El Fetch API siempre lanza `TypeError` para fallas de red en todos los
 * navegadores (Chrome: "Failed to fetch", Firefox: "NetworkError...",
 * Safari: "Load failed") — se complementa con un chequeo de mensaje por si
 * algún entorno lanza otro tipo de error para el mismo caso.
 */
export function isNetworkError(e) {
  if (!e) return false;
  if (e instanceof TypeError) return true;
  return /failed to fetch|network ?error|internet_disconnected|load failed/i.test(String(e.message || ""));
}

let onAuthFailure = null;
export function setAuthFailureHandler(handler) {
  onAuthFailure = handler;
}

let refreshPromise = null;
export function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    }).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function fetchWithAuthRetry(path, options = {}, skipAuthRetry = false) {
  const res = await fetch(`${BASE}${path}`, { credentials: "include", ...options });

  if (res.status === 401 && !skipAuthRetry && !NO_RETRY_PATHS.some((p) => path.startsWith(p))) {
    const refreshRes = await refreshSession();
    if (refreshRes.ok) {
      return fetchWithAuthRetry(path, options, true);
    }
    if (onAuthFailure) onAuthFailure();
  }

  return res;
}

/**
 * Error HTTP con el sobre completo del contrato ({ detail, codigo }), no solo
 * el texto (R-I09). `message` sigue siendo `body.detail` exactamente como
 * antes de este cambio: las vistas de Presupuestos que hacen
 * `catch (e) { setError(e.message) }` no se enteran de nada. El código
 * (`SIN_PERMISO`, `PERMISOS_NO_DISPONIBLES`, `EQUIPO_OCUPADO`, ...) y el
 * status HTTP quedan disponibles para quien sí necesite distinguir un 403 de
 * un 503 — el módulo de Equipos, donde esa distinción es obligatoria: un 503
 * JAMÁS se interpreta como sesión inválida.
 */
export class ApiError extends Error {
  constructor(message, { status, codigo, detail } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.codigo = codigo;
    this.detail = detail;
  }
}

/** `esCodigo(e, "EQUIPO_OCUPADO")` — true solo si `e` es un ApiError con ese código. */
export function esCodigo(e, codigo) {
  return e instanceof ApiError && e.codigo === codigo;
}

/** Parsea el sobre de error de una respuesta no-ok y lanza ApiError. Compartido
 * por `request()` (JSON) y por los clientes multipart (uploadTicket,
 * createGeneralExpense, el futuro cliente de media de Equipos) para no
 * duplicar el parseo tres veces. */
export async function throwApiError(res) {
  const body = await res.json().catch(() => ({}));
  const message = body.detail || `Error ${res.status}: ${res.statusText}`;
  throw new ApiError(message, { status: res.status, codigo: body.codigo, detail: body.detail });
}

export async function request(path, options = {}) {
  const res = await fetchWithAuthRetry(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    await throwApiError(res);
  }

  return res.json();
}
