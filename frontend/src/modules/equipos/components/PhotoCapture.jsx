import { useEffect, useRef, useState } from "react";
import { mediaUrl } from "../api";

const MAX_DIM = 900;
const QUALITY = 0.72;
const MAX_BYTES = 3 * 1024 * 1024;

async function compressImage(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DIM / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale);
  const h = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  canvas.getContext("2d").drawImage(bitmap, 0, 0, w, h);
  bitmap.close?.();
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", QUALITY));
}

/**
 * Una foto, un slot (frente/atrás de un equipo). Compresión en cliente a
 * 900px/calidad 0.72 (canvas), preview local con `URL.createObjectURL`
 * (nunca base64 en estado), y reintento por foto sin re-pedir el archivo —
 * el Blob comprimido se queda en un ref hasta que la subida realmente
 * funcione, así un 413 en OTRA foto del mismo préstamo nunca tira esta.
 */
export default function PhotoCapture({ label, existingMediaId, onUpload }) {
  const [preview, setPreview] = useState(null);
  const [estado, setEstado] = useState(existingMediaId ? "listo" : "vacio"); // vacio | comprimiendo | subiendo | listo | error
  const [error, setError] = useState(null);
  const [existingUrl, setExistingUrl] = useState(null);
  const blobRef = useRef(null);
  const inputRef = useRef(null);

  // mediaUrl() del barril de Equipos SIEMPRE es async (el mock resuelve un
  // import() dinámico; el real, aunque su implementación es síncrona, se
  // envuelve igual en el dispatcher) — nunca se puede usar directo como
  // `src`, hay que esperarlo primero.
  useEffect(() => {
    let cancelado = false;
    if (existingMediaId && !preview) {
      mediaUrl(existingMediaId, { tamano: "thumb" }).then((url) => {
        if (!cancelado) setExistingUrl(url);
      });
    }
    return () => {
      cancelado = true;
    };
  }, [existingMediaId, preview]);

  async function handleFile(file) {
    if (!file) return;
    setError(null);
    setEstado("comprimiendo");
    try {
      const compressed = await compressImage(file);
      if (compressed.size > MAX_BYTES) {
        setEstado("error");
        setError(`La foto sigue pesando ${(compressed.size / 1024 / 1024).toFixed(1)} MB tras comprimir — el límite es 3 MB. Intenta con otra foto.`);
        return;
      }
      blobRef.current = compressed;
      setPreview(URL.createObjectURL(compressed));
      await subir();
    } catch (e) {
      setEstado("error");
      setError(e.message);
    }
  }

  async function subir() {
    if (!blobRef.current) return;
    setEstado("subiendo");
    setError(null);
    try {
      await onUpload(blobRef.current);
      setEstado("listo");
    } catch (e) {
      setEstado("error");
      setError(e.detail || e.message);
    }
  }

  const yaSubida = estado === "listo";

  return (
    <div className="flex flex-col gap-2">
      <p className="go-eyebrow">{label}</p>
      <div
        className="flex h-32 items-center justify-center overflow-hidden rounded-go border"
        style={{ borderColor: "var(--go-border)", background: "var(--go-surface)" }}
      >
        {preview ? (
          <img src={preview} alt={label} className="h-full w-full object-cover" />
        ) : existingUrl ? (
          <img src={existingUrl} alt={label} className="h-full w-full object-cover" />
        ) : (
          <span className="font-body text-xs" style={{ color: "var(--go-text-muted)" }}>
            Sin foto
          </span>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {estado === "comprimiendo" && (
        <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          Comprimiendo...
        </p>
      )}
      {estado === "subiendo" && (
        <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          Subiendo...
        </p>
      )}
      {estado === "error" && (
        <div className="space-y-1.5">
          <p className="font-body text-xs" style={{ color: "var(--go-error)" }}>
            {error}
          </p>
          {blobRef.current && (
            <button type="button" onClick={subir} className="btn-go-ghost text-xs px-3 py-1">
              Reintentar subida
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={estado === "comprimiendo" || estado === "subiendo"}
        className="btn-go-ghost text-xs px-3 py-1.5"
      >
        {yaSubida ? "Reemplazar foto" : "Tomar / elegir foto"}
      </button>
    </div>
  );
}
