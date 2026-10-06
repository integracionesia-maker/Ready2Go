import { useRef, useState } from "react";
import { GlassModal } from "@/design";
import { useAuth } from "@/context/AuthContext";
import { mySignatureUrl } from "@/api";
import SignaturePad from "./SignaturePad";
import { uploadMedia } from "../api";

const ETIQUETA = {
  firma_entrega: "Firma del aprobador",
  firma_responsable: "Firma del beneficiario",
};

/** Completa, desde la ficha, una firma que quedó pendiente al confirmar el
 * préstamo (§1b de loan_state.py) — el servidor la acepta en cualquier
 * momento antes de `completado`. Al guardarse, la responsiva se regenera sola
 * (v2) y se avisa por correo; este modal solo sube la firma.
 *
 * Firma guardada (docs/equipos/firma-guardada.md): si quien firma tiene una
 * firma predeterminada en su Perfil y `permiteFirmaGuardada`, ofrece firmar con
 * un solo botón (el servidor copia SU firma — el cliente no la manda). El padre
 * decide `permiteFirmaGuardada`: siempre en la firma del aprobador (el servidor
 * ya exige ser el titular), y en la del beneficiario solo si quien firma ES el
 * beneficiario; si firma por otra persona, tiene que dibujar. */
export default function CompletarFirmaModal({ loanId, kind, permiteFirmaGuardada = false, onClose, onSuccess }) {
  const { user, refreshUser } = useAuth();
  const tieneGuardada = Boolean(user?.tiene_firma_guardada);
  const ofreceGuardada = permiteFirmaGuardada && tieneGuardada;

  const padRef = useRef(null);
  const [modo, setModo] = useState(ofreceGuardada ? "guardada" : "dibujar");
  const [guardarComoPredeterminada, setGuardarComoPredeterminada] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [version] = useState(() => Date.now());

  async function handleSubmit() {
    setEnviando(true);
    setError(null);
    try {
      if (modo === "guardada") {
        await uploadMedia(loanId, { kind, usarFirmaGuardada: true });
      } else {
        if (padRef.current.isEmpty()) {
          setError("Dibuja la firma antes de guardar.");
          return;
        }
        const blob = await padRef.current.getBlob();
        await uploadMedia(loanId, {
          file: new File([blob], `${kind}.png`, { type: "image/png" }),
          kind,
          guardarComoPredeterminada: permiteFirmaGuardada && guardarComoPredeterminada,
        });
        // La firma del préstamo ya quedó; el perfil se refresca sin bloquear.
        if (permiteFirmaGuardada && guardarComoPredeterminada) refreshUser().catch(() => {});
      }
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
            {enviando ? "Guardando..." : modo === "guardada" ? "Firmar con mi firma guardada" : "Guardar firma"}
          </button>
        </div>
      }
    >
      <div className="space-y-3">
        <p className="go-eyebrow">{ETIQUETA[kind] || kind}</p>

        {modo === "guardada" ? (
          <div className="space-y-2">
            <div
              className="flex items-center justify-center border p-3"
              style={{ background: "var(--go-white)", borderRadius: "var(--go-radius)", borderColor: "var(--go-border)", height: "160px" }}
            >
              <img
                data-testid="firma-guardada-preview"
                src={mySignatureUrl(version)}
                alt="Tu firma guardada"
                style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
              />
            </div>
            <button
              type="button"
              onClick={() => setModo("dibujar")}
              disabled={enviando}
              className="btn-go-ghost text-xs px-3 py-1"
              data-testid="firma-dibujar-otra"
            >
              Dibujar otra
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <SignaturePad ref={padRef} />
            {permiteFirmaGuardada && (
              <label className="flex items-center gap-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                <input
                  type="checkbox"
                  checked={guardarComoPredeterminada}
                  onChange={(e) => setGuardarComoPredeterminada(e.target.checked)}
                  disabled={enviando}
                  data-testid="firma-guardar-predeterminada"
                />
                {tieneGuardada ? "Reemplazar mi firma predeterminada con esta" : "Guardar como mi firma predeterminada"}
              </label>
            )}
            {ofreceGuardada && (
              <button
                type="button"
                onClick={() => setModo("guardada")}
                disabled={enviando}
                className="btn-go-ghost text-xs px-3 py-1"
                data-testid="firma-usar-guardada"
              >
                Usar mi firma guardada
              </button>
            )}
          </div>
        )}

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
