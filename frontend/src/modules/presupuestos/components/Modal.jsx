/**
 * Reusable modal shell: overlay + centered panel + header with close button.
 * Form content, banners and action buttons are provided by the consumer.
 *
 * I2 (piel): se apoya en la receta de cristal de GlassPanel/GlassModal
 * (.glass + .veil de src/design/glass.css) en vez de la superficie sólida
 * manual de antes. API y nombres accesibles sin cambio — los 5 consumidores
 * (AdminView, UserManagement, ValidationQueue, GeneralExpensesExportModal,
 * DeleteConfirmModal) no se tocan.
 */
export default function Modal({ title, onClose, submitting = false, children }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "var(--go-overlay)" }}
      onClick={submitting ? undefined : onClose}
    >
      <div
        className="glass relative w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="veil">
          {/* ── Header ──────────────────────────────────────────────── */}
          <div
            className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4"
            style={{ borderBottom: "1px solid var(--go-border)" }}
          >
            <h2
              className="font-display text-base font-bold uppercase tracking-[0.06em]"
              style={{ color: "var(--go-text-primary)" }}
            >
              {title}
            </h2>
            <button
              onClick={onClose}
              disabled={submitting}
              aria-label="Cerrar"
              className="rounded-go p-1.5 transition-colors hover:bg-white/5"
              style={{ color: "var(--go-text-secondary)" }}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* ── Body ────────────────────────────────────────────────── */}
          {children}
        </div>
      </div>
    </div>
  );
}
