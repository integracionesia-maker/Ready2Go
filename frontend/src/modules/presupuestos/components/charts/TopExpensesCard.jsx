import { GlassPanel, formatMXN } from "@/design";

// Fecha por split manual: `new Date("YYYY-MM-DD")` se interpreta como UTC y
// puede mostrar el día anterior en México. "2026-08-15" -> "15/08/2026".
function fmtFecha(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

/**
 * Top 3 gastos INDIVIDUALES del período (sin sumatorias): mezcla gastos
 * generales y por rubro que ya vienen ordenados por monto desc del backend
 * (`GET /api/dashboard/top-expenses`). Lista ranking, no gráfica de ejes: el
 * monto siempre va como texto y la mini barra es codificación secundaria de
 * magnitud (un solo tono, aria-hidden). La identidad de tipo vive en el badge
 * con texto (naranja General / turquesa Operativo), nunca solo en color.
 */
export default function TopExpensesCard({ data = [] }) {
  const items = Array.isArray(data) ? data.slice(0, 3) : [];
  const max = items.length ? Math.max(...items.map((i) => i.monto)) : 0;

  return (
    <GlassPanel as="section" className="p-4 sm:p-6" data-testid="top-expenses-card">
      <div className="flex items-center justify-between mb-6">
        <h2
          className="font-display text-sm font-bold uppercase tracking-[0.08em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Mayores Gastos Individuales
        </h2>
        <span className="go-eyebrow">MXN</span>
      </div>

      {items.length === 0 ? (
        <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Sin datos de gastos individuales en este período.
        </p>
      ) : (
        <ul className="space-y-4">
          {items.map((item, i) => (
            <li key={`${item.tipo}-${item.id}`} data-testid="top-expense-row">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-baseline gap-2">
                    <span className="font-display text-lg font-bold" style={{ color: "var(--go-orange)" }}>
                      {i + 1}
                    </span>
                    <span
                      className="truncate font-body text-sm font-medium"
                      style={{ color: "var(--go-text-primary)" }}
                      title={item.descripcion}
                    >
                      {item.descripcion}
                    </span>
                  </div>
                  <div
                    className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs"
                    style={{ color: "var(--go-text-secondary)" }}
                  >
                    <span className="font-display font-semibold">{item.etiqueta}</span>
                    <span>{fmtFecha(item.fecha)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <span className="num font-display text-sm font-bold" style={{ color: "var(--go-text-primary)" }}>
                    {formatMXN(item.monto)}
                  </span>
                  {/* Distintivo visual: naranja GO para general, turquesa para
                      operativo — mismo tinte que la tabla de Gastos Generales. */}
                  <span
                    className="go-badge whitespace-nowrap"
                    style={
                      item.tipo === "general"
                        ? { background: "rgba(251,103,11,0.12)", color: "var(--go-orange)" }
                        : { background: "rgba(0,163,182,0.12)", color: "#00A3B6" }
                    }
                  >
                    {item.tipo === "general" ? "General" : "Operativo"}
                  </span>
                </div>
              </div>
              <div
                className="mt-2 h-1.5 w-full overflow-hidden rounded-full"
                style={{ background: "var(--go-border)" }}
                aria-hidden="true"
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${max > 0 ? Math.max((item.monto / max) * 100, 4) : 0}%`,
                    background: "var(--go-orange)",
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </GlassPanel>
  );
}
