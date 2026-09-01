import { useMemo } from "react";
import Chart from "react-apexcharts";
import { createApexOptions, GO_CHART_COLORS } from "@/design/apexTheme";
import { useTheme } from "@/context/ThemeContext";
import { useMobile } from "@/design";

const MAX_DIAS = 90;

function dayLabel(iso) {
  // "2026-08-31" -> "31/08"
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

/** Cuántos tickets se subieron cada día (`tickets-per-day`), barras por día
 * dentro del rango seleccionado en el dashboard. */
export default function TicketsPerDayChart({ data }) {
  const { theme } = useTheme();
  const isMobile = useMobile();

  const options = useMemo(() => {
    return createApexOptions({
      chart: {
        type: "bar",
        toolbar: { show: true, tools: { download: true, selection: false, zoom: false, zoomin: false, zoomout: false, pan: false, reset: false } },
      },
      xaxis: {
        categories: (data || []).map((d) => dayLabel(d.day)),
        title: { text: "Día", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { rotate: -45 },
      },
      yaxis: {
        title: { text: "Tickets subidos", style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", color: "var(--go-text-secondary)" } },
        labels: { formatter: (v) => Math.round(v) },
        forceNiceScale: true,
      },
      plotOptions: {
        bar: {
          borderRadius: 3,
          columnWidth: "70%",
        },
      },
      dataLabels: { enabled: false },
      tooltip: {
        y: {
          formatter: (v) => (v === 1 ? "1 ticket" : `${v} tickets`),
        },
      },
      colors: [GO_CHART_COLORS[2]], // sky — tercer acento, distinto de gastos generales/operativos
    }, theme);
  }, [data, theme]);

  const series = useMemo(() => {
    return [
      {
        name: "Tickets",
        data: (data || []).map((d) => d.count),
      },
    ];
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Sin tickets subidos en este periodo.
      </p>
    );
  }

  if (data.length > MAX_DIAS) {
    return (
      <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        El periodo seleccionado tiene {data.length} días con actividad — acota el filtro de fechas
        (por ejemplo a un mes) para ver el detalle diario legible.
      </p>
    );
  }

  return (
    <Chart key={theme} options={options} series={series} type="bar" height={isMobile ? 220 : 320} width="100%" />
  );
}
