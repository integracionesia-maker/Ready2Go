import { useState } from "react";
import { GlassModal } from "@/design";
import { auditEquipment } from "../api";

const CONDICIONES_CONOCIDAS = ["bueno", "atencion"];

// equipos_inventario:auditar_condicion — condicion/estado_fisico/comentario
// son la inspeccion fisica del equipo, separada de "editar" (metadata). La
// fecha de auditoria la pone el servidor (mismo patron que atrasado/
// dias_atraso): no se manda desde aqui.
export default function EquipmentAuditModal({ equipo, onClose, onSuccess }) {
  const [condicion, setCondicion] = useState(equipo.condicion || "bueno");
  const [estadoFisico, setEstadoFisico] = useState(equipo.estado_fisico || "");
  const [comentario, setComentario] = useState(equipo.comentario_auditoria || "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await auditEquipment(equipo.id, {
        condicion,
        estado_fisico: estadoFisico.trim() || null,
        comentario_auditoria: comentario.trim() || null,
      });
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <GlassModal
      open
      onClose={submitting ? undefined : onClose}
      title={`Auditar condición — ${equipo.nombre}`}
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">
            Cancelar
          </button>
          <button type="submit" form="equipment-audit-form" disabled={submitting} className="btn-go">
            {submitting ? "Guardando..." : "Guardar auditoría"}
          </button>
        </div>
      }
    >
      <form id="equipment-audit-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="go-eyebrow mb-1.5 block">Condición</label>
          <select value={condicion} onChange={(e) => setCondicion(e.target.value)} className="go-select">
            {CONDICIONES_CONOCIDAS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Estado físico</label>
          <input
            type="text"
            value={estadoFisico}
            onChange={(e) => setEstadoFisico(e.target.value)}
            placeholder="ej. nuevo, usado"
            className="go-input"
          />
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Comentario de auditoría</label>
          <textarea
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            rows={3}
            className="go-input resize-none"
          />
        </div>

        {error && (
          <div
            className="rounded-go border px-4 py-3 font-body text-sm"
            style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
          >
            {error}
          </div>
        )}
      </form>
    </GlassModal>
  );
}
