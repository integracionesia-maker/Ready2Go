import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { approveTicket, fetchTickets, hardDeleteTicket, rejectTicket, softDeleteTicket } from "@/api";
import { PRIORITY_BADGE_CLASS, PRIORITY_LABELS } from "../utils/priority";
import DeleteConfirmModal from "./DeleteConfirmModal";
import MediaViewerModal from "./MediaViewerModal";
import Modal from "./Modal";
import { GlassPanel, RowActions, ICONS, usePageTitle } from "@/design";

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

const UNDO_SECONDS = 5;

export default function ValidationQueue({ onChange }) {
  usePageTitle("Validación");
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [viewerTicket, setViewerTicket] = useState(null);
  const [approveTarget, setApproveTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // ── Undo toast ──────────────────────────────────────────────────────
  const location = useLocation();
  const [undo, setUndo] = useState(null); // { ticket, action, label, fn }
  const undoRef = useRef(null);
  const [undoLeft, setUndoLeft] = useState(0);

  // Expira al cambiar de ruta
  useEffect(() => { if (undo) ejecutarUndo(); }, [location.pathname]); // eslint-disable-line

  const ejecutarUndo = useCallback(() => {
    if (!undoRef.current) return;
    const pendiente = undoRef.current;
    undoRef.current = null;
    setUndo(null);
    pendiente.fn();
  }, []);

  const programarUndo = useCallback((ticket, action, label, fn) => {
    // Si ya hay un undo pendiente, ejecutarlo antes de programar el nuevo
    if (undoRef.current) ejecutarUndo();
    undoRef.current = { ticket, action, label, fn };
    setUndo({ ticket, action, label });
    setUndoLeft(UNDO_SECONDS);
  }, [ejecutarUndo]);

  // Countdown
  useEffect(() => {
    if (!undo || undoLeft <= 0) return;
    const id = setInterval(() => {
      setUndoLeft((prev) => {
        if (prev <= 0.1) { clearInterval(id); ejecutarUndo(); return 0; }
        return prev - 0.1;
      });
    }, 100);
    return () => clearInterval(id);
  }, [undo, undoLeft, ejecutarUndo]);

  const cancelarUndo = () => {
    undoRef.current = null;
    setUndo(null);
    setUndoLeft(0);
  };

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

  const doApprove = async (ticket) => {
    setSubmitting(true); setError(null);
    try {
      await approveTicket(ticket.id);
      load(); if (onChange) onChange();
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  };

  const doReject = async (ticket, reason) => {
    setSubmitting(true); setError(null);
    try {
      await rejectTicket(ticket.id, reason);
      setRejectReason(""); load(); if (onChange) onChange();
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  };

  const doSoftDelete = async (ticket) => {
    setSubmitting(true); setError(null);
    try {
      await softDeleteTicket(ticket.id);
      load(); if (onChange) onChange();
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  };

  const handleApprove = () => {
    if (!approveTarget) return;
    programarUndo(approveTarget, "aprobado", "Aprobado", () => doApprove(approveTarget));
    setApproveTarget(null);
  };

  const handleReject = () => {
    if (!rejectTarget || !rejectReason.trim()) return;
    const ticket = rejectTarget;
    const reason = rejectReason.trim();
    programarUndo(ticket, "rechazado", "Rechazado", () => doReject(ticket, reason));
    setRejectTarget(null);
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
        <GlassPanel className="p-4 sm:p-6">
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
                          { key: "ver", label: "Ver comprobante", icon: ICONS.ver, onClick: () => setViewerTicket(t) },
                          { key: "aprobar", label: "Aprobar", icon: ICONS.aprobar, variant: "success", onClick: () => setApproveTarget(t) },
                          { key: "rechazar", label: "Rechazar", icon: ICONS.rechazar, variant: "warning", onClick: () => { setRejectTarget(t); setRejectReason(""); } },
                          { key: "eliminar", label: "Eliminar", icon: ICONS.eliminar, variant: "danger", onClick: () => setDeleteTarget(t) },
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
        </GlassPanel>
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
          onSoftDelete={() => {
            programarUndo(deleteTarget, "eliminado", "Eliminado", () => doSoftDelete(deleteTarget));
            setDeleteTarget(null);
          }}
          onHardDelete={async () => {
            await hardDeleteTicket(deleteTarget.id);
            setDeleteTarget(null);
            load();
            if (onChange) onChange();
          }}
        />
      )}

      {/* ── Undo toast ──────────────────────────────────────────────── */}
      {undo && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2">
          <div
            className="flex items-center gap-4 rounded-go px-5 py-3 shadow-lg"
            style={{ background: "var(--go-surface-raised)", border: "1px solid var(--go-border)" }}
          >
            <span className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
              Ticket <strong>{undo.label.toLowerCase()}</strong> — {undo.ticket.creator_name} · {formatCurrency(undo.ticket.amount)}
            </span>
            <button
              type="button"
              onClick={cancelarUndo}
              className="rounded-go px-3 py-1 font-display text-xs font-bold uppercase tracking-wide transition-colors hover:opacity-80"
              style={{ background: "var(--go-orange)", color: "#fff" }}
            >
              Deshacer
            </button>
          </div>
          {/* Barra de progreso */}
          <div className="mx-5 mt-1 h-1 overflow-hidden rounded-full" style={{ background: "var(--go-surface-sunken)" }}>
            <div
              className="h-full rounded-full transition-all duration-100"
              style={{
                width: `${(undoLeft / UNDO_SECONDS) * 100}%`,
                background: undo.action === "aprobado" ? "var(--go-success)" : undo.action === "rechazado" ? "var(--go-warning)" : "var(--go-error)",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
