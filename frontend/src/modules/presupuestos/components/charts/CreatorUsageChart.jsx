import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, GO_CHART_COLORS } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

function usageColor(pct) {
  if (pct >= 90) return "#E53E3E"; // go-error
  if (pct >= 60) return "#F59E0B"; // go-warning
  return "#00A36E"; // go-success
}

/** Barras horizontales apiladas: "% Usado" (aprobado, cuenta contra el ciclo,
 * color por umbral rojo/ámbar/verde) + "% Pendiente" (lo que representarían
 * los tickets sin revisar sobre ese mismo presupuesto — informativo, NUNCA
 * entra al cálculo de `percentage`, R7). Un creador con todo pendiente y nada
 * aprobado aún (spent=0) igual aparece, para que se vea que sí subió algo. */
export default function CreatorUsageChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();
  const options = useMemo(() => {
    const items = (data || []).filter((d) => d.spent > 0 || d.pending > 0);
    return createApexOptions({
      chart: { type: "bar", stacked: true },
      plotOptions: {
        bar: {
          horizontal: true,
          borderRadius: 4,
          barHeight: "60%",
        },
      },
      xaxis: {
        categories: items.map((d) => d.name),
        title: { text: "% del presupuesto (aprobado + pendiente)", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { formatter: (v) => `${Math.round(v)}%` },
      },
      yaxis: {
        labels: { style: { fontWeight: 600, fontSize: "12px" } },
      },
      dataLabels: {
        enabled: true,
        formatter: (v) => (v > 0 ? `${v.toFixed(0)}%` : ""),
        style: { fontSize: "11px", fontWeight: 600 },
      },
      tooltip: {
        y: {
          formatter: (v, { seriesIndex, dataPointIndex }) => {
            const item = items[dataPointIndex];
            if (seriesIndex === 0) {
              return `${v.toFixed(1)}% usado — $${item.spent.toLocaleString("es-MX", { minimumFractionDigits: 2 })} / $${item.initial_budget.toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;
            }
            const n = item?.pending_count ?? 0;
            return `${v.toFixed(1)}% pendiente — $${item.pending.toLocaleString("es-MX", { minimumFractionDigits: 2 })} (${n === 1 ? "1 ticket" : `${n} tickets`} sin revisar)`;
          },
        },
      },
      legend: { show: true, position: "top", horizontalAlign: "right" },
      grid: { xaxis: { lines: { show: true } }, yaxis: { lines: { show: false } } },
      colors: [GO_CHART_COLORS[0], GO_CHART_COLORS[5]], // el 0 se pisa por punto (fillColor); el 1 es el ambar del segmento pendiente
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    const items = (data || []).filter((d) => d.spent > 0 || d.pending > 0);
    if (items.length === 0) return [];
    return [
      {
        name: "% Usado",
        data: items.map((d) => {
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
      {
        name: "% Pendiente por confirmar",
        data: items.map((d) => ({
          x: d.name,
          y: d.initial_budget > 0 ? parseFloat(((d.pending / d.initial_budget) * 100).toFixed(1)) : 0,
        })),
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
