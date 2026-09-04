import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "motion/react";
import GlassPanel from "./GlassPanel";
import InfoTooltip from "./InfoTooltip";

/**
 * `glass` es opt-in (default false, tarjeta plana con los tokens de
 * superficie): una fila típica de KPIs son 4-7 tiles, y el límite duro de
 * DESIGN_SYSTEM.md es 3-4 superficies de cristal simultáneas en pantalla. Un
 * consumidor puede pedir `glass` para un tile único destacado (hero), pero
 * el default no puede violar el límite solo por vivir en src/design/.
 *
 * `value` puede no ser numérico todavía (p.ej. "—" mientras el dato no ha
 * cargado, un caso real de Dashboard.jsx): en ese caso se pinta tal cual, sin
 * animar ni pasar por `format` (que asume número).
 */
export default function KpiTile({
  label,
  value,
  hint,
  info,
  format = (v) => v,
  icon,
  glass = false,
  accentColor,
  className = "",
}) {
  const reduceMotion = useReducedMotion();
  const isNumeric = typeof value === "number" && Number.isFinite(value);
  const [display, setDisplay] = useState(() => (isNumeric && !reduceMotion ? 0 : value));
  const prevValue = useRef(isNumeric ? value : 0);

  useEffect(() => {
    if (!isNumeric || reduceMotion) {
      setDisplay(value);
      prevValue.current = isNumeric ? value : 0;
      return undefined;
    }
    const from = prevValue.current;
    const controls = animate(from, value, {
      duration: 0.6,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
      onComplete: () => {
        prevValue.current = value;
      },
    });
    return () => controls.stop();
  }, [value, isNumeric, reduceMotion]);

  const body = (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-body text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--go-text-secondary)" }}>
          {label}
        </span>
        <span className="flex flex-shrink-0 items-center gap-2">
          <InfoTooltip text={info} />
          {icon && (
            <span className="flex h-8 w-8 items-center justify-center rounded-go" style={{ background: "var(--go-orange-tint)", color: "var(--go-orange)" }}>
              {icon}
            </span>
          )}
        </span>
      </div>
      <span className="font-display text-2xl font-bold tabular-nums" style={{ color: "var(--go-text-primary)" }}>
        {typeof display === "number" ? format(Math.round(display)) : display}
      </span>
      {hint && (
        <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          {hint}
        </span>
      )}
    </div>
  );

  // El acento vive en el borde del contenedor exterior (igual que KpiCard
  // original), no en el body: así no se agrega un padding extra que
  // desalinee el tile respecto de uno sin accentColor.
  const accentStyle = accentColor ? { borderLeftWidth: "3px", borderLeftColor: accentColor } : undefined;

  if (glass) {
    return (
      <GlassPanel className={`p-5 ${className}`} veilClassName="p-0" style={accentStyle}>
        {body}
      </GlassPanel>
    );
  }

  return (
    <div className={`go-card ${className}`.trim()} style={accentStyle}>
      {body}
    </div>
  );
}
