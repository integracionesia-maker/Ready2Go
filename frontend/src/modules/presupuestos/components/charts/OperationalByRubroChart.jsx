import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, formatChartCurrency, GO_CHART_COLORS } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

/** Gastos operativos por rubro (`operationalDashboard.por_rubro`). Mismo
 * patrón que BrandSpendApexChart.jsx (barras horizontales, distributed). */
export default function OperationalByRubroChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();
  const options = useMemo(() => {
    const items = (data || []).filter((d) => d.total > 0);
    return createApexOptions({
      chart: { type: "bar" },
      plotOptions: {
        bar: {
          horizontal: true,
          borderRadius: 4,
          barHeight: "60%",
          distributed: true,
        },
      },
      xaxis: {
        categories: items.map((d) => d.rubro_nombre),
        title: { text: "MXN", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { formatter: formatChartCurrency },
      },
      yaxis: {
        labels: { style: { fontWeight: 600, fontSize: "12px" } },
      },
      dataLabels: {
        enabled: true,
        formatter: formatChartCurrency,
        style: { fontSize: "11px", fontWeight: 600 },
      },
      tooltip: {
        y: {
          formatter: (v, opts) => {
            const amount = `$${v.toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;
            const count = items[opts?.dataPointIndex]?.count;
            if (count === undefined || count === null) return amount;
            const label = count === 1 ? "1 gasto" : `${count} gastos`;
            return `${amount} · ${label}`;
          },
        },
      },
      legend: { show: false },
      grid: { xaxis: { lines: { show: true } }, yaxis: { lines: { show: false } } },
      colors: [GO_CHART_COLORS[1]],
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    const items = (data || []).filter((d) => d.total > 0);
    return [
      {
        name: "Gasto",
        data: items.map((d) => d.total),
      },
    ];
  }, [data]);

  if (!data || data.length === 0 || series[0].data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin datos de gastos operativos por rubro en este período.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />
  );
}
