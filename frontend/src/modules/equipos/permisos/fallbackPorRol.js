import { PAQUETES } from "./catalogo";

/**
 * TEMPORAL — se borra cuando WP1 (RBAC aditivo del servidor) esté en pie y
 * `/auth/me` mande siempre `permisos` con contenido real. Anotado como
 * pendiente de retiro en docs/backlog_interfaz.md.
 *
 * `permisos` tiene default `{}` en el contrato (para no romper nada
 * existente). Mientras el motor real no aterriza, `{}` significaría "no
 * puede nada" y la app se vería vacía y rota — así que si y solo si
 * `permisos` viene ausente o vacío, se derivan los permisos del ROL BASE
 * (superadmin/admin/creador/colaborador_mkt) usando los `paquetes` del
 * catálogo, con `_PISO` aplicado siempre.
 *
 * Los paquetes ADITIVOS (APROBADOR_EQUIPO, CUSTODIO_EQUIPO, AUDITOR) NUNCA
 * se derivan aquí: si el servidor no manda `permisos`, esas acciones
 * simplemente no se pintan. Regalarlas por rol sería el hallazgo 7 del plan
 * (creep de privilegio) — un admin no se convierte en aprobador de equipo
 * por accidente solo porque el fallback existe.
 */

function mergePermisos(base, extra) {
  if (extra === "*") return "*";
  if (base === "*") return "*";
  const result = { ...base };
  for (const [modulo, acciones] of Object.entries(extra)) {
    const actuales = new Set(result[modulo] || []);
    acciones.forEach((a) => actuales.add(a));
    result[modulo] = Array.from(actuales);
  }
  return result;
}

export function fallbackPorRol(role) {
  let permisos = {};
  if (PAQUETES._PISO) permisos = mergePermisos(permisos, PAQUETES._PISO.permisos);

  const paquete = PAQUETES[role];
  if (paquete && paquete.kind === "base") {
    permisos = mergePermisos(permisos, paquete.permisos);
  }
  return permisos;
}
