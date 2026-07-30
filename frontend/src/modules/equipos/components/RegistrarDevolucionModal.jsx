import { useState } from "react";
import { GlassModal, useToast } from "@/design";
import { returnLoan, uploadMedia } from "../api";
import PhotoCapture from "./PhotoCapture";

function itemDevolucionLista(estadoItem) {
  if (estadoItem.noDevuelto) return Boolean(estadoItem.notaDevolucion?.trim());
  return Boolean(estadoItem.fotoFrenteId && estadoItem.fotoAtrasId);
}

/** Por cada equipo: 2 fotos de devolución O `no_devuelto: true` con nota
 * obligatoria — nunca a medias (regla dura de §3 del contrato). Las fotos
 * se suben una por una (mismo patrón atómico que el wizard: uploadMedia
 * adjunta al item en la misma llamada) antes de mandar `returnLoan`. */
export default function RegistrarDevolucionModal({ loan, onClose, onSuccess }) {
  const { push } = useToast();
  const [porItem, setPorItem] = useState(() =>
    Object.fromEntries(
      loan.items.map((it) => [
        it.id,
        { noDevuelto: false, notaDevolucion: "", fotoFrenteId: it.media.foto_dev_frente, fotoAtrasId: it.media.foto_dev_atras },
      ])
    )
  );
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  function actualizarItem(itemId, patch) {
    setPorItem((prev) => ({ ...prev, [itemId]: { ...prev[itemId], ...patch } }));
  }

  async function subirFoto(item, kind, blob) {
    const file = new File([blob], `${kind}.jpg`, { type: blob.type });
    const res = await uploadMedia(loan.id, { file, kind, loanItemId: item.id });
    actualizarItem(item.id, { [kind === "foto_dev_frente" ? "fotoFrenteId" : "fotoAtrasId"]: res.id });
  }

  const todoListo = loan.items.every((it) => itemDevolucionLista(porItem[it.id]));

  async function handleSubmit() {
    setError(null);
    if (!todoListo) {
      setError("Falta registrar la devolución de uno o más equipos (2 fotos o el motivo de no devolución).");
      return;
    }
    setEnviando(true);
    try {
      // I8 lote 1: las llaves de cada item van tal cual las exige
      // `DevolucionItem` del servidor real (snake_case) — mismo patrón que
      // `ConfirmarDevolucionModal.jsx` ya usaba para `/confirmar-devolucion`.
      // Antes se mandaba camelCase y el servidor real respondía 422
      // (`loan_item_id` es obligatorio, sin default) — el mock lo aceptaba
      // igual porque nunca validó la forma, por eso sobrevivió a 48/48.
      await returnLoan(loan.id, {
        decisionesPorItem: loan.items.map((it) => ({
          loan_item_id: it.id,
          no_devuelto: porItem[it.id].noDevuelto,
          nota_devolucion: porItem[it.id].noDevuelto ? porItem[it.id].notaDevolucion : null,
        })),
      });
      push({ tone: "success", title: "Devolución registrada" });
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
      title={`Registrar devolución — ${loan.folio}`}
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={enviando} className="btn-go-ghost">
            Cancelar
          </button>
          <button type="button" onClick={handleSubmit} disabled={enviando || !todoListo} className="btn-go">
            {enviando ? "Guardando..." : "Registrar devolución"}
          </button>
        </div>
      }
    >
      <div className="space-y-6">
        <ul className="space-y-6" data-testid="equipos-devolucion">
          {loan.items.map((it) => {
            const estadoItem = porItem[it.id];
            return (
              <li key={it.id} className="border-b pb-4" style={{ borderColor: "var(--go-border)" }}>
                <p className="mb-3 font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                  {it.equipo_nombre}
                </p>

                <label className="mb-3 flex items-center gap-2 font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                  <input
                    type="checkbox"
                    checked={estadoItem.noDevuelto}
                    onChange={(e) => actualizarItem(it.id, { noDevuelto: e.target.checked })}
                    className="h-4 w-4"
                  />
                  No devuelto
                </label>

                {estadoItem.noDevuelto ? (
                  <div>
                    <label className="go-eyebrow mb-1.5 block">Motivo (obligatorio)</label>
                    <textarea
                      value={estadoItem.notaDevolucion}
                      onChange={(e) => actualizarItem(it.id, { notaDevolucion: e.target.value })}
                      rows={2}
                      className="go-input resize-none"
                      required
                    />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <PhotoCapture
                      label="Foto de frente"
                      existingMediaId={estadoItem.fotoFrenteId}
                      onUpload={(blob) => subirFoto(it, "foto_dev_frente", blob)}
                    />
                    <PhotoCapture
                      label="Foto de atrás"
                      existingMediaId={estadoItem.fotoAtrasId}
                      onUpload={(blob) => subirFoto(it, "foto_dev_atras", blob)}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>

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
