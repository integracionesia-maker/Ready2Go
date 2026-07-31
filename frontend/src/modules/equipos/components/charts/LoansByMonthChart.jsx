import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, GO_CHART_COLORS, useMobile } from "@/design";
import { useTheme } from "@/context/ThemeContext";

const MONTHS_ES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

function monthLabel(ym) {
  if (!ym) return "";
  const [y, m] = ym.split("-");
  return `${MONTHS_ES[parseInt(m, 10) - 1]} ${y}`;
}

/**
 * `data`: Array<{ month: "YYYY-MM", count: number }>, ya agregado por mes de
 * `fecha_entrega` (cuándo arrancó el préstamo, no cuándo se creó el borrador
 * — mismo campo que usa el filtro desde/hasta de Historial).
 */
export default function LoansByMonthChart({ data, forceTheme }) {
  const { theme: ctxTheme } = useTheme();
  const theme = forceTheme || ctxTheme;
  const isMobile = useMobile();

  // Conteos enteros pequeños con el tickAmount por defecto de ApexCharts
  // (~5-6 divisiones "nice scale") repiten el mismo entero varias veces en
  // el eje (ej. max=1 pinta "1,1,1,0,0,0"). Con máximos chicos, un tick por
  // entero se ve limpio; con máximos grandes, se limita a 5 divisiones.
  const maxCount = Math.max(1, ...(data || []).map((d) => d.count));
  const tickAmount = Math.min(maxCount, 5);

  const options = useMemo(() => {
    return createApexOptions(
      {
        chart: { type: "bar" },
        xaxis: {
          categories: (data || []).map((d) => monthLabel(d.month)),
          title: { text: "Mes", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        },
        yaxis: {
          title: { text: "Préstamos", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
          min: 0,
          max: maxCount,
          tickAmount,
          labels: { formatter: (v) => Math.round(v) },
        },
        plotOptions: {
          bar: { borderRadius: 4, columnWidth: "55%", dataLabels: { position: "top" } },
        },
        dataLabels: {
          enabled: true,
          offsetY: -20,
          style: { fontSize: "10px", colors: ["var(--go-text-secondary)"] },
        },
        tooltip: {
          y: { formatter: (v) => `${v} préstamo${v === 1 ? "" : "s"}` },
        },
        colors: [GO_CHART_COLORS[0]], // naranja GO
      },
      theme
    );
  }, [data, theme]);

  const series = useMemo(
    () => [{ name: "Préstamos", data: (data || []).map((d) => d.count) }],
    [data]
  );

  if (!data || data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin préstamos registrados en este período.
      </p>
    );
  }

  return <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />;
}
