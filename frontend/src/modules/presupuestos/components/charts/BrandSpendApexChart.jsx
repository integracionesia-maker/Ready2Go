import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

/** Gasto por marca como pie chart: a diferencia del resto del dashboard (series
 * por mes/día, o "% usado" por creador), esto es una sola cifra por categoría
 * sobre un total — el caso clásico de pie, y variación a propósito para no
 * repetir barra horizontal en cada gráfico del dashboard. */
export default function BrandSpendApexChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();

  const items = useMemo(() => (data || []).filter((d) => d.total_spent > 0), [data]);

  const options = useMemo(() => {
    return createApexOptions({
      chart: { type: "pie" },
      labels: items.map((d) => d.brand_name),
      dataLabels: {
        enabled: true,
        formatter: (val) => `${val.toFixed(1)}%`,
        style: { fontSize: "11px", fontWeight: 600 },
      },
      tooltip: {
        y: { formatter: (v) => `$${v.toLocaleString("es-MX", { minimumFractionDigits: 2 })}` },
      },
      legend: { show: true, position: "bottom", horizontalAlign: "center" },
    }, theme);
  }, [items, theme]);

  const series = useMemo(() => items.map((d) => d.total_spent), [items]);

  if (!data || data.length === 0 || series.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin datos de gastos por marca en este período.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="pie" height={isMobile ? 280 : 340} width="100%" />
  );
}
