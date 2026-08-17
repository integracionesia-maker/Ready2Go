import { useRef, useState } from "react";
import { comprimirImagen } from "./imagen";
import { useMobile } from "./useMobile";

/**
 * Botón "Tomar foto" para las vistas que suben evidencia. **Solo se pinta en
 * móvil**: en escritorio `capture` se ignora y quedaría un botón que abre el
 * mismo diálogo que el de al lado.
 *
 * Va aparte del input de archivos a propósito. `capture` en un input lo vuelve
 * exclusivamente de cámara: si se le agregara al input que ya existe,
 * desaparecería la posibilidad de subir un PDF o una foto de la galería. Dos
 * entradas separadas es la única forma de ofrecer las dos cosas.
 *
 * `capture` NO exige contexto seguro: delega en la app de cámara del sistema.
 * El que exige HTTPS es `getUserMedia()` (vista previa dentro de la página),
 * que aquí no se usa.
 */
export default function CameraCaptureButton({
  onFile,
  /** Se llama con un mensaje ya legible si la imagen no se pudo procesar. */
  onError,
  label = "Tomar foto",
  disabled = false,
  /**
   * Opciones para `comprimirImagen`, o `false` para entregar el archivo tal
   * cual (lo usa Equipos, que comprime con sus propios parámetros).
   */
  comprimir = {},
  className = "btn-go-ghost w-full justify-center text-sm",
}) {
  const esMovil = useMobile();
  const inputRef = useRef(null);
  const [procesando, setProcesando] = useState(false);

  if (!esMovil) return null;

  const alElegir = async (e) => {
    const archivo = e.target.files?.[0];
    // Se limpia el input ANTES de procesar. La cámara de Android suele
    // entregar siempre el mismo nombre (`image.jpg`), así que `value` no
    // cambia entre dos fotos y el evento `change` no se vuelve a disparar: el
    // botón se sentiría muerto al segundo intento.
    e.target.value = "";
    if (!archivo) return;

    if (comprimir === false) {
      onFile(archivo);
      return;
    }

    setProcesando(true);
    try {
      onFile(await comprimirImagen(archivo, comprimir));
    } catch (err) {
      if (onError) onError(err.message);
    } finally {
      setProcesando(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || procesando}
        className={className}
      >
        <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
          />
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
        </svg>
        {procesando ? "Procesando..." : label}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={alElegir}
      />
    </>
  );
}
