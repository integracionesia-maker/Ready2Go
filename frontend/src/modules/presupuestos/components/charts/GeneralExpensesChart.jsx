import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, formatChartCurrency, GO_CHART_COLORS } from "./apexTheme";
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

export default function GeneralExpensesChart({ data, forceTheme }) {
  const { theme: ctxTheme } = useTheme();
  const theme = forceTheme || ctxTheme;
  const isMobile = useMobile();
  const options = useMemo(() => {
    return createApexOptions({
      chart: {
        type: "bar",
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
          dataLabels: { position: "top" },
        },
      },
      dataLabels: {
        enabled: true,
        formatter: formatChartCurrency,
        offsetY: -20,
        style: { fontSize: "10px", colors: ["var(--go-text-secondary)"] },
      },
      tooltip: {
        y: {
          formatter: (v, opts) => {
            const amount = `$${v.toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;
            const count = (data || [])[opts?.dataPointIndex]?.count;
            if (count === undefined || count === null) return amount;
            const label = count === 1 ? "1 gasto" : `${count} gastos`;
            return `${amount} · ${label}`;
          },
        },
      },
      colors: [GO_CHART_COLORS[0]], // go-orange
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    return [
      {
        name: "Gasto",
        data: (data || []).map((d) => d.total),
      },
    ];
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin gastos generales en este periodo.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />
  );
}
