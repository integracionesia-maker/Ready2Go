import { useEffect, useId, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal de cristal con los cuatro requisitos no opcionales de 01-I1-shell.md:
 * role="dialog" + aria-modal, nombre accesible por el título, focus trap
 * real, cierre con Esc/backdrop, foco de vuelta al disparador al cerrar, y
 * scroll del body bloqueado mientras está abierto.
 */
export default function GlassModal({ open, onClose, title, children, footer, className = "", refract = false, mobileFullscreen = false }) {
  const titleId = useId();
  const panelRef = useRef(null);
  const previouslyFocused = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    previouslyFocused.current = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const panel = panelRef.current;
    const initialFocusable = panel?.querySelectorAll(FOCUSABLE_SELECTOR);
    (initialFocusable?.[0] || panel)?.focus();

    function handleKeydown(e) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose?.();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const focusables = Array.from(panel.querySelectorAll(FOCUSABLE_SELECTOR));
      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeydown, true);
    return () => {
      document.removeEventListener("keydown", handleKeydown, true);
      document.body.style.overflow = previousOverflow;
      previouslyFocused.current?.focus?.();
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={`fixed inset-0 z-[90] flex items-center justify-center ${mobileFullscreen ? "p-0 sm:p-4" : "p-4"}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <div className="absolute inset-0" style={{ background: "var(--go-overlay)" }} onClick={onClose} aria-hidden="true" />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className={`glass ${refract ? "glass--refract" : ""} relative z-10 w-full max-w-lg overflow-hidden outline-none ${
              mobileFullscreen ? "h-full rounded-none sm:h-auto sm:rounded-[var(--glass-radius)]" : ""
            } ${className}`.trim()}
          >
            <div className={`veil flex flex-col ${mobileFullscreen ? "h-full sm:max-h-[85vh]" : "max-h-[85vh]"}`}>
              <div className="flex items-center justify-between gap-4 border-b px-5 py-4" style={{ borderColor: "var(--go-border)" }}>
                <h2 id={titleId} className="font-display text-base font-bold" style={{ color: "var(--go-text-primary)" }}>
                  {title}
                </h2>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Cerrar"
                  className="rounded-go p-1.5 hover:bg-white/5"
                  style={{ color: "var(--go-text-secondary)" }}
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
              {footer && (
                <div className="border-t px-5 py-4" style={{ borderColor: "var(--go-border)" }}>
                  {footer}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
