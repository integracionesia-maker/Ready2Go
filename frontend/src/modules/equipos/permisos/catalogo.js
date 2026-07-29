import catalogoRaw from "../api/mock/fixtures/permisos_catalogo.json";

// Congelado (docs/contratos/permisos_catalogo.json): la lista de modulos y
// acciones validas sale de aqui, nunca de una constante escrita a mano. Es
// metadata estatica del contrato (no cambia entre mock y real), por eso se
// importa directo — no necesita pasar por el dispatcher mock/real de la API.
export const MODULOS = catalogoRaw.modulos; // { modulo: [acciones] }
export const PAQUETES = catalogoRaw.paquetes; // { nombre: { kind, permisos } }

export function accionExiste(modulo, accion) {
  const acciones = MODULOS[modulo];
  return Array.isArray(acciones) && acciones.includes(accion);
}
