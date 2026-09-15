import { useState, useEffect, useCallback } from "react";
import { GlassPanel, InfoTooltip, formatMXN } from "@/design";
import { fetchMonthlyEstimates, updateMonthlyEstimate } from "@/api";

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const CATEGORIAS = [
  { key: "caja_grande", label: "Caja Grande", info: "Gastos generales (ligados a una marca) + gastos por rubro (Gastos Operativos)." },
  { key: "caja_chica", label: "Caja Chica", info: "Gasto de creadores: tickets aprobados de su ciclo de presupuesto." },
];

function addMonths(year, month, delta) {
  const total = year * 12 + (month - 1) + delta;
  return { year: Math.floor(total / 12), month: (total % 12) + 1 };
}

function barColor(pct) {
  if (pct > 100) return "var(--go-error)";
  if (pct >= 80) return "var(--go-warning)";
  return "var(--go-success)";
}

/** Un bloque = una categoría (Caja Grande o Caja Chica) para el mes
 * seleccionado. Cada una tiene su propia meta/gasto/barra — nunca se
 * combinan en un solo número. */
function CategoriaBlock({ label, info, item, year, month, categoria, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const amount = item?.amount ?? null;
  const spent = item?.spent ?? 0;
  const isEditable = item?.is_editable ?? false;
  const isSuggested = item?.is_suggested ?? false;
  const pct = amount ? Math.round((spent / amount) * 100) : 0;

  // Salir de modo edición y resetear el input al cambiar de mes/categoría o
  // al recargar datos (ej. después de guardar) — nunca dejar un input a medio
  // llenar apuntando al mes equivocado.
  useEffect(() => {
    setEditing(false);
    setError(null);
    setInputValue(amount != null ? String(amount) : "");
  }, [year, month, categoria, amount]);

  const handleSave = async () => {
    const parsed = Number(inputValue);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("La estimación debe ser un número mayor a 0.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateMonthlyEstimate(year, month, categoria, parsed);
      await onSaved();
      setEditing(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="font-display text-xs font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          {label}
        </h3>
        <InfoTooltip text={info} />
      </div>

      {error && (
        <p className="font-body text-xs" style={{ color: "var(--go-error)" }}>
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Gastado:{" "}
          <span className="num font-display font-bold" style={{ color: "var(--go-text-primary)" }}>
            {formatMXN(spent)}
          </span>
        </span>
        <span className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Meta:{" "}
          <span className="num font-display font-bold" style={{ color: "var(--go-text-primary)" }}>
            {amount != null ? formatMXN(amount) : "sin definir"}
          </span>
          {isSuggested && (
            <span className="go-badge ml-2" style={{ background: "var(--go-orange-tint)", color: "var(--go-orange)" }}>
              sugerida
            </span>
          )}
        </span>
      </div>

      <div
        className="h-2.5 w-full overflow-hidden rounded-full"
        style={{ background: "var(--go-border)" }}
        aria-hidden="true"
      >
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${amount ? Math.min(pct, 100) : 0}%`,
            background: amount ? barColor(pct) : "var(--go-border)",
          }}
        />
      </div>

      {amount != null && (
        <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          {pct}% de cumplimiento
        </p>
      )}

      {isEditable && (
        <div className="pt-1">
          {editing ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Monto estimado"
                className="go-input w-40"
                disabled={saving}
              />
              <button type="button" onClick={handleSave} disabled={saving} className="btn-go">
                {saving ? "Guardando…" : "Guardar"}
              </button>
              <button type="button" onClick={() => setEditing(false)} disabled={saving} className="btn-go-ghost">
                Cancelar
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => setEditing(true)} className="btn-go-ghost">
              {isSuggested
                ? "Confirmar o cambiar estimación"
                : amount != null
                  ? "Editar estimación"
                  : "Definir estimación"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Meta fija de gasto de un mes, en DOS categorías independientes (Caja Grande
 * y Caja Chica — nunca combinadas en un solo total, I10 10/09/2026). Un mes
 * futuro siempre tiene una estimación real y funcional: si nadie fijó una
 * meta propia, se propone el promedio de los 3 meses anteriores (esa misma
 * categoría) y esa propuesta YA impulsa el % y el color de la barra — un
 * admin de marketing puede en cualquier momento (mientras el mes siga siendo
 * futuro) fijar un valor definitivo que la reemplaza. En cuanto el mes
 * arranca se congela (el backend rechaza el PUT con 409).
 * Navegación de mes propia, independiente del filtro de fechas del resto del
 * Dashboard.
 */
export default function MonthlyEstimateCard() {
  const hoy = new Date();
  const [year, setYear] = useState(hoy.getFullYear());
  const [month, setMonth] = useState(hoy.getMonth() + 1);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const load = useCallback(async (y, signal) => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await fetchMonthlyEstimates(y, { signal });
      setItems(data);
    } catch (e) {
      if (e.name === "AbortError") return;
      setLoadError(e.message);
    } finally {
      if (!signal || !signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(year, controller.signal);
    return () => controller.abort();
  }, [year, load]);

  const goToMonth = (delta) => {
    const next = addMonths(year, month, delta);
    setYear(next.year);
    setMonth(next.month);
  };

  const itemFor = (categoria) => items.find((i) => i.month === month && i.categoria === categoria) || null;

  return (
    <GlassPanel as="section" className="p-4 sm:p-6" data-testid="monthly-estimate-card">
      <div className="mb-6 flex items-center justify-between">
        <h2
          className="font-display text-sm font-bold uppercase tracking-[0.08em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Meta de Gasto Mensual
        </h2>
        <span className="go-eyebrow">MXN</span>
      </div>

      <div className="mb-6 flex items-center justify-center gap-3">
        <button type="button" onClick={() => goToMonth(-1)} className="btn-go-ghost px-3 py-1.5" aria-label="Mes anterior">
          ‹
        </button>
        <span
          className="font-display text-sm font-bold"
          style={{ color: "var(--go-text-primary)", minWidth: "10rem", textAlign: "center" }}
        >
          {MESES[month - 1]} {year}
        </span>
        <button type="button" onClick={() => goToMonth(1)} className="btn-go-ghost px-3 py-1.5" aria-label="Mes siguiente">
          ›
        </button>
      </div>

      {loadError && (
        <p className="mb-4 font-body text-sm" style={{ color: "var(--go-error)" }}>
          {loadError}
        </p>
      )}

      {loading ? (
        <p className="py-6 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Cargando…
        </p>
      ) : (
        <div className="grid gap-8 sm:grid-cols-2">
          {CATEGORIAS.map(({ key, label, info }) => (
            <CategoriaBlock
              key={key}
              label={label}
              info={info}
              item={itemFor(key)}
              year={year}
              month={month}
              categoria={key}
              onSaved={() => load(year)}
            />
          ))}
        </div>
      )}
    </GlassPanel>
  );
}
