import { useState } from "react";
import { GlassModal } from "@/design";
import { closeIncident } from "../api";

/** Nota obligatoria (422 si falta); devuelve los equipos en "revision" a
 * "activo" — sin esto, "incompleto" es terminal y el equipo se queda
 * varado en revision para siempre (hallazgo 12). */
export default function CerrarIncidenciaModal({ loan, onClose, onSuccess }) {
  const [nota, setNota] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit() {
    if (!nota.trim()) {
      setError("La nota es obligatoria.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await closeIncident(loan.id, nota.trim());
      onSuccess();
    } catch (e) {
      setError(e.detail || e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <GlassModal
      open
      onClose={enviando ? undefined : onClose}
      title={`Cerrar incidencia — ${loan.folio}`}
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={enviando} className="btn-go-ghost">
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={enviando}
            className="btn-go-ghost"
            style={{ color: "var(--go-error)" }}
          >
            {enviando ? "Cerrando..." : "Cerrar incidencia"}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Los equipos de este préstamo que quedaron en "revisión" vuelven a
          quedar disponibles ("activo") al cerrar la incidencia.
        </p>
        <div>
          <label className="go-eyebrow mb-1.5 block">Nota (obligatoria)</label>
          <textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={3} className="go-input resize-none" required />
        </div>
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
