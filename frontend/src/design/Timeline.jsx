import EmptyState from "./EmptyState";

function formatEventDate(iso) {
  try {
    return new Date(iso).toLocaleString("es-MX", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * Bitácora genérica (§8.4: el único componente de esa lista que se queda en
 * src/design/ — SignaturePad/PhotoCapture/EquipmentCard bajan a
 * modules/equipos/). Consume el arreglo `eventos` tal como lo entrega
 * `GET /api/loans/{id}` (fixtures/prestamo_demo.json): { id, tipo, actor,
 * detalle, created_at }. Solo formatea para mostrar — nunca recalcula fechas
 * de negocio (atraso lo entrega siempre el servidor).
 */
export default function Timeline({ events = [], emptyMessage = "Sin eventos todavía." }) {
  if (events.length === 0) {
    return <EmptyState title={emptyMessage} />;
  }

  return (
    <ol className="relative flex flex-col gap-6 border-l pl-6" style={{ borderColor: "var(--go-border)" }}>
      {events.map((ev) => (
        <li key={ev.id} className="relative">
          <span
            className="absolute -left-[29px] top-1 h-3 w-3 rounded-full"
            style={{ background: "var(--go-orange)" }}
            aria-hidden="true"
          />
          <p className="font-display text-xs font-bold uppercase tracking-wide" style={{ color: "var(--go-text-primary)" }}>
            {ev.actor}
          </p>
          <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            {ev.detalle}
          </p>
          <time dateTime={ev.created_at} className="font-mono text-[11px]" style={{ color: "var(--go-text-muted)" }}>
            {formatEventDate(ev.created_at)}
          </time>
        </li>
      ))}
    </ol>
  );
}
