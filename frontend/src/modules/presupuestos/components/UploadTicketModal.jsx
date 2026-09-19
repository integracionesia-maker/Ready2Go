import { useState, useRef, useCallback, useEffect } from "react";
import { uploadTicket } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { CameraCaptureButton, useMobile } from "@/design";

const ALLOWED_EXTS = [".jpg", ".jpeg", ".png", ".pdf"];
const ALLOWED_MIME = [
  "image/jpeg",
  "image/png",
  "image/jpg",
  "application/pdf",
];
// Con solo extensiones, varias versiones de Chrome en Android no ofrecen la
// cámara en el selector: la decisión la toman con los MIME. Se dejan las dos
// formas — los selectores de Windows sí usan las extensiones.
const ACCEPT = "image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf";
// Mismo valor que `upload_manager.MAX_FILES_PER_TICKET` — sin límite de
// negocio, solo salvaguarda técnica.
const MAX_FILES = 20;

/**
 * Extensión en minúsculas, o cadena vacía si el nombre no trae ninguna.
 * `"image".split(".").pop()` devuelve `"image"`, así que la versión anterior
 * producía `.image` y rechazaba con "Formato no permitido: .image" — que es
 * justo lo que entregan varias cámaras de Android.
 */
function extensionDe(nombre) {
  const partes = (nombre || "").split(".");
  return partes.length > 1 ? `.${partes.pop().toLowerCase()}` : "";
}

import { formatMXN } from "@/design";

export default function UploadTicketModal({
  creators,
  brands,
  onClose,
  onSuccess,
}) {
  const { user } = useAuth();
  const isCreador = user?.role === "creador";
  const esMovil = useMobile();

  const [creatorId, setCreatorId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fileInputRef = useRef(null);

  /* ── Derived ─────────────────────────────────────────────────────────── */

  const activeCreators = creators.filter((c) => c.is_active);
  const activeBrands = brands.filter((b) => b.is_active);

  const selectedCreator = activeCreators.find(
    (c) => c.id === Number(creatorId)
  );

  /* Un creador solo registra tickets a su propio nombre: preseleccionado y bloqueado. */
  useEffect(() => {
    if (isCreador && !creatorId && activeCreators.length > 0) {
      setCreatorId(String(activeCreators[0].id));
    }
  }, [isCreador, creatorId, activeCreators]);

  /* ── File validation ─────────────────────────────────────────────────── */

  /** Valida cada archivo nuevo y agrega los válidos a la lista ya elegida
   * (no reemplaza) — un error en uno no descarta los demás. */
  const addFiles = useCallback((fileList) => {
    setError(null);
    const nuevos = Array.from(fileList || []);
    if (nuevos.length === 0) return;

    setFiles((prev) => {
      const aceptados = [];
      let errorMsg = null;

      for (const f of nuevos) {
        const ext = extensionDe(f.name);
        if (!ALLOWED_EXTS.includes(ext)) {
          errorMsg = ext
            ? `Formato no permitido: ${ext}. Solo: ${ALLOWED_EXTS.join(", ")}`
            : `El archivo no tiene extensión. Solo: ${ALLOWED_EXTS.join(", ")}`;
          continue;
        }
        if (!ALLOWED_MIME.includes(f.type)) {
          errorMsg = `Tipo de archivo no permitido: ${f.type}`;
          continue;
        }
        if (f.size > 10 * 1024 * 1024) {
          errorMsg = "El archivo supera los 10 MB.";
          continue;
        }
        aceptados.push(f);
      }

      const combinados = [...prev, ...aceptados];
      if (combinados.length > MAX_FILES) {
        errorMsg = `Máximo ${MAX_FILES} archivos por ticket.`;
        combinados.length = MAX_FILES;
      }
      if (errorMsg) setError(errorMsg);
      return combinados;
    });
  }, []);

  const removeFile = useCallback((index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
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
    addFiles(e.dataTransfer.files);
  };

  const handleFileSelect = (e) => {
    // `e.target.files` es un FileList VIVO: limpiar `value` lo vacía a él
    // también, no solo al input. Hay que copiarlo a un arreglo ANTES de
    // limpiar, o `addFiles` recibe una lista ya vacía.
    const selected = Array.from(e.target.files || []);
    // Se limpia `value` para que volver a elegir EL MISMO archivo (típico tras
    // un error de tamaño) dispare `change` otra vez en vez de no hacer nada.
    e.target.value = "";
    addFiles(selected);
  };

  /* ── Submit ──────────────────────────────────────────────────────────── */

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (!creatorId) {
      setError("Selecciona un creador.");
      return;
    }
    if (!brandId) {
      setError("Selecciona una marca.");
      return;
    }
    if (!amount || Number(amount) <= 0) {
      setError("El monto debe ser mayor a $0.");
      return;
    }
    if (files.length === 0) {
      setError("Adjunta al menos un archivo del ticket.");
      return;
    }

    setSubmitting(true);
    try {
      await uploadTicket({
        creatorId: Number(creatorId),
        brandId: Number(brandId),
        amount: Number(amount),
        notes: notes || undefined,
        files,
      });
      setSuccessMsg("Ticket registrado exitosamente.");
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
            Registrar Nuevo Ticket
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
          {/* Creator dropdown */}
          <div>
            <label className="go-eyebrow mb-1.5 block">Creador</label>
            <select
              value={creatorId}
              onChange={(e) => setCreatorId(e.target.value)}
              className="go-select"
              required
              disabled={isCreador}
            >
              {!isCreador && <option value="">Seleccionar creador...</option>}
              {activeCreators.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} — Restante del ciclo: {formatMXN(c.cycle_remaining ?? 0)}
                </option>
              ))}
            </select>
          </div>

          {/* Brand dropdown */}
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

          {/* Amount */}
          <div>
            <label className="go-eyebrow mb-1.5 block">Monto del Ticket</label>
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
            {selectedCreator && amount > 0 && (
              <p
                className="mt-1.5 font-body text-xs"
                style={{
                  color:
                    Number(amount) > (selectedCreator.cycle_remaining ?? 0)
                      ? "var(--go-warning)"
                      : "var(--go-text-secondary)",
                }}
              >
                {Number(amount) > (selectedCreator.cycle_remaining ?? 0)
                  ? `Atención: el monto excede el restante del ciclo (${formatMXN(selectedCreator.cycle_remaining ?? 0)}). Se puede registrar igual.`
                  : `Restante del ciclo después del ticket: ${formatMXN(
                      (selectedCreator.cycle_remaining ?? 0) - Number(amount)
                    )}`}
              </p>
            )}
            {isCreador && (
              <p className="mt-1.5 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                Tu ticket quedará <strong>pendiente de validación</strong> — no descuenta presupuesto hasta que un administrador lo apruebe.
              </p>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className="go-eyebrow mb-1.5 block">
              Observaciones{" "}
              <span className="font-normal normal-case tracking-normal" style={{ color: "var(--go-text-muted)" }}>
                (opcional)
              </span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Notas sobre este gasto..."
              className="go-input resize-none"
            />
          </div>

          {/* File drop zone — acepta varios archivos, se pueden seguir agregando */}
          <div>
            <label className="go-eyebrow mb-1.5 block">
              Comprobante{" "}
              <span className="font-normal normal-case tracking-normal" style={{ color: "var(--go-text-muted)" }}>
                (puedes adjuntar más de una foto)
              </span>
            </label>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className="relative flex cursor-pointer flex-col items-center justify-center rounded-go-lg border-2 border-dashed px-6 py-4 sm:py-7 transition-colors"
              style={{
                borderColor: dragOver
                  ? "var(--go-orange)"
                  : files.length > 0
                  ? "rgba(0,163,110,0.3)"
                  : "var(--go-surface-sunken)",
                background: dragOver
                  ? "var(--go-orange-tint)"
                  : files.length > 0
                  ? "rgba(0,163,110,0.05)"
                  : "var(--go-bg)",
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              {files.length > 0 ? (
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
                    {files.length} {files.length === 1 ? "archivo" : "archivos"} listo{files.length === 1 ? "" : "s"}
                  </p>
                  <p className="mt-0.5 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                    Haz clic o arrastra para agregar más
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
                    {esMovil ? (
                      <span className="font-semibold" style={{ color: "var(--go-orange)" }}>
                        Toca para elegir uno o más archivos
                      </span>
                    ) : (
                      <>
                        Arrastra los archivos aquí o{" "}
                        <span className="font-semibold" style={{ color: "var(--go-orange)" }}>
                          haz clic para seleccionar
                        </span>
                      </>
                    )}
                  </p>
                  <p className="mt-1 font-body text-xs" style={{ color: "var(--go-text-muted)" }}>
                    PNG, JPG o PDF — Máx. 10 MB c/u
                  </p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPT}
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            {files.length > 0 && (
              <ul className="mt-2 space-y-1">
                {files.map((f, i) => (
                  <li
                    key={`${f.name}-${f.size}-${i}`}
                    className="flex items-center justify-between gap-2 rounded-go px-3 py-1.5"
                    style={{ background: "var(--go-bg)", border: "1px solid var(--go-border)" }}
                  >
                    <span
                      className="truncate font-body text-xs"
                      style={{ color: "var(--go-text-primary)" }}
                      title={f.name}
                    >
                      {f.name}{" "}
                      <span style={{ color: "var(--go-text-secondary)" }}>
                        ({(f.size / 1024).toFixed(0)} KB)
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => removeFile(i)}
                      aria-label={`Quitar ${f.name}`}
                      className="flex-shrink-0 rounded-go p-1 transition-colors hover:bg-white/5"
                      style={{ color: "var(--go-text-secondary)" }}
                    >
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/* Solo se pinta en móvil (ver CameraCaptureButton). La foto llega
                ya reescalada y en JPEG, así pasa la validación por extensión y
                MIME de upload_manager.py sin depender de lo que mande la
                cámara del teléfono. Cada toma se agrega a la lista, no la
                reemplaza. */}
            <div className="mt-2">
              <CameraCaptureButton onFile={(f) => addFiles([f])} onError={setError} />
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
                "Registrar Ticket"
              )}
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>
  );
}
