import { useState, useEffect, useCallback, useRef } from "react";
import { GlassPanel, KpiTile, InfoTooltip, ICONS, usePageTitle } from "@/design";
import DateRangeFilter from "./DateRangeFilter";
import MonthlySpendChart from "./charts/MonthlySpendChart";
import CreatorUsageChart from "./charts/CreatorUsageChart";
import BrandSpendApexChart from "./charts/BrandSpendApexChart";
import SpendTrendChart from "./charts/SpendTrendChart";
import GeneralExpensesChart from "./charts/GeneralExpensesChart";
import OperationalExpensesChart from "./charts/OperationalExpensesChart";
import OperationalByRubroChart from "./charts/OperationalByRubroChart";
import TicketsPerDayChart from "./charts/TicketsPerDayChart";
import TopExpensesCard from "./charts/TopExpensesCard";
import {
  fetchDashboardSummary,
  fetchMonthlySpend,
  fetchCreatorUsage,
  fetchBrandSpendBreakdown,
  fetchGeneralExpensesMonthly,
  fetchOperationalDashboard,
  fetchTicketsPerDay,
  fetchTopExpenses,
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

/** Cabecera compartida de cada panel de gráfica: título + ícono "i" (mismo
 * InfoTooltip de los KpiTile) que explica qué se muestra y cómo se calcula,
 * sin tener que adivinarlo mirando la gráfica sola. */
function ChartHeader({ title, unit, info }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-2">
        <h2
          className="font-display text-sm font-bold uppercase tracking-[0.08em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          {title}
        </h2>
        <InfoTooltip text={info} />
      </div>
      {unit && <span className="go-eyebrow">{unit}</span>}
    </div>
  );
}

/** Agrupa las gráficas por lo que muestran (creadores, actividad, gastos
 * generales/operativos) en vez de amontonarlas todas en una sola lista —
 * cada grupo trae su propio ícono + una línea de contexto. */
function DashboardSection({ icon, title, subtitle, children }) {
  return (
    <section className="space-y-6">
      <div className="flex items-center gap-3">
        <span
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-go"
          style={{ background: "var(--go-orange-tint)", color: "var(--go-orange)" }}
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
          </svg>
        </span>
        <div>
          <h2
            className="font-display text-base font-bold uppercase tracking-[0.06em]"
            style={{ color: "var(--go-text-primary)" }}
          >
            {title}
          </h2>
          {subtitle && (
            <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>
      <div className="space-y-8">{children}</div>
    </section>
  );
}

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
  const [topExpenses, setTopExpenses] = useState([]);
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
      const [s, m, c, b, ge, od, tpd, te] = await Promise.all([
        fetchDashboardSummary(start, end, opts),
        fetchMonthlySpend(start, end, opts),
        fetchCreatorUsage(start, end, opts),
        fetchBrandSpendBreakdown(start, end, opts),
        fetchGeneralExpensesMonthly(start, end, opts),
        fetchOperationalDashboard(start, end, opts),
        fetchTicketsPerDay(start, end, opts),
        fetchTopExpenses(start, end, opts),
      ]);
      setSummary(s);
      setMonthly(m);
      setCreatorUsage(c);
      setBrandSpend(b);
      setGeneralExpensesMonthly(ge);
      setOperationalDashboard(od);
      setTicketsPerDay(tpd);
      setTopExpenses(te);
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
              info="Suma del monto del ciclo vigente (semanal o mensual) de cada creador activo, ahora mismo — no cambia con el filtro de fechas de arriba. Si ves $0, revisa que los creadores tengan un monto de ciclo configurado en Administración → Creadores."
              accentColor={ACCENTS.orange}
              glass
            />
            <KpiTile
              label="Total Gastado"
              value={kpi ? kpi.total_spent : "—"}
              format={formatMXN}
              hint={`${spentPct.toFixed(1)}% ejecutado`}
              info="Lo ya aprobado dentro del ciclo vigente de cada creador activo — también fijo, sin importar el filtro de fechas. Sube al aprobar un ticket; los pendientes o rechazados nunca cuentan aquí."
              accentColor={ACCENTS.turquoise}
              glass
            />
            <KpiTile
              label="Total Disponible"
              value={kpi ? kpi.total_remaining : "—"}
              format={formatMXN}
              hint={`${remainingPct.toFixed(1)}% restante`}
              info="Presupuesto Total menos Total Gastado del ciclo vigente. Puede salir en negativo si se aprobó más de lo presupuestado — la app lo permite a propósito, no es un error."
              accentColor={ACCENTS.sky}
              glass
            />
            <KpiTile
              label="Marcas Activas"
              value={summary?.active_brands ?? "—"}
              hint="con gastos en el período"
              info="Marcas con al menos un ticket aprobado dentro del rango de fechas seleccionado arriba. Si acabas de cambiar el filtro a un período sin nada aprobado todavía, este número cae a 0."
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
              info="Suma de tickets aprobados cuya fecha de subida cae dentro del filtro de fechas de arriba — a diferencia de 'Total Gastado', este sí cambia con el filtro. En $0 casi siempre significa que no hay tickets aprobados en ese rango (revisa si hay pendientes por confirmar, se muestran aparte)."
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
              info="Cantidad de tickets aprobados en el período filtrado, con su monto promedio. Los pendientes de validación se muestran aparte y no entran en este conteo ni en el promedio."
              accentColor={ACCENTS.turquoise}
              glass
            />
            <KpiTile
              label="Creadores Activos"
              value={creatorUsage.filter((c) => c.spent > 0).length}
              hint="con gastos en el período"
              info="Creadores con al menos un ticket aprobado (monto mayor a $0) dentro del período filtrado — distinto de 'Marcas Activas', que cuenta marcas, no creadores."
              accentColor={ACCENTS.sky}
              glass
            />
            <KpiTile
              label="Gastos Generales"
              value={generalExpensesTotal}
              format={formatMXN}
              hint={`${generalExpensesCount} ${generalExpensesCount === 1 ? "gasto" : "gastos"} en el periodo`}
              info="Gastos generales (ligados a una marca, sin ciclo ni validación) registrados dentro del período filtrado. No incluye Gastos Operativos ni afecta el presupuesto de los creadores."
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
              info="Gastos operativos (clasificados por rubro) registrados dentro del período filtrado, según su fecha de gasto manual — independientes de creadores y marcas."
              accentColor={ACCENTS.turquoise}
              glass
            />
          </div>

          {/* ── Mayores Gastos Individuales: siempre hasta arriba, es un dato
              que el departamento revisa primero, antes de meterse a cada
              sección agrupada de abajo. ─────────────────────────────────── */}
          <TopExpensesCard data={topExpenses} />

          {/* ── Sección: Presupuesto de Creadores ───────────────────────── */}
          <DashboardSection
            icon={ICONS.personas}
            title="Presupuesto de Creadores"
            subtitle="Ciclos, tickets y marcas de los creadores de contenido"
          >
            <GlassPanel as="section" className="p-4 sm:p-6">
              <ChartHeader
                title="Transacciones por Mes"
                unit="MXN"
                info="Gasto aprobado por mes (oficial, cuenta contra el ciclo) con el pendiente por confirmar superpuesto en ámbar — el pendiente nunca se suma al total aprobado."
              />
              <MonthlySpendChart data={monthly} />
            </GlassPanel>

            <div className="grid gap-8 lg:grid-cols-2">
              <GlassPanel as="section" className="p-4 sm:p-6">
                <ChartHeader
                  title="Gastos por Marca"
                  unit="MXN"
                  info="Cómo se reparte el gasto aprobado del período entre las marcas activas — cada rebanada es el total de esa marca sobre el total del pie."
                />
                <BrandSpendApexChart data={brandSpend} />
              </GlassPanel>

              <GlassPanel as="section" className="p-4 sm:p-6">
                <ChartHeader
                  title="Uso de Presupuesto por Creador"
                  unit="% usado"
                  info="Porcentaje del ciclo vigente que cada creador ya usó (aprobado), con lo pendiente por confirmar superpuesto — el color pasa a ámbar/rojo según qué tan cerca está del límite del ciclo."
                />
                <CreatorUsageChart data={creatorUsage} />
              </GlassPanel>
            </div>

            <GlassPanel as="section" className="p-4 sm:p-6">
              <ChartHeader
                title="Tendencia de Gasto Acumulado"
                unit="MXN"
                info="Suma acumulada del gasto aprobado, mes a mes, dentro del período filtrado — por definición nunca baja, solo sube o se mantiene."
              />
              <SpendTrendChart data={monthly} />
            </GlassPanel>
          </DashboardSection>

          {/* ── Sección: Actividad ──────────────────────────────────────── */}
          <DashboardSection
            icon={ICONS.actividad}
            title="Actividad"
            subtitle="Qué tan seguido se sube evidencia de gasto, sin importar si ya se validó"
          >
            <GlassPanel as="section" className="p-4 sm:p-6">
              <ChartHeader
                title="Tickets Subidos por Día"
                unit="Tickets"
                info="Cuántos tickets se subieron cada día del período, en cualquier estado (pendiente, aprobado o rechazado) — mide actividad, no gasto aprobado."
              />
              <TicketsPerDayChart data={ticketsPerDay} />
            </GlassPanel>
          </DashboardSection>

          {/* ── Sección: Gastos Generales y Operativos ──────────────────── */}
          <DashboardSection
            icon={ICONS.recibo}
            title="Gastos Generales y Operativos"
            subtitle="Gastos fuera del ciclo de creadores: ligados a una marca o clasificados por rubro"
          >
            <GlassPanel as="section" className="p-4 sm:p-6">
              <ChartHeader
                title="Gastos Generales por Mes"
                unit="MXN"
                info="Gastos generales (ligados a una marca, sin ciclo ni validación) agrupados por el mes en que se subieron."
              />
              <GeneralExpensesChart data={generalExpensesMonthly} />
            </GlassPanel>

            <div className="grid gap-8 lg:grid-cols-2">
              <GlassPanel as="section" className="p-4 sm:p-6">
                <ChartHeader
                  title="Gastos Operativos por Mes"
                  unit="MXN"
                  info="Gastos operativos (clasificados por rubro) agrupados por su fecha de gasto manual, no por fecha de subida."
                />
                <OperationalExpensesChart data={operationalDashboard?.mensual} />
              </GlassPanel>

              <GlassPanel as="section" className="p-4 sm:p-6">
                <ChartHeader
                  title="Gastos Operativos por Rubro"
                  unit="MXN"
                  info="Cómo se reparte el gasto operativo del período entre los rubros — el tamaño de cada bloque es proporcional a su monto."
                />
                <OperationalByRubroChart data={operationalDashboard?.por_rubro} />
              </GlassPanel>
            </div>
          </DashboardSection>
        </>
      )}
    </div>
  );
}
