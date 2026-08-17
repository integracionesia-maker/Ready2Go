import { useEffect, useRef, useState } from "react";
import { CameraCaptureButton, MediaViewer, comprimirImagen } from "@/design";
import { mediaUrl } from "../api";

// 900px/0.72 son los parámetros de este módulo, más agresivos que los de
// `comprimirImagen` por defecto (1600/0.85): aquí se fotografían objetos, no
// texto que alguien tenga que leer para validar un monto.
const MAX_DIM = 900;
const QUALITY = 0.72;
const MAX_BYTES = 3 * 1024 * 1024;

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
  // Ampliación de la foto. El recuadro mide 128px y va recortado
  // (`object-cover`): sin esto no hay forma de comprobar si la foto salió
  // movida antes de mandarla, que es justo lo que se está revisando aquí.
  const [ampliada, setAmpliada] = useState(false);
  const [urlCompleta, setUrlCompleta] = useState(null);
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

  // Los objectURL del preview no se revocaban: cada "Reemplazar foto" dejaba el
  // Blob anterior retenido en memoria hasta recargar la página. El cleanup corre
  // antes del siguiente efecto y al desmontar, así que libera el que se va.
  useEffect(() => {
    if (!preview) return undefined;
    return () => URL.revokeObjectURL(preview);
  }, [preview]);

  async function handleFile(file) {
    if (!file) return;
    setError(null);
    setEstado("comprimiendo");
    try {
      const compressed = await comprimirImagen(file, {
        maxDim: MAX_DIM,
        calidad: QUALITY,
      });
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
  const ocupado = estado === "comprimiendo" || estado === "subiendo";

  return (
    <div className="flex flex-col gap-2">
      <p className="go-eyebrow">{label}</p>
      <div
        className="flex h-32 items-center justify-center overflow-hidden rounded-go border"
        style={{
          borderColor: "var(--go-border)",
          background: "var(--go-surface)",
          cursor: preview || existingUrl ? "zoom-in" : "default",
        }}
        onClick={() => {
          if (!preview && !existingUrl) return;
          // El recuadro usa la miniatura de 96px; para ampliar hace falta el
          // original. Si la foto es de esta sesión, el objectURL local ya es
          // la imagen completa.
          if (preview) setUrlCompleta(preview);
          else if (!urlCompleta && existingMediaId) {
            mediaUrl(existingMediaId).then(setUrlCompleta);
          }
          setAmpliada(true);
        }}
        role={preview || existingUrl ? "button" : undefined}
        tabIndex={preview || existingUrl ? 0 : undefined}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && (preview || existingUrl)) {
            e.preventDefault();
            e.currentTarget.click();
          }
        }}
        aria-label={preview || existingUrl ? `Ampliar ${label}` : undefined}
      >
        {preview ? (
          <img src={preview} alt={label} className="h-full w-full object-cover" />
        ) : existingUrl ? (
          // I8 lote 3 (hallazgo): si el archivo ya no existe en el servidor
          // (borrado, id viejo), sin este `onError` quedaba el ícono roto
          // nativo del navegador dentro de la caja — se cae al mismo "Sin
          // foto" de abajo.
          <img
            src={existingUrl}
            alt={label}
            className="h-full w-full object-cover"
            onError={() => setExistingUrl(null)}
          />
        ) : (
          <span className="font-body text-xs" style={{ color: "var(--go-text-muted)" }}>
            Sin foto
          </span>
        )}
      </div>

      {/* Sin `capture`: este input es el de "elegir archivo". Antes lo llevaba,
          lo que en móvil dejaba la cámara como ÚNICA vía — no se podía subir una
          foto que ya estuviera en la galería. La cámara ahora es el botón
          aparte de abajo. */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files[0];
          e.target.value = "";
          handleFile(f);
        }}
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

      <div className="flex flex-col gap-2">
        {/* Solo aparece en móvil. `comprimir={false}`: la compresión la hace
            handleFile con los parámetros de este módulo, no los del util. */}
        <CameraCaptureButton
          label={yaSubida ? "Volver a tomar" : "Tomar foto"}
          onFile={handleFile}
          onError={(m) => {
            setEstado("error");
            setError(m);
          }}
          comprimir={false}
          disabled={ocupado}
          className="btn-go-ghost justify-center text-xs px-3 py-1.5"
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={ocupado}
          className="btn-go-ghost justify-center text-xs px-3 py-1.5"
        >
          {yaSubida ? "Elegir otro archivo" : "Elegir archivo"}
        </button>
      </div>

      {ampliada && (
        <MediaViewer
          url={urlCompleta}
          fileName={`${label}.jpg`}
          mimeType="image/*"
          title={label}
          onClose={() => setAmpliada(false)}
        />
      )}
    </div>
  );
}
