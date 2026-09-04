import { useMemo, useState } from "react";

/**
 * Orden universal de 3 estados (predeterminado → asc → desc → predeterminado)
 * reutilizado en todas las tablas de la app. Extraído de la implementación
 * original de TransactionTable.jsx.
 *
 * `columns`: array de { key, type?: "string"|"number"|"date", getValue?(item) }.
 * `type` default "string" (localeCompare en español, insensible a acentos).
 * `getValue` es opcional — por default lee `item[key]` directo; úsalo cuando
 * el valor a comparar no vive plano en esa propiedad (ej. una etiqueta
 * traducida o un booleano convertido a texto).
 */
export function useSortable(items, columns) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState(null);

  const columnByKey = useMemo(
    () => Object.fromEntries(columns.map((c) => [c.key, c])),
    [columns]
  );

  const cycleSort = (key) => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSortKey(null);
      setSortDir(null);
    }
  };

  const sortedItems = useMemo(() => {
    if (!sortKey || !sortDir) return items;
    const column = columnByKey[sortKey];
    const getValue = column?.getValue || ((item) => item[sortKey]);
    const type = column?.type || "string";

    const sorted = [...items].sort((a, b) => {
      const va = getValue(a);
      const vb = getValue(b);
      let cmp;
      if (type === "number") {
        cmp = (va ?? 0) - (vb ?? 0);
      } else if (type === "date") {
        cmp = new Date(va || 0) - new Date(vb || 0);
      } else {
        cmp = String(va ?? "").localeCompare(String(vb ?? ""), "es", { sensitivity: "base" });
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [items, sortKey, sortDir, columnByKey]);

  return { sortedItems, sortKey, sortDir, cycleSort };
}
