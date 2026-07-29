import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

const ToastContext = createContext(null);
let toastIdCounter = 0;

const TONE_ACCENT = {
  info: "var(--go-orange)",
  success: "var(--go-success)",
  error: "var(--go-error)",
  warning: "var(--go-warning)",
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((toast) => {
    const id = ++toastIdCounter;
    setToasts((prev) => [...prev, { id, tone: "info", duration: 4000, ...toast }]);
    return id;
  }, []);

  useEffect(() => {
    const timers = toasts.map((t) => setTimeout(() => remove(t.id), t.duration));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toasts.map((t) => t.id).join(","), remove]);

  return (
    <ToastContext.Provider value={{ push, remove }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2 sm:bottom-6 sm:right-6">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              role="status"
              aria-live="polite"
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="glass pointer-events-auto"
            >
              <div className="veil flex items-start gap-3 border-l-4 px-4 py-3" style={{ borderColor: TONE_ACCENT[t.tone] || TONE_ACCENT.info }}>
                <div className="flex-1">
                  {t.title && (
                    <p className="font-display text-sm font-bold" style={{ color: "var(--go-text-primary)" }}>
                      {t.title}
                    </p>
                  )}
                  {t.message && (
                    <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                      {t.message}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => remove(t.id)}
                  aria-label="Cerrar notificación"
                  className="rounded-go p-1 hover:bg-white/5"
                  style={{ color: "var(--go-text-muted)" }}
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast debe usarse dentro de <ToastProvider>.");
  }
  return ctx;
}
