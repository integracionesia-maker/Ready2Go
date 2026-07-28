import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";

const CommandPaletteContext = createContext(null);

function isTypingTarget(el) {
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
}

export function CommandPaletteProvider({ children }) {
  const [commands, setCommands] = useState([]);
  const [open, setOpen] = useState(false);

  const register = useCallback((command) => {
    setCommands((prev) => [...prev.filter((c) => c.id !== command.id), command]);
    return () => setCommands((prev) => prev.filter((c) => c.id !== command.id));
  }, []);

  useEffect(() => {
    function handleKeydown(e) {
      // Nunca captura teclas mientras el foco está en un campo de texto —
      // incluye Cmd/Ctrl+K: si alguien escribe en un input, esta paleta no
      // existe para el navegador.
      if (isTypingTarget(e.target)) return;
      const isMod = e.metaKey || e.ctrlKey;
      if (isMod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, []);

  const value = useMemo(() => ({ register, open, setOpen }), [register, open]);

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}
      <CommandPaletteModal open={open} onClose={() => setOpen(false)} commands={commands} />
    </CommandPaletteContext.Provider>
  );
}

/** Registra un comando mientras el componente llamador está montado. */
export function useRegisterCommand(command) {
  const ctx = useContext(CommandPaletteContext);
  useEffect(() => {
    if (!ctx || !command) return undefined;
    return ctx.register(command);
  }, [ctx, command]);
}

export function useCommandPalette() {
  const ctx = useContext(CommandPaletteContext);
  if (!ctx) {
    throw new Error("useCommandPalette debe usarse dentro de <CommandPaletteProvider>.");
  }
  return ctx;
}

function CommandPaletteModal({ open, onClose, commands }) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q) || c.keywords?.toLowerCase().includes(q));
  }, [query, commands]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  useEffect(() => setActiveIndex(0), [query]);

  function run(cmd) {
    onClose();
    cmd.run?.({ navigate });
  }

  function handleKeyDown(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[activeIndex]) run(filtered[activeIndex]);
    } else if (e.key === "Escape") {
      onClose();
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[95] flex items-start justify-center px-4 pt-[12vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <div className="absolute inset-0" style={{ background: "var(--go-overlay)" }} onClick={onClose} aria-hidden="true" />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Paleta de comandos"
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="glass relative z-10 w-full max-w-lg overflow-hidden"
            onKeyDown={handleKeyDown}
          >
            <div className="veil flex max-h-[60vh] flex-col">
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar una acción..."
                aria-label="Buscar comando"
                className="go-input rounded-none border-0 border-b focus:shadow-none"
                style={{ borderColor: "var(--go-border)" }}
              />
              <ul role="listbox" className="flex-1 overflow-y-auto py-2">
                {filtered.length === 0 && (
                  <li className="px-4 py-3 font-body text-sm" style={{ color: "var(--go-text-muted)" }}>
                    Sin resultados.
                  </li>
                )}
                {filtered.map((c, i) => (
                  <li key={c.id} role="option" aria-selected={i === activeIndex}>
                    <button
                      type="button"
                      onMouseEnter={() => setActiveIndex(i)}
                      onClick={() => run(c)}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left font-body text-sm transition-colors"
                      style={{
                        background: i === activeIndex ? "var(--go-surface-sunken)" : "transparent",
                        color: "var(--go-text-primary)",
                      }}
                    >
                      {c.icon}
                      {c.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
