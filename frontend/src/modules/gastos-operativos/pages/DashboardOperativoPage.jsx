import { useCallback, useEffect, useMemo, useState } from "react";
import Chart from "react-apexcharts";
import { GlassPanel, useMobile } from "@/design";
import { createApexOptions, formatChartCurrency, GO_CHART_COLORS } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import KpiCard from "@/modules/presupuestos/components/KpiCard";
import DateRangeFilter from "@/modules/presupuestos/components/DateRangeFilter";
import { operationalDashboard } from "../api";

const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function mesLabel(ym) {
  if (!ym) return "";
  const [y, m] = ym.split("-");
  return `${MESES[parseInt(m, 10) - 1]} ${y}`;
}

function formatCurrency(n) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", minimumFractionDigits: 2 }).format(n || 0);
}

function firstOfMonth() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth() - 5, 1); // últimos ~6 meses por defecto
}

export default function DashboardOperativoPage() {
  const { theme } = useTheme();
  const isMobile = useMobile();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [range, setRange] = useState({ start: firstOfMonth(), end: new Date() });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await operationalDashboard({ startDate: range.start, endDate: range.end }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => { load(); }, [load]);

  const porRubro = data?.por_rubro || [];
  const mensual = data?.mensual || [];

  const donutOptions = useMemo(
    () =>
      createApexOptions(
        {
          chart: { type: "donut" },
          labels: porRubro.map((r) => r.rubro_nombre),
          legend: { position: "bottom" },
          dataLabels: { enabled: true, formatter: (v) => `${v.toFixed(0)}%` },
          tooltip: { y: { formatter: (v) => formatCurrency(v) } },
          colors: GO_CHART_COLORS,
        },
        theme
      ),
    [porRubro, theme]
  );

  const barOptions = useMemo(
    () =>
      createApexOptions(
        {
          chart: { type: "bar", toolbar: { show: false } },
          xaxis: { categories: mensual.map((m) => mesLabel(m.month)) },
          yaxis: { labels: { formatter: formatChartCurrency } },
          plotOptions: { bar: { borderRadius: 4, columnWidth: "55%" } },
          dataLabels: { enabled: false },
          tooltip: { y: { formatter: (v) => formatCurrency(v) } },
          colors: [GO_CHART_COLORS[0]],
        },
        theme
      ),
    [mensual, theme]
  );

  return (
    <div className="space-y-6">
      <h1 className="font-display text-xl font-bold uppercase tracking-[0.04em]" style={{ color: "var(--go-text-primary)" }}>
        Dashboard — Gastos Operativos
      </h1>

      <GlassPanel className="p-4 sm:p-6">
        <DateRangeFilter startDate={range.start} endDate={range.end} onChange={(s, e) => setRange({ start: s, end: e })} />
      </GlassPanel>

      {error && (
        <div className="rounded-go border px-4 py-3 font-body text-sm" style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}>
          {error}
        </div>
      )}

      {loading ? (
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Cargando...</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard title="Total gastado" value={formatCurrency(data?.total)} accent="orange" />
            <KpiCard title="Número de gastos" value={data?.count ?? 0} accent="sky" />
            <KpiCard title="Rubros con gasto" value={porRubro.length} accent="violet" />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <GlassPanel className="p-4 sm:p-6">
              <p className="go-eyebrow mb-3">Distribución por rubro</p>
              {porRubro.length === 0 ? (
                <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Sin datos en el periodo.</p>
              ) : (
                <Chart key={theme} options={donutOptions} series={porRubro.map((r) => r.total)} type="donut" height={isMobile ? 260 : 320} width="100%" />
              )}
            </GlassPanel>

            <GlassPanel className="p-4 sm:p-6">
              <p className="go-eyebrow mb-3">Gasto por mes</p>
              {mensual.length === 0 ? (
                <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Sin datos en el periodo.</p>
              ) : (
                <Chart key={theme} options={barOptions} series={[{ name: "Gasto", data: mensual.map((m) => m.total) }]} type="bar" height={isMobile ? 240 : 320} width="100%" />
              )}
            </GlassPanel>
          </div>

          <GlassPanel className="space-y-3 p-4 sm:p-6">
            <p className="go-eyebrow">Detalle por rubro</p>
            {porRubro.length === 0 ? (
              <p className="py-6 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Sin datos.</p>
            ) : (
              <div className="go-table-scroll-wrapper">
                <div className="overflow-x-auto go-table-scroll rounded-go-lg border" style={{ borderColor: "var(--go-border)" }}>
                  <table className="go-table w-full">
                    <thead>
                      <tr><th>Rubro</th><th className="text-right"># Gastos</th><th className="text-right">Total</th></tr>
                    </thead>
                    <tbody>
                      {porRubro.map((r) => (
                        <tr key={r.rubro_id}>
                          <td style={{ color: "var(--go-text-primary)" }}>{r.rubro_nombre}</td>
                          <td className="num text-right">{r.count}</td>
                          <td className="num text-right font-semibold" style={{ color: "var(--go-warning)" }}>{formatCurrency(r.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </GlassPanel>
        </>
      )}
    </div>
  );
}
