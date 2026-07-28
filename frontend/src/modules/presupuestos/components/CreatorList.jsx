function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount);
}

const MONTH_ABBR = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function parseISODate(iso) {
  // Evita corrimientos de zona horaria al parsear "YYYY-MM-DD" como fecha local.
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatDateRange(startIso, endIso) {
  const start = parseISODate(startIso);
  const end = parseISODate(endIso);
  const sameMonth = start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear();
  if (sameMonth) {
    return `${start.getDate()}-${end.getDate()} ${MONTH_ABBR[end.getMonth()]} ${end.getFullYear()}`;
  }
  return `${start.getDate()} ${MONTH_ABBR[start.getMonth()]} - ${end.getDate()} ${MONTH_ABBR[end.getMonth()]} ${end.getFullYear()}`;
}

function daysRemaining(endIso) {
  const end = parseISODate(endIso);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.ceil((end - today) / (1000 * 60 * 60 * 24));
  return Math.max(0, diff);
}

function BudgetBar({ spent, total }) {
  const pct = total > 0 ? (spent / total) * 100 : 0;
  const clamped = Math.min(Math.max(pct, 0), 100);
  const remainingPct = 100 - pct; // puede ser negativo si hay sobregiro

  let barColor = "#00A36E"; // go-success
  if (remainingPct < 10) barColor = "#E53E3E"; // go-error
  else if (remainingPct < 30) barColor = "#F59E0B"; // go-warning

  return (
    <div className="mt-3">
      <div className="mb-1.5 flex justify-between font-body text-[11px]">
        <span style={{ color: "var(--go-text-secondary)" }}>{pct.toFixed(0)}% consumido</span>
        <span
          className="font-semibold"
          style={{
            color:
              remainingPct < 0
                ? "var(--go-error)"
                : remainingPct < 30
                ? "var(--go-warning)"
                : "var(--go-success)",
          }}
        >
          {remainingPct < 0
            ? `${Math.abs(remainingPct).toFixed(0)}% de sobregiro`
            : `${remainingPct.toFixed(0)}% restante`}
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden"
        style={{
          background: "var(--go-surface-sunken)",
          borderRadius: "var(--go-radius)",
        }}
      >
        <div
          className="h-full transition-all duration-500"
          style={{
            width: `${clamped}%`,
            background: barColor,
            borderRadius: "var(--go-radius)",
          }}
        />
      </div>
    </div>
  );
}

export default function CreatorList({ creators }) {
  if (!creators || creators.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center py-24 font-body text-sm"
        style={{ color: "var(--go-text-secondary)" }}
      >
        <svg
          className="mb-4 h-12 w-12"
          fill="none"
          stroke="currentColor"
          strokeWidth={1}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <p>No hay creadores registrados.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2
          className="font-display text-lg font-bold uppercase tracking-[0.06em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Creadores{" "}
          <span style={{ color: "var(--go-orange)" }}>({creators.length})</span>
        </h2>
        <span className="go-eyebrow">Ciclo vigente por creador</span>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {creators.map((c) => (
          <div key={c.id} className="go-card">
            {/* ── Avatar + name ──────────────────────────────────── */}
            <div className="mb-4 flex items-center gap-3">
              <div
                className="flex h-10 w-10 items-center justify-center rounded-go font-display text-sm font-bold text-white"
                style={{ background: "var(--go-orange)" }}
              >
                {c.name
                  .split(" ")
                  .map((w) => w[0])
                  .join("")
                  .toUpperCase()
                  .slice(0, 2)}
              </div>
              <div className="min-w-0 flex-1">
                <h3
                  className="truncate font-display text-sm font-bold tracking-wide"
                  style={{ color: "var(--go-text-primary)" }}
                >
                  {c.name}
                </h3>
                <span
                  className={`go-badge mt-1 ${
                    c.is_active ? "go-badge-success" : "go-badge-error"
                  }`}
                >
                  {c.is_active ? "Activo" : "Inactivo"}
                </span>
              </div>
            </div>

            {/* ── Ciclo vigente ────────────────────────────────────── */}
            {c.cycle_start_date && c.cycle_end_date && (
              <div className="mb-3 flex items-center justify-between font-body text-[11px]" style={{ color: "var(--go-text-secondary)" }}>
                <span className="capitalize">
                  {c.cycle_period === "semanal" ? "Semanal" : "Mensual"} · {formatDateRange(c.cycle_start_date, c.cycle_end_date)}
                </span>
                <span>{daysRemaining(c.cycle_end_date)} días rest.</span>
              </div>
            )}

            {/* ── Budget figures ─────────────────────────────────── */}
            <div
              className="mb-3 grid grid-cols-2 gap-3 rounded-go p-3"
              style={{ background: "var(--go-surface)" }}
            >
              <div>
                <p className="font-body text-[11px] uppercase tracking-wider" style={{ color: "var(--go-text-secondary)" }}>
                  Presupuesto
                </p>
                <p
                  className="mt-0.5 font-mono text-sm font-semibold tracking-tight"
                  style={{ color: "var(--go-text-primary)" }}
                >
                  {formatCurrency(c.cycle_amount ?? 0)}
                </p>
              </div>
              <div>
                <p className="font-body text-[11px] uppercase tracking-wider" style={{ color: "var(--go-text-secondary)" }}>
                  Gastado
                </p>
                <p
                  className="mt-0.5 font-mono text-sm font-semibold tracking-tight"
                  style={{ color: "var(--go-warning)" }}
                >
                  {formatCurrency(c.cycle_spent ?? 0)}
                </p>
              </div>
              <div className="col-span-2 border-t pt-2" style={{ borderColor: "var(--go-border)" }}>
                <p className="font-body text-[11px] uppercase tracking-wider" style={{ color: "var(--go-text-secondary)" }}>
                  Restante
                </p>
                <p
                  className="mt-0.5 font-mono text-lg font-bold tracking-tight"
                  style={{
                    color: (c.cycle_remaining ?? 0) <= 0 ? "var(--go-error)" : "var(--go-success)",
                  }}
                >
                  {formatCurrency(c.cycle_remaining ?? 0)}
                </p>
              </div>
            </div>

            {/* ── Progress bar ───────────────────────────────────── */}
            <BudgetBar spent={c.cycle_spent ?? 0} total={c.cycle_amount ?? 0} />
          </div>
        ))}
      </div>
    </div>
  );
}
