import { useState } from "react";
import { ticketFileUrl } from "@/api";

const ZOOM_STEPS = [1, 1.5, 2, 2.5];

/**
 * Visor in-app de comprobantes (R11): imagen con zoom básico o PDF embebido,
 * siempre vía el endpoint autenticado (nunca una URL pública) — las cookies de
 * sesión viajan automáticamente porque es del mismo origen.
 */
export default function MediaViewerModal({ ticket, onClose }) {
  const [zoomIndex, setZoomIndex] = useState(0);
  const [imgError, setImgError] = useState(false);

  if (!ticket) return null;

  const isImage = ticket.mime_type?.startsWith("image/");
  const isPdf = ticket.mime_type === "application/pdf";
  const fileUrl = ticketFileUrl(ticket.id);
  const zoom = ZOOM_STEPS[zoomIndex];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "var(--go-overlay)" }}
      onClick={onClose}
    >
      <div
        className="glass relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
      <div className="veil flex max-h-[90vh] flex-col">
        {/* ── Header ──────────────────────────────────────────────── */}
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: "1px solid var(--go-border)" }}
        >
          <h2
            className="truncate font-display text-base font-bold uppercase tracking-[0.06em]"
            style={{ color: "var(--go-text-primary)" }}
          >
            Comprobante — {ticket.file_name}
          </h2>
          <div className="flex items-center gap-2">
            {isImage && (
              <>
                <button
                  onClick={() => setZoomIndex((i) => Math.max(0, i - 1))}
                  disabled={zoomIndex === 0}
                  className="btn-go-ghost px-2.5 py-1.5 text-xs disabled:opacity-40"
                  title="Alejar"
                >
                  −
                </button>
                <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  onClick={() => setZoomIndex((i) => Math.min(ZOOM_STEPS.length - 1, i + 1))}
                  disabled={zoomIndex === ZOOM_STEPS.length - 1}
                  className="btn-go-ghost px-2.5 py-1.5 text-xs disabled:opacity-40"
                  title="Acercar"
                >
                  +
                </button>
              </>
            )}
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-go-ghost px-2.5 py-1.5 text-xs"
              title="Abrir en pestaña nueva"
            >
              Abrir aparte
            </a>
            <button
              onClick={onClose}
              aria-label="Cerrar"
              className="rounded-go p-1.5 transition-colors hover:bg-white/5"
              style={{ color: "var(--go-text-secondary)" }}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* ── Body ────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-auto p-4" style={{ background: "var(--go-bg)" }}>
          {isImage && !imgError && (
            <div className="flex min-h-full items-center justify-center">
              <img
                src={fileUrl}
                alt={ticket.file_name}
                onError={() => setImgError(true)}
                style={{ transform: `scale(${zoom})`, transformOrigin: "center", transition: "transform 150ms" }}
                className="max-w-full"
              />
            </div>
          )}

          {isImage && imgError && (
            <p className="py-16 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
              No se pudo cargar la imagen. Es posible que el archivo ya no exista.
            </p>
          )}

          {isPdf && (
            <iframe title={ticket.file_name} src={fileUrl} className="h-full min-h-[65vh] w-full rounded-go" style={{ border: "none" }} />
          )}

          {!isImage && !isPdf && (
            <p className="py-16 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
              Este tipo de archivo no tiene vista previa. Usa "Abrir aparte" para verlo.
            </p>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
