import { useRef, useState } from "react";

const CONDICION_BADGE = {
  bueno: "go-badge-success",
  atencion: "go-badge-warning",
};

const ESTADO_OPERATIVO_LABEL = {
  activo: "Activo",
  revision: "En revisión",
  baja: "Dado de baja",
};

// Se computa una sola vez por montaje del módulo: el tipo de dispositivo no
// cambia a media sesión. El tilt 3D NUNCA se monta (ni listeners ni estado)
// en táctil — no es solo ocultarlo con CSS.
const SOPORTA_HOVER_FINO =
  typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

function useTilt() {
  const ref = useRef(null);
  const [transform, setTransform] = useState("");

  if (!SOPORTA_HOVER_FINO) {
    return { ref, style: {}, onMouseMove: undefined, onMouseLeave: undefined };
  }

  function onMouseMove(e) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setTransform(`perspective(700px) rotateX(${(-py * 6).toFixed(2)}deg) rotateY(${(px * 6).toFixed(2)}deg)`);
  }

  function onMouseLeave() {
    setTransform("");
  }

  return { ref, style: { transform, transition: transform ? "none" : "transform 0.3s ease" }, onMouseMove, onMouseLeave };
}

export default function EquipmentCard({ equipo, onClick }) {
  const tilt = useTilt();

  const ocupadoPor = equipo.tenedor_actual?.nombre;

  return (
    <button
      type="button"
      ref={tilt.ref}
      onMouseMove={tilt.onMouseMove}
      onMouseLeave={tilt.onMouseLeave}
      onClick={() => onClick(equipo)}
      style={tilt.style}
      className="go-card w-full text-left"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="font-display text-sm font-bold leading-snug" style={{ color: "var(--go-text-primary)" }}>
          {equipo.nombre}
        </h3>
        {equipo.codigo && (
          <span className="shrink-0 font-mono text-xs" style={{ color: "var(--go-text-muted)" }}>
            {equipo.codigo}
          </span>
        )}
      </div>

      <p className="mb-3 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
        {equipo.categoria}
      </p>

      <div className="mb-3 flex flex-wrap gap-1.5">
        <span className={`go-badge ${CONDICION_BADGE[equipo.condicion] || "go-badge-neutral"}`}>
          {equipo.condicion || "sin auditar"}
        </span>
        <span className={`go-badge ${equipo.disponible ? "go-badge-success" : "go-badge-neutral"}`}>
          {equipo.disponible ? "Disponible" : "No disponible"}
        </span>
        {equipo.estado_operativo !== "activo" && (
          <span className="go-badge go-badge-warning">{ESTADO_OPERATIVO_LABEL[equipo.estado_operativo] || equipo.estado_operativo}</span>
        )}
        {equipo.atrasado && <span className="go-badge go-badge-error">Atrasado {equipo.dias_atraso}d</span>}
      </div>

      {ocupadoPor && (
        <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          Con: <span style={{ color: "var(--go-text-primary)" }}>{ocupadoPor}</span>
          {equipo.fecha_regreso_esperada && ` · regresa ${equipo.fecha_regreso_esperada}`}
        </p>
      )}
    </button>
  );
}
