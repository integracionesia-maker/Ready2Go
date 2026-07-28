/** Prioridad de marcas (R9): alta/media/baja, con orden y estilos consistentes
 * en toda la app (Administración, Transacciones, Dashboard). */

export const PRIORITY_LABELS = { alta: "Alta", media: "Media", baja: "Baja" };

export const PRIORITY_ORDER = { alta: 0, media: 1, baja: 2 };

export const PRIORITY_BADGE_CLASS = {
  alta: "go-badge-error",
  media: "go-badge-warning",
  baja: "go-badge-success",
};

export function sortByPriority(items, getPriority = (i) => i.priority) {
  return [...items].sort((a, b) => (PRIORITY_ORDER[getPriority(a)] ?? 3) - (PRIORITY_ORDER[getPriority(b)] ?? 3));
}
