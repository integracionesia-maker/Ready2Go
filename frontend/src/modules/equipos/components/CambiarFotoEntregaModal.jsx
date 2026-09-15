import { useState } from "react";
import { GlassModal, useToast } from "@/design";
import PhotoCapture from "./PhotoCapture";
import { uploadMedia } from "../api";

/** Reemplaza una foto de ENTREGA (frente/atrás) desde la ficha del préstamo —
 * espejo de la fecha de regreso esperada: quien ve la ficha puede retomar la
 * foto en cualquier momento antes de que el préstamo se cierre. Las fotos de
 * devolución no se tocan (docs/equipos/fotos-entrega-reemplazables.md). La
 * subida es inmediata dentro de PhotoCapture (mismo flujo que el wizard); el
 * modal solo envuelve y confirma. */
export default function CambiarFotoEntregaModal({ loanId, item, kind, label, onClose, onSuccess }) {
  const { push } = useToast();
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState(null);

  async function handleUpload(blob) {
    setSubiendo(true);
    setError(null);
    try {
      await uploadMedia(loanId, {
        file: new File([blob], `${kind}.jpg`, { type: blob.type }),
        kind,
        loanItemId: item.id,
      });
      push({ tone: "success", title: "Foto reemplazada" });
      onSuccess();
    } catch (e) {
      setError(e.detail || e.message);
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <GlassModal
      open
      onClose={subiendo ? undefined : onClose}
      title={`Cambiar foto de entrega — ${item.equipo_nombre}`}
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={subiendo} className="btn-go-ghost">
            Cerrar
          </button>
        </div>
      }
    >
      <div className="space-y-3">
        <p className="go-eyebrow">{label}</p>
        <PhotoCapture label={label} existingMediaId={item.media[kind]} onUpload={handleUpload} />
        {error && (
          <div
            className="rounded-go border px-4 py-3 font-body text-sm"
            style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
          >
            {error}
          </div>
        )}
      </div>
    </GlassModal>
  );
}
