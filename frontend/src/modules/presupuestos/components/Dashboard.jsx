import { useState, useEffect, useCallback, useRef } from "react";
import { GlassPanel, KpiTile, usePageTitle } from "@/design";
import DateRangeFilter from "./DateRangeFilter";
import MonthlySpendChart from "./charts/MonthlySpendChart";
import CreatorUsageChart from "./charts/CreatorUsageChart";
import BrandSpendApexChart from "./charts/BrandSpendApexChart";
import SpendTrendChart from "./charts/SpendTrendChart";
import GeneralExpensesChart from "./charts/GeneralExpensesChart";
import OperationalExpensesChart from "./charts/OperationalExpensesChart";
import OperationalByRubroChart from "./charts/OperationalByRubroChart";
import TicketsPerDayChart from "./charts/TicketsPerDayChart";
import {
  fetchDashboardSummary,
  fetchMonthlySpend,
  fetchCreatorUsage,
  fetchBrandSpendBreakdown,
  fetchGeneralExpensesMonthly,
  fetchOperationalDashboard,
  fetchTicketsPerDay,
  downloadDashboardReportPdf,
} from "@/api";

import { formatMXN } from "@/design";

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
  usePageTitle("Dashboard");
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [creatorUsage, setCreatorUsage] = useState([]);
  const [brandSpend, setBrandSpend] = useState([]);
  const [generalExpensesMonthly, setGeneralExpensesMonthly] = useState([]);
  const [operationalDashboard, setOperationalDashboard] = useState(null);
  const [ticketsPerDay, setTicketsPerDay] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pdfState, setPdfState] = useState("idle"); // idle | generating

  const loadDashboardData = useCallback(async (signal, isFirstLoad) => {
    setLoading(true);
    setError(null);
    try {
      const start = fmtDateParam(dateRange.start);
      const end = fmtDateParam(dateRange.end);
      // En la primera carga NO se pasa AbortSignal: si el token expiró, el
      // refresh cycle de client.js necesita completar sin que React Strict
      // Mode lo aborte a medio camino (lo que dejaría 401s visibles en
      // consola). Las cargas subsecuentes (debounced por cambio de fecha)
      // sí usan AbortController para cancelar requests obsoletas.
      const opts = isFirstLoad ? {} : { signal };
      const [s, m, c, b, ge, od, tpd] = await Promise.all([
        fetchDashboardSummary(start, end, opts),
        fetchMonthlySpend(start, end, opts),
        fetchCreatorUsage(start, end, opts),
        fetchBrandSpendBreakdown(start, end, opts),
        fetchGeneralExpensesMonthly(start, end, opts),
        fetchOperationalDashboard(start, end, opts),
        fetchTicketsPerDay(start, end, opts),
      ]);
      setSummary(s);
      setMonthly(m);
      setCreatorUsage(c);
      setBrandSpend(b);
      setGeneralExpensesMonthly(ge);
      setOperationalDashboard(od);
      setTicketsPerDay(tpd);
    } catch (e) {
      if (e.name === "AbortError") return; // reemplazada por un filtro mas reciente, no es un error real
      setError(e.message);
    } finally {
      if (!isFirstLoad && !signal.aborted) setLoading(false);
      else if (isFirstLoad) setLoading(false);
    }
  }, [dateRange]);

  // Cambiar de fecha con más de un clic/tecleo rápido no debe disparar un
  // Promise.all de 5 requests por cada cambio intermedio: se espera a que el
  // usuario se detenga (debounce) y cualquier carga que haya quedado a medias
  // se cancela con AbortController en vez de dejarla correr para nada.
  const isFirstLoadRef = useRef(true);

  useEffect(() => {
    const isFirstLoad = isFirstLoadRef.current;
    const controller = new AbortController();
    const delay = isFirstLoad ? 0 : 350;
    isFirstLoadRef.current = false;

    const timeoutId = window.setTimeout(() => {
      loadDashboardData(controller.signal, isFirstLoad);
    }, delay);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
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

  const operationalTotal = operationalDashboard?.total ?? 0;
  const operationalCount = operationalDashboard?.count ?? 0;

  const handleDownloadPdf = async () => {
    if (pdfState !== "idle") return;
    setError(null);
    setPdfState("generating");
    try {
      // El PDF se genera en el backend (reportlab, vectores nativos) — ya no
      // hay plantilla off-screen ni captura de pantalla que esperar.
      const start = fmtDateParam(dateRange.start);
      const end = fmtDateParam(dateRange.end);
      await downloadDashboardReportPdf(start, end);
    } catch (e) {
      setError(e.message || "No se pudo generar el PDF.");
    } finally {
      setPdfState("idle");
    }
  };

  return (
    <div className="space-y-8">
      {/* ── Date filter + descarga de reporte ────────────────────────── */}
      <GlassPanel as="div" className="flex flex-wrap items-end justify-between gap-4 p-4 sm:p-6">
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
          {pdfState === "generating" && "Generando PDF…"}
        </button>
      </GlassPanel>

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
              format={formatMXN}
              hint={`${kpi?.active_creators ?? 0} creadores activos`}
              accentColor={ACCENTS.orange}
              glass
            />
            <KpiTile
              label="Total Gastado"
              value={kpi ? kpi.total_spent : "—"}
              format={formatMXN}
              hint={`${spentPct.toFixed(1)}% ejecutado`}
              accentColor={ACCENTS.turquoise}
              glass
            />
            <KpiTile
              label="Total Disponible"
              value={kpi ? kpi.total_remaining : "—"}
              format={formatMXN}
              hint={`${remainingPct.toFixed(1)}% restante`}
              accentColor={ACCENTS.sky}
              glass
            />
            <KpiTile
              label="Marcas Activas"
              value={summary?.active_brands ?? "—"}
              hint="con gastos en el período"
              accentColor={ACCENTS.violet}
              glass
            />
          </div>

          {/* ── KPI row 2: Period-specific ────────────────────────────── */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiTile
              label="Gastado en el Período"
              value={summary ? summary.total_spent : "—"}
              format={formatMXN}
              hint={
                <>
                  según filtro de fechas
                  {summary?.pending_total > 0 && (
                    <>
                      {" · "}
                      <span style={{ color: "var(--go-warning)" }}>
                        +{formatMXN(summary.pending_total)} pendientes por confirmar
                      </span>
                    </>
                  )}
                </>
              }
              accentColor={ACCENTS.orange}
              glass
            />
            <KpiTile
              label="Tickets"
              value={summary?.ticket_count ?? "—"}
              hint={
                <>
                  Promedio {summary ? formatMXN(summary.avg_ticket) : "—"} por ticket
                  {summary?.pending_count > 0 && (
                    <>
                      {" · "}
                      <span style={{ color: "var(--go-warning)" }}>
                        {summary.pending_count === 1 ? "1 pendiente" : `${summary.pending_count} pendientes`} por confirmar
                      </span>
                    </>
                  )}
                </>
              }
              accentColor={ACCENTS.turquoise}
              glass
            />
            <KpiTile
              label="Creadores Activos"
              value={creatorUsage.filter((c) => c.spent > 0).length}
              hint="con gastos en el período"
              accentColor={ACCENTS.sky}
              glass
            />
            <KpiTile
              label="Gastos Generales"
              value={generalExpensesTotal}
              format={formatMXN}
              hint={`${generalExpensesCount} ${generalExpensesCount === 1 ? "gasto" : "gastos"} en el periodo`}
              accentColor={ACCENTS.orange}
              glass
            />
          </div>

          {/* ── KPI row 3: Gastos Operativos (fusionados con Gastos Generales) ── */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiTile
              label="Gastos Operativos"
              value={operationalTotal}
              format={formatMXN}
              hint={`${operationalCount} ${operationalCount === 1 ? "gasto" : "gastos"} en el periodo`}
              accentColor={ACCENTS.turquoise}
              glass
            />
          </div>

          {/* ── Row: Monthly bar chart ────────────────────────────────── */}
          <GlassPanel as="section" className="p-4 sm:p-6">
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
          </GlassPanel>

          {/* ── Row: Brand spend + Creator usage (side by side) ────────── */}
          <div className="grid gap-8 lg:grid-cols-2">
            <GlassPanel as="section" className="p-4 sm:p-6">
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
            </GlassPanel>

            <GlassPanel as="section" className="p-4 sm:p-6">
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
            </GlassPanel>
          </div>

          {/* ── Row: Cumulative spend trend ────────────────────────────── */}
          <GlassPanel as="section" className="p-4 sm:p-6">
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
          </GlassPanel>

          {/* ── Row: General expenses by month ─────────────────────────── */}
          <GlassPanel as="section" className="p-4 sm:p-6">
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
          </GlassPanel>

          {/* ── Row: Operational expenses by month + by rubro (side by side) ── */}
          <div className="grid gap-8 lg:grid-cols-2">
            <GlassPanel as="section" className="p-4 sm:p-6">
              <div className="flex items-center justify-between mb-6">
                <h2
                  className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                  style={{ color: "var(--go-text-primary)" }}
                >
                  Gastos Operativos por Mes
                </h2>
                <span className="go-eyebrow">MXN</span>
              </div>
              <OperationalExpensesChart data={operationalDashboard?.mensual} />
            </GlassPanel>

            <GlassPanel as="section" className="p-4 sm:p-6">
              <div className="flex items-center justify-between mb-6">
                <h2
                  className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                  style={{ color: "var(--go-text-primary)" }}
                >
                  Gastos Operativos por Rubro
                </h2>
                <span className="go-eyebrow">MXN</span>
              </div>
              <OperationalByRubroChart data={operationalDashboard?.por_rubro} />
            </GlassPanel>
          </div>

          {/* ── Row: Tickets subidos por día ────────────────────────────── */}
          <GlassPanel as="section" className="p-4 sm:p-6">
            <div className="flex items-center justify-between mb-6">
              <h2
                className="font-display text-sm font-bold uppercase tracking-[0.08em]"
                style={{ color: "var(--go-text-primary)" }}
              >
                Tickets Subidos por Día
              </h2>
              <span className="go-eyebrow">Tickets</span>
            </div>
            <TicketsPerDayChart data={ticketsPerDay} />
          </GlassPanel>
        </>
      )}
    </div>
  );
}
