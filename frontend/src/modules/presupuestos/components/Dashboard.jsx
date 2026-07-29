import { useState, useEffect, useCallback, useRef } from "react";
import { KpiTile } from "@/design";
import DateRangeFilter from "./DateRangeFilter";
import MonthlySpendChart from "./charts/MonthlySpendChart";
import CreatorUsageChart from "./charts/CreatorUsageChart";
import BrandSpendApexChart from "./charts/BrandSpendApexChart";
import SpendTrendChart from "./charts/SpendTrendChart";
import GeneralExpensesChart from "./charts/GeneralExpensesChart";
import DashboardPdfTemplate from "./PdfReport/DashboardPdfTemplate";
import { generateDashboardPdf } from "./PdfReport/generateDashboardPdf";
import { useAuth } from "@/context/AuthContext";
import {
  fetchDashboardSummary,
  fetchMonthlySpend,
  fetchCreatorUsage,
  fetchBrandSpendBreakdown,
  fetchGeneralExpensesMonthly,
} from "@/api";

function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount);
}

// Mismos 4 acentos que tenía KpiCard, ahora como color sólido (coincide con
// GO_CHART_COLORS de apexTheme.js) para el borde de KpiTile.
const ACCENTS = {
  orange: "#FB670B",
  turquoise: "#14B8A6",
  sky: "#38BDF8",
  violet: "#A78BFA",
};

function fmtDateParam(d) {
  if (!d) return undefined;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function Dashboard({ kpi, dateRange, onDateRangeChange }) {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [creatorUsage, setCreatorUsage] = useState([]);
  const [brandSpend, setBrandSpend] = useState([]);
  const [generalExpensesMonthly, setGeneralExpensesMonthly] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pdfState, setPdfState] = useState("idle"); // idle | rendering | generating
  const pdfSnapshotRef = useRef(null);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const start = fmtDateParam(dateRange.start);
      const end = fmtDateParam(dateRange.end);
      const [s, m, c, b, ge] = await Promise.all([
        fetchDashboardSummary(start, end),
        fetchMonthlySpend(start, end),
        fetchCreatorUsage(start, end),
        fetchBrandSpendBreakdown(start, end),
        fetchGeneralExpensesMonthly(start, end),
      ]);
      setSummary(s);
      setMonthly(m);
      setCreatorUsage(c);
      setBrandSpend(b);
      setGeneralExpensesMonthly(ge);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const spentPct =
    kpi && kpi.total_budget > 0
      ? (kpi.total_spent / kpi.total_budget) * 100
      : 0;
  const remainingPct =
    kpi && kpi.total_budget > 0
      ? (kpi.total_remaining / kpi.total_budget) * 100
      : 0;

  const generalExpensesTotal = generalExpensesMonthly.reduce(
    (acc, item) => acc + (item.total || 0),
    0
  );
  const generalExpensesCount = generalExpensesMonthly.reduce(
    (acc, item) => acc + (item.count || 0),
    0
  );

  const handleDownloadPdf = async () => {
    if (pdfState !== "idle") return;
    setError(null);
    pdfSnapshotRef.current = {
      kpi,
      summary,
      monthly,
      creatorUsage,
      brandSpend,
      generalExpensesMonthly,
      dateRange,
      generatedAt: new Date(),
      generatedByName: user?.full_name,
    };
    setPdfState("rendering");
    try {
      // La plantilla off-screen se monta recién ahora; se espera un tick de
      // pintado (ApexCharts renderiza su SVG de forma asíncrona) antes de
      // capturarla con html2canvas.
      await new Promise((resolve) => requestAnimationFrame(resolve));
      await new Promise((resolve) => requestAnimationFrame(resolve));
      await new Promise((resolve) => setTimeout(resolve, 500));

      setPdfState("generating");
      const start = fmtDateParam(dateRange.start) || "historico";
      const end = fmtDateParam(dateRange.end) || "actual";
      await generateDashboardPdf({ filename: `reporte-presupuesto_${start}_a_${end}.pdf` });
    } catch (e) {
      setError(e.message || "No se pudo generar el PDF.");
    } finally {
      setPdfState("idle");
    }
  };

  return (
    <div className="space-y-8">
      {/* ── Date filter + descarga de reporte ────────────────────────── */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <DateRangeFilter
          startDate={dateRange.start}
          endDate={dateRange.end}
          onChange={onDateRangeChange}
        />
        <button
          type="button"
          onClick={handleDownloadPdf}
          disabled={loading || pdfState !== "idle"}
          className="btn-go-ghost shrink-0"
        >
          {pdfState === "idle" && "Descargar PDF"}
          {pdfState === "rendering" && "Preparando reporte…"}
          {pdfState === "generating" && "Generando PDF…"}
        </button>
      </div>

      {/* ── Error ─────────────────────────────────────────────────────── */}
      {error && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{
            background: "rgba(229,62,62,0.08)",
            borderColor: "rgba(229,62,62,0.25)",
            color: "var(--go-error)",
          }}
        >
          {error}
        </div>
      )}

      {/* ── Loading ───────────────────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div
            className="h-8 w-8 animate-spin rounded-full border-[3px]"
            style={{
              borderColor: "var(--go-border)",
              borderTopColor: "var(--go-orange)",
            }}
          />
          <span
            className="ml-3 font-body text-sm"
            style={{ color: "var(--go-text-secondary)" }}
          >
            Cargando dashboard...
          </span>
        </div>
      )}

      {!loading && (
        <>
          {/* ── KPI row 1: Cumulative ─────────────────────────────────── */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiTile
              label="Presupuesto Total"
              value={kpi ? kpi.total_budget : "—"}
              format={formatCurrency}
              hint={`${kpi?.active_creators ?? 0} creadores activos`}
              accentColor={ACCENTS.orange}
            />
            {/* Las dos cifras "de un vistazo" llevan cristal — el resto se
                queda plano para no pasar de 3 superficies de cristal en
                pantalla junto con el nav de módulos del shell. */}
            <KpiTile
              label="Total Gastado"
              value={kpi ? kpi.total_spent : "—"}
              format={formatCurrency}
              hint={`${spentPct.toFixed(1)}% ejecutado`}
              accentColor={ACCENTS.turquoise}
              glass
            />
            <KpiTile
              label="Total Disponible"
              value={kpi ? kpi.total_remaining : "—"}
              format={formatCurrency}
              hint={`${remainingPct.toFixed(1)}% restante`}
              accentColor={ACCENTS.sky}
              glass
            />
            <KpiTile
              label="Marcas Activas"
              value={summary?.active_brands ?? "—"}
              hint="con gastos en el período"
              accentColor={ACCENTS.violet}
            />
          </div>

          {/* ── KPI row 2: Period-specific ────────────────────────────── */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiTile
              label="Gastado en el Período"
              value={summary ? summary.total_spent : "—"}
              format={formatCurrency}
              hint="según filtro de fechas"
              accentColor={ACCENTS.orange}
            />
            <KpiTile
              label="Tickets"
              value={summary?.ticket_count ?? "—"}
              hint={`Promedio ${summary ? formatCurrency(summary.avg_ticket) : "—"} por ticket`}
              accentColor={ACCENTS.turquoise}
            />
            <KpiTile
              label="Creadores Activos"
              value={creatorUsage.filter((c) => c.spent > 0).length}
              hint="con gastos en el período"
              accentColor={ACCENTS.sky}
            />
            <KpiTile
              label="Gastos Generales"
              value={generalExpensesTotal}
              format={formatCurrency}
              hint={`${generalExpensesCount} ${generalExpensesCount === 1 ? "gasto" : "gastos"} en el periodo`}
              accentColor={ACCENTS.orange}
            />
          </div>

          {/* ── Row: Monthly bar chart ────────────────────────────────── */}
          <section className="go-card">
            <div className="flex items-center justify-between mb-6">
              <h2
                className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                style={{ color: "var(--go-text-primary)" }}
              >
                Transacciones por Mes
              </h2>
              <span className="go-eyebrow">MXN</span>
            </div>
            <MonthlySpendChart data={monthly} />
          </section>

          {/* ── Row: Brand spend + Creator usage (side by side) ────────── */}
          <div className="grid gap-8 lg:grid-cols-2">
            <section className="go-card">
              <div className="flex items-center justify-between mb-6">
                <h2
                  className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                  style={{ color: "var(--go-text-primary)" }}
                >
                  Gastos por Marca
                </h2>
                <span className="go-eyebrow">MXN</span>
              </div>
              <BrandSpendApexChart data={brandSpend} />
            </section>

            <section className="go-card">
              <div className="flex items-center justify-between mb-6">
                <h2
                  className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                  style={{ color: "var(--go-text-primary)" }}
                >
                  Uso de Presupuesto por Creador
                </h2>
                <span className="go-eyebrow">% usado</span>
              </div>
              <CreatorUsageChart data={creatorUsage} />
            </section>
          </div>

          {/* ── Row: Cumulative spend trend ────────────────────────────── */}
          <section className="go-card">
            <div className="flex items-center justify-between mb-6">
              <h2
                className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                style={{ color: "var(--go-text-primary)" }}
              >
                Tendencia de Gasto Acumulado
              </h2>
              <span className="go-eyebrow">MXN</span>
            </div>
            <SpendTrendChart data={monthly} />
          </section>

          {/* ── Row: General expenses by month ─────────────────────────── */}
          <section className="go-card">
            <div className="flex items-center justify-between mb-6">
              <h2
                className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                style={{ color: "var(--go-text-primary)" }}
              >
                Gastos Generales por Mes
              </h2>
              <span className="go-eyebrow">MXN</span>
            </div>
            <GeneralExpensesChart data={generalExpensesMonthly} />
          </section>
        </>
      )}

      {/* ── Plantilla off-screen para el PDF (R8), solo montada al generar ── */}
      {pdfState !== "idle" && pdfSnapshotRef.current && (
        <DashboardPdfTemplate {...pdfSnapshotRef.current} />
      )}
    </div>
  );
}
