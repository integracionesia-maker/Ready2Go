import { useState, useRef, useCallback } from "react";
import { createGeneralExpense } from "@/api";

const ALLOWED_EXTS = [".jpg", ".jpeg", ".png", ".pdf"];
const ALLOWED_MIME = [
  "image/jpeg",
  "image/png",
  "image/jpg",
  "application/pdf",
];

export default function GeneralExpenseModal({ brands, onClose, onSuccess }) {
  const [brandId, setBrandId] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const activeBrands = (brands || []).filter((b) => b.is_active);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fileInputRef = useRef(null);

  /* ── File validation ─────────────────────────────────────────────────── */

  const validateAndSet = useCallback((f) => {
    setError(null);
    if (!f) return;

    const ext = "." + f.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setError(
        `Formato no permitido: ${ext}. Solo: ${ALLOWED_EXTS.join(", ")}`
      );
      setFile(null);
      return;
    }
    if (!ALLOWED_MIME.includes(f.type)) {
      setError(`Tipo de archivo no permitido: ${f.type}`);
      setFile(null);
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("El archivo supera los 10 MB.");
      setFile(null);
      return;
    }
    setFile(f);
  }, []);

  /* ── Drag & drop handlers ────────────────────────────────────────────── */

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) validateAndSet(f);
  };

  const handleFileSelect = (e) => {
    const f = e.target.files[0];
    if (f) validateAndSet(f);
  };

  /* ── Submit ──────────────────────────────────────────────────────────── */

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (!brandId) {
      setError("Selecciona una marca.");
      return;
    }
    if (!description || description.trim().length < 1) {
      setError("La descripción es obligatoria.");
      return;
    }
    if (description.length > 500) {
      setError("La descripción no puede superar los 500 caracteres.");
      return;
    }
    if (!amount || Number(amount) <= 0) {
      setError("El monto debe ser mayor a $0.");
      return;
    }
    if (!file) {
      setError("Adjunta el comprobante del gasto.");
      return;
    }

    setSubmitting(true);
    try {
      await createGeneralExpense({
        brandId: Number(brandId),
        amount: Number(amount),
        description,
        file,
      });
      setSuccessMsg("Gasto general registrado exitosamente.");
      setTimeout(() => {
        onSuccess();
      }, 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  /* ── Render ──────────────────────────────────────────────────────────── */

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "var(--go-overlay)" }} onClick={submitting ? undefined : onClose}>
      <div
        className="glass relative w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
      <div className="veil">
        {/* ── Header ──────────────────────────────────────────────── */}
        <div
          className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4"
          style={{ borderBottom: "1px solid var(--go-border)" }}
        >
          <h2
            className="font-display text-base font-bold uppercase tracking-[0.06em]"
            style={{ color: "var(--go-text-primary)" }}
          >
            Nuevo Gasto General
          </h2>
          <button
            onClick={onClose}
            disabled={submitting}
            aria-label="Cerrar"
            className="rounded-go p-1.5 transition-colors hover:bg-white/5"
            style={{ color: "var(--go-text-secondary)" }}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ── Body ────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="space-y-4 px-4 sm:px-6 py-5">
          {/* Brand selector */}
          <div>
            <label className="go-eyebrow mb-1.5 block">Marca</label>
            <select
              value={brandId}
              onChange={(e) => setBrandId(e.target.value)}
              className="go-select"
              required
            >
              <option value="">Seleccionar marca...</option>
              {activeBrands.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="go-eyebrow mb-1.5 block">Descripción</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={500}
              placeholder="Describe el gasto general..."
              className="go-input resize-none"
              required
            />
            <p className="mt-1 font-body text-xs" style={{ color: "var(--go-text-muted)" }}>
              {description.length}/500 caracteres
            </p>
          </div>

          {/* Amount */}
          <div>
            <label className="go-eyebrow mb-1.5 block">Monto</label>
            <div className="relative">
              <span
                className="absolute left-3.5 top-[10px] font-mono text-sm"
                style={{ color: "var(--go-text-secondary)" }}
              >
                $
              </span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="go-input pl-7 font-mono"
                required
              />
            </div>
          </div>

          {/* File drop zone */}
          <div>
            <label className="go-eyebrow mb-1.5 block">Comprobante</label>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className="relative flex cursor-pointer flex-col items-center justify-center rounded-go-lg border-2 border-dashed px-6 py-4 sm:py-7 transition-colors"
              style={{
                borderColor: dragOver
                  ? "var(--go-orange)"
                  : file
                  ? "rgba(0,163,110,0.3)"
                  : "var(--go-surface-sunken)",
                background: dragOver
                  ? "var(--go-orange-tint)"
                  : file
                  ? "rgba(0,163,110,0.05)"
                  : "var(--go-bg)",
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              {file ? (
                <div className="text-center">
                  <svg
                    className="mx-auto mb-1.5 h-8 w-8"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    viewBox="0 0 24 24"
                    style={{ color: "var(--go-success)" }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p
                    className="font-display text-sm font-semibold"
                    style={{ color: "var(--go-success)" }}
                  >
                    {file.name}
                  </p>
                  <p className="mt-0.5 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                    {(file.size / 1024).toFixed(0)} KB — Haz clic para cambiar
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <svg
                    className="mx-auto mb-2 h-8 w-8"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    viewBox="0 0 24 24"
                    style={{ color: "var(--go-text-muted)" }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                    Arrastra el archivo aquí o{" "}
                    <span className="font-semibold" style={{ color: "var(--go-orange)" }}>
                      haz clic para seleccionar
                    </span>
                  </p>
                  <p className="mt-1 font-body text-xs" style={{ color: "var(--go-text-muted)" }}>
                    PNG, JPG o PDF — Máx. 10 MB
                  </p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          </div>

          {/* ── Notifications ──────────────────────────────────────── */}
          {error && (
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{
                background: "rgba(229,62,62,0.08)",
                borderColor: "rgba(229,62,62,0.25)",
                color: "var(--go-error)",
              }}
            >
              {error}
            </div>
          )}
          {successMsg && (
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{
                background: "rgba(0,163,110,0.08)",
                borderColor: "rgba(0,163,110,0.25)",
                color: "var(--go-success)",
              }}
            >
              {successMsg}
            </div>
          )}

          {/* ── Actions ────────────────────────────────────────────── */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="btn-go-ghost"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="btn-go"
            >
              {submitting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Registrando...
                </>
              ) : (
                "Registrar Gasto"
              )}
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>
  );
}
