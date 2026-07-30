import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, formatChartCurrency, GO_CHART_COLORS } from "./apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

export default function BrandSpendApexChart({ data, forceTheme }) {
  const { theme: ctxTheme } = useTheme();
  const theme = forceTheme || ctxTheme;
  const isMobile = useMobile();
  const options = useMemo(() => {
    const items = (data || []).filter((d) => d.total_spent > 0);
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
        categories: items.map((d) => d.brand_name),
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
        y: { formatter: (v) => `$${v.toLocaleString("es-MX", { minimumFractionDigits: 2 })}` },
      },
      legend: { show: false },
      grid: { xaxis: { lines: { show: true } }, yaxis: { lines: { show: false } } },
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    const items = (data || []).filter((d) => d.total_spent > 0);
    return [
      {
        name: "Gasto",
        data: items.map((d) => d.total_spent),
      },
    ];
  }, [data]);

  if (!data || data.length === 0 || series[0].data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin datos de gastos por marca en este período.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />
  );
}
