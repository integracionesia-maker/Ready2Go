/**
 * Donut de distribución de estados — SVG/CSS puro, nunca ApexCharts: montar
 * Apex aquí arrastraría 942 kB al chunk del shell y el presupuesto de
 * rendimiento muere en I1 (regla dura, 01-I1-shell.md).
 */
export default function StatusDonut({ data = [], size = 120, thickness = 14, centerLabel, centerValue }) {
  const total = data.reduce((sum, d) => sum + d.value, 0) || 1;
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  let offsetAcc = 0;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" role="img" aria-label={centerLabel || "Distribución de estados"}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--go-surface-sunken)" strokeWidth={thickness} />
        {data.map((d, i) => {
          const fraction = total > 0 ? d.value / total : 0;
          const dash = fraction * circumference;
          const gap = circumference - dash;
          const strokeDashoffset = -offsetAcc;
          offsetAcc += dash;
          if (dash <= 0) return null;
          return (
            <circle
              key={d.label ?? i}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={d.color}
              strokeWidth={thickness}
              strokeDasharray={`${dash} ${gap}`}
              strokeDashoffset={strokeDashoffset}
            />
          );
        })}
      </svg>
      {(centerLabel || centerValue != null) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {centerValue != null && (
            <span className="font-display text-xl font-bold tabular-nums" style={{ color: "var(--go-text-primary)" }}>
              {centerValue}
            </span>
          )}
          {centerLabel && (
            <span className="font-body text-[10px] uppercase tracking-wide" style={{ color: "var(--go-text-secondary)" }}>
              {centerLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
