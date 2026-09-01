import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, formatChartCurrency, GO_CHART_COLORS } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

const MONTHS_ES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

function monthLabel(ym) {
  if (!ym) return "";
  const [y, m] = ym.split("-");
  return `${MONTHS_ES[parseInt(m, 10) - 1]} ${y}`;
}

/** Barras apiladas: "Aprobado" (gasto oficial, cuenta contra el ciclo) +
 * "Pendiente por confirmar" (lo que los creadores ya subieron pero
 * admin/superadmin no ha revisado — informativo, NUNCA suma al ciclo, R7).
 * Un mes con solo pendientes (ej. el mes en curso) igual aparece: el
 * backend une las llaves de ambos estados. */
export default function MonthlySpendChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();
  const options = useMemo(() => {
    return createApexOptions({
      chart: {
        type: "bar",
        stacked: true,
        toolbar: { show: true, tools: { download: true, selection: false, zoom: false, zoomin: false, zoomout: false, pan: false, reset: false } },
      },
      xaxis: {
        categories: (data || []).map((d) => monthLabel(d.month)),
        title: { text: "Mes", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
      },
      yaxis: {
        title: { text: "Monto (MXN)", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { formatter: formatChartCurrency },
      },
      plotOptions: {
        bar: {
          borderRadius: 4,
          columnWidth: "55%",
        },
      },
      dataLabels: {
        enabled: true,
        formatter: (v) => (v > 0 ? formatChartCurrency(v) : ""),
        style: { fontSize: "10px", colors: ["var(--go-text-secondary)"] },
      },
      tooltip: {
        y: {
          formatter: (v, { seriesIndex, dataPointIndex }) => {
            const amount = `$${v.toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;
            const item = (data || [])[dataPointIndex];
            if (seriesIndex === 0) {
              const n = item?.count ?? 0;
              return `${amount} · ${n === 1 ? "1 ticket aprobado" : `${n} tickets aprobados`}`;
            }
            const n = item?.pending_count ?? 0;
            return `${amount} · ${n === 1 ? "1 ticket pendiente" : `${n} tickets pendientes`}`;
          },
        },
      },
      legend: { show: true, position: "top", horizontalAlign: "right" },
      colors: [GO_CHART_COLORS[1], GO_CHART_COLORS[5]], // turquesa (aprobado) + ambar (pendiente)
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    return [
      { name: "Aprobado", data: (data || []).map((d) => d.total) },
      { name: "Pendiente por confirmar", data: (data || []).map((d) => d.pending_total || 0) },
    ];
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin transacciones en este período.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />
  );
}
