/**
 * Identidad del build: versión, commit, fecha y entorno.
 *
 * Los tres primeros valores los inyecta `vite.config.js` por `process.env.VITE_*`,
 * que Vite copia a `import.meta.env` (`loadEnv`).
 *
 * **Por qué no `define`.** El plugin `vite:define` de Vite sale temprano cuando
 * el consumidor es el cliente y no es build:
 *
 *     if (this.environment.config.consumer === "client" && !isBuild) return;
 *
 * O sea que en el dev server **no sustituye nada**: un `__APP_VERSION__` llega
 * al navegador como identificador no declarado y revienta con ReferenceError al
 * renderizar. Solo funcionaba en el bundle construido, que es lo que sirven los
 * E2E (puerto 5175) — por eso el fallo estuvo enmascarado desde el 18/08/2026.
 * `import.meta.env` funciona igual en dev y en build, y una clave ausente es
 * `undefined` en vez de una excepción.
 */

export const APP_VERSION = import.meta.env.VITE_APP_VERSION || "dev";
export const COMMIT_HASH = import.meta.env.VITE_COMMIT_HASH || "sin-git";
export const BUILD_DATE = import.meta.env.VITE_BUILD_DATE || "—";

/** Entorno derivado del host: la app ya sabe dónde corre, no hace falta endpoint. */
export function entornoActual() {
  const host = typeof window === "undefined" ? "" : window.location.hostname;
  if (host === "gocreate.mx" || host === "www.gocreate.mx") return "producción";
  if (host === "localhost" || host === "127.0.0.1") return "local";
  return host || "desconocido";
}
