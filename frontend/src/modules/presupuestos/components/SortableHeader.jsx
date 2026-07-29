/** Ícono de orden de 3 estados: doble chevron tenue (predeterminado), o
 * chevron simple arriba/abajo coloreado naranja (asc/desc). Extraído de
 * TransactionTable.jsx para reutilizarse en cualquier tabla ordenable. */
export function SortIcon({ dir }) {
  if (dir === "asc") {
    return (
      <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
      </svg>
    );
  }
  if (dir === "desc") {
    return (
      <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    );
  }
  return (
    <svg className="h-3 w-3 opacity-40" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l4-4 4 4M8 15l4 4 4-4" />
    </svg>
  );
}

/**
 * Celda `<th>` clicable para una columna ordenable (usar junto a `useSortable`).
 * `columnKey` identifica la columna; `activeKey`/`dir` vienen del hook.
 */
const TH_ALIGN_CLASS = { right: "text-right", center: "text-center" };
const BTN_ALIGN_CLASS = { right: "justify-end", center: "justify-center" };

export function SortableHeaderCell({ label, columnKey, activeKey, dir, onSort, align }) {
  const active = activeKey === columnKey;
  return (
    <th className={TH_ALIGN_CLASS[align] || ""}>
      <button
        onClick={() => onSort(columnKey)}
        title={!active ? "Ordenar ascendente" : dir === "asc" ? "Ordenar descendente" : "Quitar orden"}
        className={`inline-flex items-center gap-1.5 font-display text-[11px] font-bold uppercase tracking-[0.10em] transition-colors ${
          BTN_ALIGN_CLASS[align] || ""
        }`}
        style={{ color: active ? "var(--go-orange)" : "inherit" }}
      >
        {label}
        <SortIcon dir={active ? dir : null} />
      </button>
    </th>
  );
}
