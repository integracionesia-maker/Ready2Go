import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ICONS } from "./icons";

const POPOVER_WIDTH = 256; // px — coincide con w-64 de abajo

/**
 * Botón "i" que al hacer clic despliega una explicación corta de qué mide un
 * dato y cómo se calcula — pensado para los KPI del Dashboard que en
 * producción a veces llegan en $0/0 y no es obvio por qué (filtro de fechas,
 * falta de configuración, etc.).
 *
 * **Portal a `document.body`, no estilístico** (mismo motivo que
 * `AboutPanel.jsx`): las tarjetas KPI son `.glass` (`backdrop-filter`), que
 * crea su propio contexto de apilamiento — sin portal, el popover se recorta
 * a la tarjeta y las tarjetas siguientes del grid (pintadas después en el
 * DOM) lo tapan. Como ya no es descendiente de la tarjeta, se posiciona con
 * `fixed` a partir de `getBoundingClientRect()` del botón en vez de
 * `absolute`; se cierra en scroll/resize en vez de reubicarse, para no
 * arrastrar lógica de recálculo continuo por una tarjeta informativa.
 */
export default function InfoTooltip({ text, className = "" }) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState(null); // { top, left } en viewport
  const buttonRef = useRef(null);
  const popoverRef = useRef(null);

  const close = () => setOpen(false);

  const toggle = (e) => {
    e.stopPropagation();
    if (open) {
      close();
      return;
    }
    const rect = buttonRef.current?.getBoundingClientRect();
    if (!rect) return;
    const idealLeft = rect.right - POPOVER_WIDTH;
    const left = Math.min(Math.max(idealLeft, 8), window.innerWidth - POPOVER_WIDTH - 8);
    setCoords({ top: rect.bottom + 8, left });
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return undefined;
    function handleClickOutside(e) {
      if (buttonRef.current?.contains(e.target) || popoverRef.current?.contains(e.target)) return;
      close();
    }
    function handleEscape(e) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [open]);

  if (!text) return null;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={toggle}
        aria-label="Más información"
        aria-expanded={open}
        aria-haspopup="true"
        data-html2canvas-ignore="true"
        className={`flex h-3.5 w-3.5 flex-shrink-0 items-center justify-center rounded-full transition-colors hover:opacity-70 ${className}`.trim()}
        style={{ color: "var(--go-text-muted)" }}
      >
        <svg className="h-full w-full" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d={ICONS.info} />
        </svg>
      </button>

      {open && coords && typeof document !== "undefined" &&
        createPortal(
          <div
            ref={popoverRef}
            role="tooltip"
            data-html2canvas-ignore="true"
            className="fixed z-50 w-64 max-w-[calc(100vw-1rem)] rounded-go border p-3 text-left normal-case shadow-lg"
            style={{
              top: coords.top,
              left: coords.left,
              background: "var(--go-surface)",
              borderColor: "var(--go-border)",
            }}
          >
            <p className="font-body text-xs font-normal leading-relaxed" style={{ color: "var(--go-text-secondary)" }}>
              {text}
            </p>
          </div>,
          document.body
        )}
    </>
  );
}
