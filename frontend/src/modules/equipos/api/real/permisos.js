/**
 * El catálogo de permisos (permisos_catalogo.json) es un documento de
 * contrato estático, no un endpoint — no existe un "GET catálogo" real.
 * En modo real no hay nada que pedir aquí; el modo diagnóstico de I5 usa
 * la copia local del contrato directamente. Este archivo existe para que
 * el import sea simétrico con mock/permisos.js (mismo nombre de función
 * en ambos lados, sin que el consumidor sepa cuál transporte tiene detrás).
 */
export function fetchPermisosCatalogo() {
  return Promise.resolve(null);
}

export function fetchAuthMeMock() {
  return Promise.resolve(null);
}
