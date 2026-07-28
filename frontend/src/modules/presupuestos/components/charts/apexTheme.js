/**
 * Shared ApexCharts theme configuration — Grupo Ortiz design system.
 * Every chart component imports this to stay visually consistent.
 * Theme-aware (R2): pasa el tema activo ('dark' | 'light') para que grid,
 * ejes, tooltip y leyenda se vean bien en ambos.
 */

export const GO_CHART_COLORS = [
  "#FB670B", // go-orange
  "#14B8A6", // turquoise
  "#38BDF8", // sky
  "#A78BFA", // violet
  "#00A36E", // go-success
  "#F59E0B", // go-warning
];

const THEME_TOKENS = {
  dark: {
    border: "#27272a",
    textSecondary: "#c5c5c5",
    textPrimary: "#ffffff",
    tooltip: "dark",
  },
  light: {
    border: "#dcdbd0",
    textSecondary: "#535353",
    textPrimary: "#262626",
    tooltip: "light",
  },
};

function tokensFor(theme) {
  return THEME_TOKENS[theme] || THEME_TOKENS.dark;
}

export function goApexGrid(theme) {
  const t = tokensFor(theme);
  return {
    borderColor: t.border,
    strokeDashArray: 3,
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
  };
}

/**
 * Returns a base ApexCharts options object pre-filled with GO theme values.
 * Pass per-chart overrides via the `overrides` parameter and the active
 * theme ('dark' | 'light', default 'dark') as the second argument.
 */
export function createApexOptions(overrides = {}, theme = "dark") {
  const t = tokensFor(theme);

  const options = {
    chart: {
      background: "transparent",
      fontFamily: "'Inter', sans-serif",
      foreColor: t.textSecondary,
      toolbar: { show: false },
      zoom: { enabled: false },
      ...overrides.chart,
    },
    theme: { mode: theme, palette: "palette1", monochrome: { enabled: false }, ...overrides.theme },
    colors: overrides.colors || GO_CHART_COLORS,
    grid: { ...goApexGrid(theme), ...overrides.grid },
    tooltip: {
      theme: t.tooltip,
      style: { fontSize: "12px", fontFamily: "'Inter', sans-serif" },
      ...overrides.tooltip,
    },
    legend: {
      fontSize: "12px",
      fontFamily: "'Inter', sans-serif",
      labels: { colors: t.textSecondary },
      markers: { width: 10, height: 10, radius: 3 },
      ...overrides.legend,
    },
    dataLabels: {
      style: { colors: [t.textPrimary], fontSize: "11px", fontFamily: "'Inter', sans-serif" },
      ...overrides.dataLabels,
    },
    xaxis: {
      labels: { style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", colors: t.textSecondary } },
      axisBorder: { color: t.border },
      axisTicks: { color: t.border },
      ...overrides.xaxis,
    },
    yaxis: {
      labels: { style: { fontSize: "11px", fontFamily: "'Inter', sans-serif", colors: t.textSecondary } },
      ...overrides.yaxis,
    },
  };

  // Only set these when actually overridden — ApexCharts merges its own
  // defaults (e.g. plotOptions.line, responsive: []) only when the key is
  // absent; an explicit `undefined` wipes out that default and crashes.
  if (overrides.stroke) options.stroke = overrides.stroke;
  if (overrides.fill) options.fill = overrides.fill;
  if (overrides.plotOptions) options.plotOptions = overrides.plotOptions;
  if (overrides.responsive) options.responsive = overrides.responsive;

  return options;
}

/** Format a number as MXN currency — short form for chart labels */
export function formatChartCurrency(value) {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}k`;
  }
  return `$${value.toFixed(0)}`;
}
