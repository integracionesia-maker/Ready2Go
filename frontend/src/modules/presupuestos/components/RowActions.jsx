import { useEffect, useRef, useState } from "react";
import { useMobile } from "../hooks/useMobile";

/**
 * Acciones de una fila de tabla (auditoría de responsividad móvil, C2/C3):
 * en desktop, botones horizontales de siempre; en móvil (<640px), un botón
 * "⋯" que agrupa las mismas acciones en un menú desplegable — evita que 2-4
 * botones de texto se encimen o desborden en celdas angostas.
 *
 * `actions`: Array<{ key, label, mobileLabel?, onClick, variant?: "danger" } | falsy>
 * Los valores falsy (ej. `canDelete && {...}`) se filtran — así cada
 * consumidor puede condicionar una acción sin un `if` aparte.
 */
export default function RowActions({ actions }) {
  const isMobile = useMobile();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  const visibleActions = (actions || []).filter(Boolean);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  if (visibleActions.length === 0) return null;

  if (!isMobile) {
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        {visibleActions.map((a) => (
          <button
            key={a.key}
            type="button"
            onClick={a.onClick}
            className="btn-go-ghost text-xs px-3 py-1.5"
            style={a.variant === "danger" ? { color: "var(--go-error)" } : undefined}
          >
            {a.label}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="relative flex justify-end" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Más acciones"
        aria-haspopup="true"
        aria-expanded={open}
        className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-go transition-colors hover:bg-white/5"
        style={{ color: "var(--go-text-secondary)" }}
      >
        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 100-4 2 2 0 000 4zm0 6a2 2 0 100-4 2 2 0 000 4zm0 6a2 2 0 100-4 2 2 0 000 4z" />
        </svg>
      </button>
      {open && (
        <div
          className="absolute right-0 top-full z-20 mt-1 min-w-[170px] overflow-hidden rounded-go border py-1 shadow-lg"
          style={{ background: "var(--go-surface)", borderColor: "var(--go-border)" }}
        >
          {visibleActions.map((a) => (
            <button
              key={a.key}
              type="button"
              onClick={() => {
                setOpen(false);
                a.onClick();
              }}
              className="block w-full whitespace-nowrap px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
              style={{ color: a.variant === "danger" ? "var(--go-error)" : "var(--go-text-primary)" }}
            >
              {a.mobileLabel || a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
