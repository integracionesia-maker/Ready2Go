import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "motion/react";
import GlassPanel from "./GlassPanel";

/**
 * `glass` es opt-in (default false, tarjeta plana con los tokens de
 * superficie): una fila típica de KPIs son 4-7 tiles, y el límite duro de
 * DESIGN_SYSTEM.md es 3-4 superficies de cristal simultáneas en pantalla. Un
 * consumidor puede pedir `glass` para un tile único destacado (hero), pero
 * el default no puede violar el límite solo por vivir en src/design/.
 */
export default function KpiTile({ label, value, format = (v) => v, icon, glass = false, className = "" }) {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(() => (reduceMotion ? value : 0));
  const prevValue = useRef(reduceMotion ? value : 0);

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(value);
      prevValue.current = value;
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
  }, [value, reduceMotion]);

  const body = (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-body text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--go-text-secondary)" }}>
          {label}
        </span>
        {icon && (
          <span className="flex h-8 w-8 items-center justify-center rounded-go" style={{ background: "var(--go-orange-tint)", color: "var(--go-orange)" }}>
            {icon}
          </span>
        )}
      </div>
      <span className="font-display text-2xl font-bold tabular-nums" style={{ color: "var(--go-text-primary)" }}>
        {format(Math.round(display))}
      </span>
    </div>
  );

  if (glass) {
    return (
      <GlassPanel className={`p-5 ${className}`} veilClassName="p-0">
        {body}
      </GlassPanel>
    );
  }

  return (
    <div className={`go-card ${className}`.trim()}>{body}</div>
  );
}
