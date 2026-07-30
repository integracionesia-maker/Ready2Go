import { useState } from "react";
import { GlassModal } from "@/design";
import { confirmReturnDecision } from "../api";

const OPCIONES_DECISION = [
  { value: "ok", label: "OK" },
  { value: "danado", label: "Dañado" },
  { value: "faltante", label: "Faltante" },
];

/** Una decision por equipo (ok | danado | faltante); nota obligatoria si
 * no es "ok" (422 del servidor si falta, replicado aquí como validación
 * de cliente para no hacer el viaje). Todas "ok" → completado; alguna
 * distinta → incompleto y esos equipos a revision (lo hace el servidor,
 * la UI no lo simula). */
export default function ConfirmarDevolucionModal({ loan, onClose, onSuccess }) {
  const [decisiones, setDecisiones] = useState(() =>
    Object.fromEntries(loan.items.map((it) => [it.id, { decision: "ok", nota: "" }]))
  );
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  function actualizar(itemId, patch) {
    setDecisiones((prev) => ({ ...prev, [itemId]: { ...prev[itemId], ...patch } }));
  }

  const faltaNota = loan.items.some((it) => decisiones[it.id].decision !== "ok" && !decisiones[it.id].nota.trim());

  async function handleSubmit() {
    setError(null);
    if (faltaNota) {
      setError("Falta la nota en uno o más equipos con decisión distinta de OK.");
      return;
    }
    setEnviando(true);
    try {
      await confirmReturnDecision(
        loan.id,
        loan.items.map((it) => ({
          loan_item_id: it.id,
          decision: decisiones[it.id].decision,
          nota: decisiones[it.id].decision !== "ok" ? decisiones[it.id].nota.trim() : null,
        }))
      );
      onSuccess();
    } catch (e) {
      setError(e.detail || e.message);
    } finally {
      setEnviando(false);
    }
  }

  if (!loan.entrega_autorizada) {
    // Regla dura del contrato: un préstamo con entrega_autorizada:false
    // NUNCA llega a completado (409 TRANSICION_INVALIDA) — se explica
    // ANTES de que la persona lo intente, no después de un error.
    return (
      <GlassModal open onClose={onClose} title={`Confirmar devolución — ${loan.folio}`}>
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{ background: "rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.3)", color: "var(--go-warning)" }}
        >
          Este préstamo todavía no tiene autorizada su entrega — no puede
          confirmarse hasta que alguien con permiso de autorización lo
          apruebe primero (sección "Autorizaciones de entrega" arriba).
        </div>
      </GlassModal>
    );
  }

  return (
    <GlassModal
      open
      onClose={enviando ? undefined : onClose}
      title={`Confirmar devolución — ${loan.folio}`}
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={enviando} className="btn-go-ghost">
            Cancelar
          </button>
          <button type="button" onClick={handleSubmit} disabled={enviando} className="btn-go flex items-center gap-1.5">
            <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            {enviando ? "Guardando..." : "Confirmar"}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <ul className="space-y-4" data-testid="decisiones-devolucion">
          {loan.items.map((it) => (
            <li key={it.id} className="border-b pb-3" style={{ borderColor: "var(--go-border)" }}>
              <p className="mb-2 font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                {it.equipo_nombre}
              </p>
              <select
                value={decisiones[it.id].decision}
                onChange={(e) => actualizar(it.id, { decision: e.target.value })}
                className="go-select mb-2"
              >
                {OPCIONES_DECISION.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              {decisiones[it.id].decision !== "ok" && (
                <textarea
                  value={decisiones[it.id].nota}
                  onChange={(e) => actualizar(it.id, { nota: e.target.value })}
                  placeholder="Nota obligatoria..."
                  rows={2}
                  className="go-input resize-none"
                  required
                />
              )}
            </li>
          ))}
        </ul>

        {error && (
          <div
            className="rounded-go border px-4 py-3 font-body text-sm"
            style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
          >
            {error}
          </div>
        )}
      </div>
    </GlassModal>
  );
}
