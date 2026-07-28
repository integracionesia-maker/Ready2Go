import MonthlySpendChart from "../charts/MonthlySpendChart";
import CreatorUsageChart from "../charts/CreatorUsageChart";
import BrandSpendApexChart from "../charts/BrandSpendApexChart";
import SpendTrendChart from "../charts/SpendTrendChart";
import GeneralExpensesChart from "../charts/GeneralExpensesChart";
import KpiCard from "../KpiCard";
import { PRIORITY_LABELS, sortByPriority } from "../../utils/priority";
import isotipoNaranja from "@/assets/logos/isotipo-go-naranja.png";

function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount || 0);
}

function formatDateLong(d) {
  if (!d) return "—";
  return new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "long", year: "numeric" }).format(d);
}

function formatDateTimeLong(d) {
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

const SECTION_STYLE = {
  width: "900px",
  padding: "28px 32px",
  background: "#ffffff",
  boxSizing: "border-box",
};

/**
 * Plantilla de impresión del dashboard (R8), renderizada fuera de pantalla y
 * capturada sección por sección con html2canvas para armar el PDF. Fuerza
 * tema claro vía el atributo `data-theme="light"` del contenedor raíz —
 * ver la nota en index.css sobre por qué ese selector ya no exige `:root`.
 */
export default function DashboardPdfTemplate({
  kpi,
  summary,
  monthly,
  creatorUsage,
  brandSpend,
  dateRange,
  generatedAt,
  generatedByName,
  generalExpensesMonthly = [],
}) {
  const spentPct = kpi && kpi.total_budget > 0 ? (kpi.total_spent / kpi.total_budget) * 100 : 0;
  const remainingPct = kpi && kpi.total_budget > 0 ? (kpi.total_remaining / kpi.total_budget) * 100 : 0;
  const activeCreatorsInPeriod = creatorUsage.filter((c) => c.spent > 0).length;
  const brandRows = sortByPriority(brandSpend, (b) => b.priority).filter((b) => b.total_spent > 0);
  const creatorRows = [...creatorUsage].sort((a, b) => b.spent - a.spent);
  const generalExpensesTotal = generalExpensesMonthly.reduce((sum, m) => sum + (m.total || 0), 0);
  const generalExpensesCount = generalExpensesMonthly.reduce((sum, m) => sum + (m.count || 0), 0);

  const periodLabel =
    dateRange.start && dateRange.end
      ? `${formatDateLong(dateRange.start)} — ${formatDateLong(dateRange.end)}`
      : "Todo el historial";

  return (
    <div id="pdf-report-root" data-theme="light" style={{ position: "fixed", top: 0, left: "-10000px", zIndex: -1 }}>
      {/* ── Sección 1: encabezado + KPIs ────────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
          <img
            src={isotipoNaranja}
            alt="Grupo Ortiz"
            style={{ height: "36px", width: "auto", display: "block" }}
          />
          <div>
            <h1
              className="font-display"
              style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#262626", textTransform: "uppercase", letterSpacing: "0.06em" }}
            >
              Grupo Ortiz — Control de Presupuestos
            </h1>
            <p className="font-body" style={{ margin: 0, fontSize: "11px", color: "#535353" }}>
              Reporte de presupuesto de creadores de contenido
            </p>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "11px",
            color: "#535353",
            borderTop: "1px solid #dcdbd0",
            borderBottom: "1px solid #dcdbd0",
            padding: "8px 0",
            margin: "12px 0 20px",
          }}
        >
          <span>Período: {periodLabel}</span>
          <span>Generado: {formatDateTimeLong(generatedAt)}{generatedByName ? ` por ${generatedByName}` : ""}</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "12px" }}>
          <KpiCard title="Presupuesto Total" value={kpi ? formatCurrency(kpi.total_budget) : "—"} subtitle={`${kpi?.active_creators ?? 0} creadores activos`} accent="orange" />
          <KpiCard title="Total Gastado" value={kpi ? formatCurrency(kpi.total_spent) : "—"} subtitle={`${spentPct.toFixed(1)}% ejecutado`} accent="turquoise" />
          <KpiCard title="Total Disponible" value={kpi ? formatCurrency(kpi.total_remaining) : "—"} subtitle={`${remainingPct.toFixed(1)}% restante`} accent="sky" />
          <KpiCard title="Marcas Activas" value={summary?.active_brands ?? "—"} subtitle="con gastos en el período" accent="violet" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
          <KpiCard title="Gastado en el Período" value={summary ? formatCurrency(summary.total_spent) : "—"} subtitle="según filtro de fechas" accent="orange" />
          <KpiCard title="Tickets" value={summary?.ticket_count ?? "—"} subtitle={`Promedio ${summary ? formatCurrency(summary.avg_ticket) : "—"} por ticket`} accent="turquoise" />
          <KpiCard title="Creadores Activos" value={activeCreatorsInPeriod} subtitle="con gastos en el período" accent="sky" />
        </div>
      </div>

      {/* ── Sección 2: gráfica mensual ──────────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Transacciones por Mes
        </h2>
        <MonthlySpendChart data={monthly} forceTheme="light" />
      </div>

      {/* ── Sección 3: gasto por marca + uso por creador ─────────────────── */}
      <div className="pdf-section" style={{ ...SECTION_STYLE, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        <div>
          <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
            Gastos por Marca
          </h2>
          <BrandSpendApexChart data={brandSpend} forceTheme="light" />
        </div>
        <div>
          <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
            Uso de Presupuesto por Creador
          </h2>
          <CreatorUsageChart data={creatorUsage} forceTheme="light" />
        </div>
      </div>

      {/* ── Sección 4: tendencia acumulada ──────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Tendencia de Gasto Acumulado
        </h2>
        <SpendTrendChart data={monthly} forceTheme="light" />
      </div>

      {/* ── Sección 5: desglose por marca ────────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Desglose por Marca
        </h2>
        {brandRows.length === 0 ? (
          <p style={{ fontSize: "12px", color: "#535353" }}>Sin datos de gastos por marca en este período.</p>
        ) : (
          <table className="go-table">
            <thead>
              <tr>
                <th>Marca</th>
                <th>Prioridad</th>
                <th style={{ textAlign: "right" }}>Total gastado</th>
              </tr>
            </thead>
            <tbody>
              {brandRows.map((b) => (
                <tr key={b.brand_name}>
                  <td>{b.brand_name}</td>
                  <td>{PRIORITY_LABELS[b.priority] || b.priority}</td>
                  <td className="num" style={{ textAlign: "right" }}>{formatCurrency(b.total_spent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Sección 6: desglose por creador ──────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Desglose por Creador
        </h2>
        {creatorRows.length === 0 ? (
          <p style={{ fontSize: "12px", color: "#535353" }}>Sin datos de uso de presupuesto en este período.</p>
        ) : (
          <table className="go-table">
            <thead>
              <tr>
                <th>Creador</th>
                <th style={{ textAlign: "right" }}>Gastado</th>
                <th style={{ textAlign: "right" }}>Ciclo vigente</th>
                <th style={{ textAlign: "right" }}>% usado</th>
              </tr>
            </thead>
            <tbody>
              {creatorRows.map((c) => (
                <tr key={c.creator_id}>
                  <td>{c.name}</td>
                  <td className="num" style={{ textAlign: "right" }}>{formatCurrency(c.spent)}</td>
                  <td className="num" style={{ textAlign: "right" }}>{formatCurrency(c.initial_budget)}</td>
                  <td className="num" style={{ textAlign: "right" }}>{c.percentage.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Sección 7: gastos generales por mes ──────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Gastos Generales por Mes
        </h2>
        {generalExpensesMonthly.length === 0 ? (
          <p style={{ fontSize: "12px", color: "#535353" }}>Sin gastos generales en el periodo.</p>
        ) : (
          <>
            <GeneralExpensesChart data={generalExpensesMonthly} forceTheme="light" />
            <table className="go-table">
              <thead>
                <tr>
                  <th>Mes</th>
                  <th style={{ textAlign: "right" }}>Total</th>
                  <th style={{ textAlign: "right" }}>Gastos</th>
                </tr>
              </thead>
              <tbody>
                {generalExpensesMonthly.map((m) => (
                  <tr key={m.month}>
                    <td>{m.month}</td>
                    <td className="num" style={{ textAlign: "right" }}>{formatCurrency(m.total)}</td>
                    <td className="num" style={{ textAlign: "right" }}>{m.count}</td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 700 }}>
                  <td>Total</td>
                  <td className="num" style={{ textAlign: "right" }}>{formatCurrency(generalExpensesTotal)}</td>
                  <td className="num" style={{ textAlign: "right" }}>{generalExpensesCount}</td>
                </tr>
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
