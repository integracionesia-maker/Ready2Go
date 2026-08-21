import { useRef, useState } from "react";
import Modal from "@/modules/presupuestos/components/Modal";
import { CameraCaptureButton } from "@/design";
import { createOperationalExpense } from "../api";

const ACCEPT = "image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf";
const ALLOWED_EXTS = [".jpg", ".jpeg", ".png", ".pdf"];

function extensionDe(nombre) {
  const partes = (nombre || "").split(".");
  return partes.length > 1 ? `.${partes.pop().toLowerCase()}` : "";
}

function hoyISO() {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
}

export default function GastoModal({ rubros, onClose, onSuccess }) {
  const [rubroId, setRubroId] = useState("");
  const [fechaGasto, setFechaGasto] = useState(hoyISO());
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  const setArchivo = (f) => {
    setError(null);
    if (!f) return;
    const ext = extensionDe(f.name);
    if (!ALLOWED_EXTS.includes(ext)) {
      setError(`Formato no permitido. Solo: ${ALLOWED_EXTS.join(", ")}`);
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("El archivo supera los 10 MB.");
      return;
    }
    setFile(f);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!rubroId) return setError("Selecciona un rubro.");
    if (!amount || Number(amount) <= 0) return setError("El monto debe ser mayor a $0.");
    if (!description.trim()) return setError("La descripción es obligatoria.");
    if (!fechaGasto) return setError("La fecha del gasto es obligatoria.");
    if (!file) return setError("El comprobante es obligatorio.");

    setSubmitting(true);
    try {
      await createOperationalExpense({
        rubroId,
        amount: Number(amount),
        description: description.trim(),
        fechaGasto,
        file,
      });
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Nuevo Gasto Operativo" onClose={onClose} submitting={submitting}>
      <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-4 overflow-y-auto px-4 sm:px-6 py-5">
        <div>
          <label className="go-eyebrow mb-1.5 block">Rubro</label>
          <select value={rubroId} onChange={(e) => setRubroId(e.target.value)} className="go-select" required>
            <option value="">Selecciona un rubro...</option>
            {rubros.map((r) => (
              <option key={r.id} value={r.id}>{r.nombre}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="go-eyebrow mb-1.5 block">Fecha del gasto</label>
            <input type="date" value={fechaGasto} onChange={(e) => setFechaGasto(e.target.value)} className="go-input" required />
            <p className="mt-1 font-body text-[11px]" style={{ color: "var(--go-text-muted)" }}>
              Define el mes al que cuenta el gasto.
            </p>
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Monto (MXN)</label>
            <input type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className="go-input" required />
          </div>
        </div>

        <div>
          <label className="go-eyebrow mb-1.5 block">Descripción</label>
          <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} className="go-input" maxLength={500} required />
        </div>

        <div>
          <label className="go-eyebrow mb-1.5 block">Comprobante (obligatorio)</label>
          <div
            className="flex cursor-pointer items-center justify-center rounded-go-lg border-2 border-dashed px-4 py-4"
            style={{
              borderColor: file ? "rgba(0,163,110,0.3)" : "var(--go-surface-sunken)",
              background: file ? "rgba(0,163,110,0.05)" : "var(--go-bg)",
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <span className="font-body text-sm" style={{ color: file ? "var(--go-success)" : "var(--go-text-primary)" }}>
              {file ? file.name : "Toca para elegir un archivo (PNG, JPG o PDF)"}
            </span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files[0];
              e.target.value = "";
              setArchivo(f);
            }}
          />
          <div className="mt-2">
            <CameraCaptureButton onFile={setArchivo} onError={setError} />
          </div>
        </div>

        {error && (
          <div
            className="rounded-go border px-4 py-3 font-body text-sm"
            style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
          >
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">Cancelar</button>
          <button type="submit" disabled={submitting} className="btn-go">{submitting ? "Guardando..." : "Registrar Gasto"}</button>
        </div>
      </form>
    </Modal>
  );
}
