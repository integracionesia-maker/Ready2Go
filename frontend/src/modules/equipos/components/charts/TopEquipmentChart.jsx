import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, GO_CHART_COLORS, useMobile } from "@/design";
import { useTheme } from "@/context/ThemeContext";

/**
 * `data`: Array<{ name: string, count: number }>, ya recortado a los
 * top N equipos (mayor `count` primero) por quien llama.
 */
export default function TopEquipmentChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();

  // Mismo ajuste que LoansByMonthChart: sin esto, un máximo chico (ej. 1)
  // repite el mismo entero varias veces en la escala de valores (que en una
  // barra horizontal vive en `xaxis`, no en `yaxis`).
  const maxCount = Math.max(1, ...(data || []).map((d) => d.count));
  const tickAmount = Math.min(maxCount, 5);

  const options = useMemo(() => {
    return createApexOptions(
      {
        chart: { type: "bar" },
        xaxis: {
          categories: (data || []).map((d) => d.name),
          min: 0,
          max: maxCount,
          tickAmount,
          labels: { formatter: (v) => Math.round(v) },
        },
        plotOptions: {
          bar: { borderRadius: 4, horizontal: true, barHeight: "60%", dataLabels: { position: "top" } },
        },
        dataLabels: {
          enabled: true,
          offsetX: 20,
          style: { fontSize: "10px", colors: ["var(--go-text-secondary)"] },
        },
        tooltip: {
          y: { formatter: (v) => `${v} préstamo${v === 1 ? "" : "s"}` },
        },
        colors: [GO_CHART_COLORS[1]], // turquesa
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
        Sin datos suficientes para calcular el top de equipos.
      </p>
    );
  }

  const height = isMobile ? Math.max(160, data.length * 36) : Math.max(240, data.length * 40);

  return <Chart key={theme} options={options} series={series} type="bar" height={height} width="100%" />;
}
