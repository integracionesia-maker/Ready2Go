import { useRef, useState } from "react";
import { GlassModal } from "@/design";
import SignaturePad from "./SignaturePad";
import { uploadMedia } from "../api";

const ETIQUETA = {
  firma_entrega: "Firma de quien entrega el equipo",
  firma_responsable: "Firma del responsable",
};

/** Completa, desde la ficha, una firma que quedó pendiente al confirmar el
 * préstamo (§1b de loan_state.py) — el servidor la acepta en cualquier
 * momento antes de `completado`. Al guardarse, la responsiva se regenera sola
 * (v2) y se avisa por correo; este modal solo sube la firma. */
export default function CompletarFirmaModal({ loanId, kind, onClose, onSuccess }) {
  const padRef = useRef(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit() {
    if (padRef.current.isEmpty()) {
      setError("Dibuja la firma antes de guardar.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const blob = await padRef.current.getBlob();
      await uploadMedia(loanId, { file: new File([blob], `${kind}.png`, { type: "image/png" }), kind });
      onSuccess();
    } catch (e) {
      setError(e.detail || e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <GlassModal
      open
      onClose={enviando ? undefined : onClose}
      title="Completar firma pendiente"
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={enviando} className="btn-go-ghost">
            Cancelar
          </button>
          <button type="button" onClick={handleSubmit} disabled={enviando} className="btn-go">
            {enviando ? "Guardando..." : "Guardar firma"}
          </button>
        </div>
      }
    >
      <div className="space-y-3">
        <p className="go-eyebrow">{ETIQUETA[kind] || kind}</p>
        <SignaturePad ref={padRef} />
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
