import catalogo from "./fixtures/permisos_catalogo.json";
import authMe from "./fixtures/auth_me.json";
import { checkGlobalInjection, checkInjection } from "./errorInjection";

/** El catálogo (permisos_catalogo.json) es el documento de contrato completo
 * — I5 lo usa para el modo diagnóstico que loguea claves de permiso
 * desconocidas. */
export async function fetchPermisosCatalogo() {
  checkInjection("PERMISOS_NO_DISPONIBLES");
  checkGlobalInjection();
  return catalogo;
}

/** `auth_me.json` de ejemplo (usuario colaborador_mkt) — sirve para probar
 * la UI de permisos sin depender de que el backend real de auth ya sirva
 * el campo `permisos`. */
export async function fetchAuthMeMock() {
  checkInjection("PERMISOS_NO_DISPONIBLES");
  checkGlobalInjection();
  return authMe;
}
