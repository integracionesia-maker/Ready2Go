import { useEffect, useState } from "react";
import { approveTicket, fetchTickets, hardDeleteTicket, rejectTicket, softDeleteTicket } from "@/api";
import { PRIORITY_BADGE_CLASS, PRIORITY_LABELS } from "../utils/priority";
import DeleteConfirmModal from "./DeleteConfirmModal";
import MediaViewerModal from "./MediaViewerModal";
import Modal from "./Modal";
import RowActions from "./RowActions";

function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-MX", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ValidationQueue({ onChange }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [viewerTicket, setViewerTicket] = useState(null);
  const [approveTarget, setApproveTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setTickets(await fetchTickets({ status: "pendiente" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleApprove = async () => {
    if (!approveTarget) return;
    setSubmitting(true);
    setError(null);
    try {
      await approveTicket(approveTarget.id);
      setApproveTarget(null);
      load();
      if (onChange) onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectTarget || !rejectReason.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await rejectTicket(rejectTarget.id, rejectReason.trim());
      setRejectTarget(null);
      setRejectReason("");
      load();
      if (onChange) onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const errorBanner = error && (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
    >
      {error}
    </div>
  );

  const wouldGoNegative =
    approveTarget && approveTarget.cycle_amount != null && approveTarget.amount > approveTarget.cycle_amount - approveTarget.cycle_spent;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Validación de Tickets
        </h2>
        <span className="go-eyebrow">{tickets.length} pendientes</span>
      </div>

      {errorBanner}

      {loading ? (
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Cargando...
        </p>
      ) : tickets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          <svg className="mb-4 h-12 w-12" fill="none" stroke="currentColor" strokeWidth={1} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>No hay tickets pendientes de validación.</p>
        </div>
      ) : (
        <div className="go-table-scroll-wrapper">
        <div className="overflow-x-auto go-table-scroll rounded-go-lg border" style={{ borderColor: "var(--go-border)" }}>
          <table className="go-table">
            <thead>
              <tr>
                <th>Creador</th>
                <th>Marca</th>
                <th className="text-right">Monto</th>
                <th>Fecha</th>
                <th className="text-right">Ciclo restante</th>
                <th className="text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => {
                const cycleRemaining = t.cycle_amount != null ? t.cycle_amount - t.cycle_spent : null;
                return (
                  <tr key={t.id}>
                    <td>
                      <span className="font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                        {t.creator_name}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span>{t.brand_name}</span>
                        {t.brand_priority && (
                          <span className={`go-badge ${PRIORITY_BADGE_CLASS[t.brand_priority] || "go-badge-warning"}`}>
                            {PRIORITY_LABELS[t.brand_priority] || t.brand_priority}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="num text-right font-semibold" style={{ color: "var(--go-warning)" }}>
                      {formatCurrency(t.amount)}
                    </td>
                    <td style={{ color: "var(--go-text-secondary)" }}>{formatDate(t.upload_date)}</td>
                    <td
                      className="num text-right"
                      style={{ color: cycleRemaining != null && cycleRemaining < t.amount ? "var(--go-error)" : "var(--go-text-secondary)" }}
                    >
                      {cycleRemaining != null ? formatCurrency(cycleRemaining) : "—"}
                    </td>
                    <td>
                      <RowActions
                        actions={[
                          { key: "ver", label: "Ver", onClick: () => setViewerTicket(t) },
                          { key: "aprobar", label: "Aprobar", onClick: () => setApproveTarget(t) },
                          {
                            key: "rechazar",
                            label: "Rechazar",
                            onClick: () => {
                              setRejectTarget(t);
                              setRejectReason("");
                            },
                          },
                          { key: "eliminar", label: "Eliminar", variant: "danger", onClick: () => setDeleteTarget(t) },
                        ]}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        </div>
      )}

      {viewerTicket && <MediaViewerModal ticket={viewerTicket} onClose={() => setViewerTicket(null)} />}

      {approveTarget && (
        <Modal title="Aprobar ticket" onClose={() => setApproveTarget(null)} submitting={submitting}>
          <div className="space-y-4 px-4 sm:px-6 py-5">
            <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
              ¿Aprobar el ticket de <strong>{approveTarget.creator_name}</strong> por{" "}
              <strong>{formatCurrency(approveTarget.amount)}</strong>?
            </p>
            {wouldGoNegative && (
              <div
                className="rounded-go border px-4 py-3 font-body text-sm"
                style={{ background: "rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.25)", color: "var(--go-warning)" }}
              >
                Esto dejará el ciclo de {approveTarget.creator_name} en negativo. Puedes aprobar de todas formas.
              </div>
            )}
            {errorBanner}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button type="button" onClick={() => setApproveTarget(null)} disabled={submitting} className="btn-go-ghost">
                Cancelar
              </button>
              <button type="button" onClick={handleApprove} disabled={submitting} className="btn-go">
                {submitting ? "Aprobando..." : "Aprobar"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {rejectTarget && (
        <Modal title="Rechazar ticket" onClose={() => setRejectTarget(null)} submitting={submitting}>
          <div className="space-y-4 px-4 sm:px-6 py-5">
            <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
              Rechazar el ticket de <strong>{rejectTarget.creator_name}</strong> por{" "}
              <strong>{formatCurrency(rejectTarget.amount)}</strong>. El motivo es obligatorio y lo verá el creador.
            </p>
            <div>
              <label className="go-eyebrow mb-1.5 block">Motivo del rechazo</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={3}
                placeholder="Ej. Comprobante ilegible, monto no coincide..."
                className="go-input resize-none"
                required
              />
            </div>
            {errorBanner}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button type="button" onClick={() => setRejectTarget(null)} disabled={submitting} className="btn-go-ghost">
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={submitting || !rejectReason.trim()}
                className="btn-go"
              >
                {submitting ? "Rechazando..." : "Rechazar"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {deleteTarget && (
        <DeleteConfirmModal
          itemLabel={`el ticket de ${deleteTarget.creator_name} por ${formatCurrency(deleteTarget.amount)}`}
          onClose={() => setDeleteTarget(null)}
          onSoftDelete={async () => {
            await softDeleteTicket(deleteTarget.id);
            load();
            if (onChange) onChange();
          }}
          onHardDelete={async () => {
            await hardDeleteTicket(deleteTarget.id);
            load();
            if (onChange) onChange();
          }}
        />
      )}
    </div>
  );
}
