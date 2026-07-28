/**
 * Reusable modal shell: overlay + centered panel + header with close button.
 * Form content, banners and action buttons are provided by the consumer.
 */
export default function Modal({ title, onClose, submitting = false, children }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
      onClick={submitting ? undefined : onClose}
    >
      <div
        className="relative w-full max-w-lg overflow-hidden"
        style={{
          background: "var(--go-surface)",
          borderRadius: "var(--go-radius-lg)",
          border: "1px solid var(--go-border)",
          boxShadow: "0 25px 50px rgba(0,0,0,0.5)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
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
  );
}
