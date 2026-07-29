import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, GO_CHART_COLORS } from "./apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "../../hooks/useMobile";

function usageColor(pct) {
  if (pct >= 90) return "#E53E3E"; // go-error
  if (pct >= 60) return "#F59E0B"; // go-warning
  return "#00A36E"; // go-success
}

export default function CreatorUsageChart({ data, forceTheme }) {
  const { theme: ctxTheme } = useTheme();
  const theme = forceTheme || ctxTheme;
  const isMobile = useMobile();
  const options = useMemo(() => {
    const items = (data || []).filter((d) => d.spent > 0);
    return createApexOptions({
      chart: { type: "bar" },
      plotOptions: {
        bar: {
          horizontal: true,
          borderRadius: 4,
          barHeight: "60%",
        },
      },
      xaxis: {
        categories: items.map((d) => d.name),
        title: { text: "% del presupuesto utilizado", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { formatter: (v) => `${v}%` },
        max: 100,
      },
      yaxis: {
        labels: { style: { fontWeight: 600, fontSize: "12px" } },
      },
      dataLabels: {
        enabled: true,
        formatter: (v) => `${v}%`,
        style: { fontSize: "11px", fontWeight: 600 },
      },
      tooltip: {
        y: {
          formatter: (v, { dataPointIndex }) => {
            const item = items[dataPointIndex];
            return `${v}% — $${item.spent.toLocaleString("es-MX", { minimumFractionDigits: 2 })} / $${item.initial_budget.toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;
          },
        },
      },
      legend: { show: false },
      grid: { xaxis: { lines: { show: true } }, yaxis: { lines: { show: false } } },
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    const items = (data || []).filter((d) => d.spent > 0);
    if (items.length === 0) return [];
    return [
      {
        name: "% Usado",
        data: items.map((d) => {
          // Use percentage from backend but also compute global for color
          const globalPct = d.initial_budget > 0
            ? parseFloat(((d.spent / d.initial_budget) * 100).toFixed(1))
            : 0;
          return {
            x: d.name,
            y: parseFloat(d.percentage.toFixed(1)),
            fillColor: usageColor(globalPct),
          };
        }),
      },
    ];
  }, [data]);

  if (!data || data.length === 0 || series.length === 0 || series[0].data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin datos de uso de presupuesto.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />
  );
}
