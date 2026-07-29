/**
 * Barril público de la API de Equipos: el resto del módulo importa de
 * `@/modules/equipos/api`, nunca de `./mock/` o `./real/` directamente.
 *
 * Cada archivo por dominio (equipment.js, loans.js, media.js, empresas.js,
 * permisos.js) decide su propio transporte con `import()` dinámico:
 * `import.meta.env.VITE_EQUIPOS_MOCK === "1"` → mock, si no → HTTP real.
 * Es una constante conocida en build time (Vite la reemplaza literal), así
 * que en un build de producción sin la variable, Rollup elimina la rama del
 * mock por completo — no entra ni como chunk aparte. Verificado mirando
 * `dist/` de un build sin VITE_EQUIPOS_MOCK: cero referencia a fixtures/*.json
 * ni a mock/*.js.
 */
export * from "./equipment";
export * from "./loans";
export * from "./media";
export * from "./empresas";
export * from "./permisos";
