import { useMemo } from "react";

function fmtDate(d) {
  if (!d) return "";
  return d.toISOString().split("T")[0];
}

function firstOfMonth(y, m) {
  return new Date(y, m, 1);
}

function today() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}

const PRESETS = [
  {
    label: "Este mes",
    getRange: () => {
      const t = today();
      return { start: firstOfMonth(t.getFullYear(), t.getMonth()), end: t };
    },
  },
  {
    label: "Mes pasado",
    getRange: () => {
      const t = today();
      const y = t.getMonth() === 0 ? t.getFullYear() - 1 : t.getFullYear();
      const m = t.getMonth() === 0 ? 11 : t.getMonth() - 1;
      return { start: firstOfMonth(y, m), end: new Date(y, m + 1, 0) };
    },
  },
  {
    label: "Últimos 3M",
    getRange: () => {
      const t = today();
      const d = new Date(t);
      d.setMonth(d.getMonth() - 3);
      return { start: d, end: t };
    },
  },
  {
    label: "Este año",
    getRange: () => {
      const t = today();
      return { start: new Date(t.getFullYear(), 0, 1), end: t };
    },
  },
  {
    label: "Todo",
    getRange: () => {
      return { start: null, end: null };
    },
  },
];

export default function DateRangeFilter({ startDate, endDate, onChange }) {
  const startStr = useMemo(() => (startDate ? fmtDate(startDate) : ""), [startDate]);
  const endStr = useMemo(() => (endDate ? fmtDate(endDate) : ""), [endDate]);

  const handlePreset = (preset) => {
    const { start, end } = preset.getRange();
    onChange(start, end);
  };

  return (
    <div className="flex flex-wrap items-end gap-3">
      {/* ── Desde ──────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col gap-1 sm:flex-none">
        <label
          className="font-display text-[11px] font-bold uppercase tracking-[0.14em]"
          style={{ color: "var(--go-orange)" }}
        >
          Desde
        </label>
        <input
          type="date"
          value={startStr}
          onChange={(e) => {
            const d = e.target.value ? new Date(e.target.value + "T00:00:00") : null;
            onChange(d, endDate);
          }}
          className="go-input w-full min-w-[140px] sm:w-[160px]"
        />
      </div>

      {/* ── Hasta ──────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col gap-1 sm:flex-none">
        <label
          className="font-display text-[11px] font-bold uppercase tracking-[0.14em]"
          style={{ color: "var(--go-orange)" }}
        >
          Hasta
        </label>
        <input
          type="date"
          value={endStr}
          onChange={(e) => {
            const d = e.target.value ? new Date(e.target.value + "T00:00:00") : null;
            onChange(startDate, d);
          }}
          className="go-input w-full min-w-[140px] sm:w-[160px]"
        />
      </div>

      {/* ── Presets ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-1.5 pb-[2px]">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => handlePreset(p)}
            className="rounded-full px-3 py-1 font-display text-[11px] font-semibold uppercase tracking-wider transition-all duration-200"
            style={{
              background: "var(--go-surface-sunken)",
              color: "var(--go-text-secondary)",
              border: "1px solid var(--go-border)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--go-orange)";
              e.currentTarget.style.color = "var(--go-orange)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--go-border)";
              e.currentTarget.style.color = "var(--go-text-secondary)";
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
