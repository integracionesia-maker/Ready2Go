import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, formatChartCurrency, GO_CHART_COLORS } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

export default function SpendTrendChart({ data, forceTheme }) {
  const { theme: ctxTheme } = useTheme();
  const theme = forceTheme || ctxTheme;
  const isMobile = useMobile();
  const options = useMemo(() => {
    return createApexOptions({
      chart: {
        type: "area",
        toolbar: { show: true, tools: { download: true, selection: false, zoom: false, zoomin: false, zoomout: false, pan: false, reset: false } },
      },
      stroke: {
        curve: "smooth",
        width: 2,
        colors: [GO_CHART_COLORS[0]],
      },
      fill: {
        type: "gradient",
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.35,
          opacityTo: 0.05,
          stops: [0, 100],
        },
      },
      xaxis: {
        type: "datetime",
        labels: {
          format: "dd MMM",
          style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", colors: "var(--go-text-secondary)" },
        },
        title: { text: "Fecha", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
      },
      yaxis: {
        title: { text: "Gasto acumulado (MXN)", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { formatter: formatChartCurrency },
      },
      tooltip: {
        x: { format: "dd MMM yyyy" },
        y: { formatter: (v) => `$${v.toLocaleString("es-MX", { minimumFractionDigits: 2 })}` },
      },
      dataLabels: { enabled: false },
      colors: [GO_CHART_COLORS[0]], // orange
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    if (!data || data.length === 0) return [];
    // Compute cumulative spend over time
    let cumulative = 0;
    const points = data.map((d) => {
      cumulative += d.total;
      // d.month is "YYYY-MM", convert to first day of that month for datetime axis
      const dt = new Date(d.month + "-01T00:00:00");
      return { x: dt.getTime(), y: parseFloat(cumulative.toFixed(2)) };
    });
    return [{ name: "Gasto acumulado", data: points }];
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin datos de tendencia en este período.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="area" height={isMobile ? 200 : 280} width="100%" />
  );
}
