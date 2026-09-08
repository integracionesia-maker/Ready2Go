import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, formatChartCurrency } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

/** Gastos operativos por rubro (`operationalDashboard.por_rubro`) como
 * treemap: cada bloque es un rubro, su tamaño es proporcional al monto —
 * variación a propósito frente a la barra horizontal de "Gastos por Marca"
 * (ahora pie), para que el dashboard no repita la misma forma dos veces. */
export default function OperationalByRubroChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();

  const items = useMemo(() => (data || []).filter((d) => d.total > 0), [data]);

  const options = useMemo(() => {
    return createApexOptions({
      chart: { type: "treemap" },
      plotOptions: {
        treemap: { distributed: true, enableShades: false },
      },
      dataLabels: {
        enabled: true,
        formatter: (text, opts) => [text, formatChartCurrency(opts.value)],
        style: { fontSize: "12px", fontWeight: 600 },
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
    }, theme);
  }, [items, theme]);

  const series = useMemo(() => {
    if (items.length === 0) return [];
    return [{ data: items.map((d) => ({ x: d.rubro_nombre, y: d.total })) }];
  }, [items]);

  if (!data || data.length === 0 || series.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin datos de gastos operativos por rubro en este período.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="treemap" height={isMobile ? 220 : 320} width="100%" />
  );
}
