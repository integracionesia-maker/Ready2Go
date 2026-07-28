const accentColors = {
  orange: { bg: "rgba(251,103,11,0.08)", border: "rgba(251,103,11,0.25)" },
  turquoise: { bg: "rgba(20,184,166,0.08)", border: "rgba(20,184,166,0.25)" },
  sky: { bg: "rgba(56,189,248,0.08)", border: "rgba(56,189,248,0.25)" },
  violet: { bg: "rgba(167,139,250,0.08)", border: "rgba(167,139,250,0.25)" },
};

export default function KpiCard({ title, value, subtitle, accent = "orange" }) {
  const c = accentColors[accent] || accentColors.orange;

  return (
    <div
      className="go-card flex flex-col gap-1 border-l-[3px]"
      style={{ borderLeftColor: c.border }}
    >
      <p className="go-eyebrow">{title}</p>
      <p
        className="font-display text-2xl sm:text-[28px] font-bold tracking-tight"
        style={{ color: "var(--go-text-primary)" }}
      >
        {value}
      </p>
      {subtitle && (
        <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}
