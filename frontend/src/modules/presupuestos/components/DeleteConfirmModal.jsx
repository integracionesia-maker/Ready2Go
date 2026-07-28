import { useState } from "react";
import Modal from "./Modal";

/**
 * Confirmación de borrado en dos pasos, compartida por TransactionTable,
 * ValidationQueue y GeneralExpensesPage (R12): por defecto ofrece el borrado
 * lógico (recuperable); un enlace secundario escala al borrado físico
 * (irreversible), que exige leer una advertencia en rojo antes de confirmar.
 */
export default function DeleteConfirmModal({ itemLabel, onClose, onSoftDelete, onHardDelete }) {
  const [step, setStep] = useState("soft"); // "soft" | "hard"
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSoftDelete = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onSoftDelete();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleHardDelete = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onHardDelete();
      onClose();
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

  return (
    <Modal title={step === "soft" ? "Eliminar" : "Eliminar permanentemente"} onClose={onClose} submitting={submitting}>
      <div className="space-y-4 px-4 sm:px-6 py-5">
        {step === "soft" ? (
          <>
            <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
              ¿Eliminar {itemLabel}? Dejará de contar en cálculos y reportes, pero el registro y su comprobante se conservan para auditoría.
            </p>
            {errorBanner}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep("hard")}
                disabled={submitting}
                className="font-body text-xs underline"
                style={{ color: "var(--go-text-secondary)" }}
              >
                Prefiero eliminarlo permanentemente
              </button>
              <div className="flex items-center gap-3">
                <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">
                  Cancelar
                </button>
                <button type="button" onClick={handleSoftDelete} disabled={submitting} className="btn-go">
                  {submitting ? "Eliminando..." : "Eliminar"}
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{ background: "rgba(229,62,62,0.1)", borderColor: "rgba(229,62,62,0.35)", color: "var(--go-error)" }}
            >
              <strong>Esta acción es irreversible.</strong> El archivo y el registro de {itemLabel} se borrarán para siempre — no podrá recuperarse ni auditarse después.
            </div>
            {errorBanner}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep("soft")}
                disabled={submitting}
                className="font-body text-xs underline"
                style={{ color: "var(--go-text-secondary)" }}
              >
                Volver
              </button>
              <div className="flex items-center gap-3">
                <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleHardDelete}
                  disabled={submitting}
                  className="rounded-go px-4 py-2 font-display text-sm font-semibold text-white transition-colors"
                  style={{ background: "var(--go-error)" }}
                >
                  {submitting ? "Eliminando..." : "Eliminar permanentemente"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
