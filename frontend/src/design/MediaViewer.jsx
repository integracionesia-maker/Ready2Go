import { useCallback, useEffect, useRef, useState } from "react";
import SkeletonShimmer from "./SkeletonShimmer";
import { useMobile } from "./useMobile";

/**
 * Visor de imágenes y PDF compartido por los dos módulos.
 *
 * La regla que motiva el componente: **el modal manda, la imagen se adapta.**
 * Antes cada visor dejaba que la imagen definiera el tamaño del contenedor, así
 * que una foto de 4000px de celular producía un modal enorme y con scroll. Aquí
 * el panel tiene medida fija (pantalla completa en móvil) y la imagen entra por
 * `object-contain` dentro de un escenario de altura acotada.
 *
 * Navegación, con el mismo gesto disponible en las dos plataformas:
 *
 * | Acción   | Escritorio                  | Móvil                  |
 * |----------|-----------------------------|------------------------|
 * | Zoom     | rueda, botones +/−, tecla ± | pellizco, botones +/−  |
 * | Encuadre | arrastrar con el mouse      | arrastrar con un dedo  |
 * | Alternar | doble clic                  | doble toque            |
 * | Ajustar  | botón, tecla 0              | botón                  |
 * | Cerrar   | Esc, botón, clic afuera     | botón                  |
 *
 * Los controles de zoom flotan abajo al centro (no en el encabezado) para que
 * en móvil queden al alcance del pulgar.
 */

const ESCALA_MIN = 1;
const ESCALA_MAX = 6;
const PASO_BOTON = 0.5;
const ESCALA_DOBLE_TOQUE = 2.5;
const VISTA_INICIAL = { escala: 1, x: 0, y: 0 };

function acotar(valor, min, max) {
  return Math.min(max, Math.max(min, valor));
}

export default function MediaViewer({
  url,
  fileName = "archivo",
  // Por defecto imagen: es el caso de las fotos de Equipos, donde el backend
  // no expone el mime en el listado.
  mimeType = "image/*",
  title,
  onClose,
  /** Si descargar y previsualizar no salen de la misma ruta. */
  downloadUrl,
}) {
  const esMovil = useMobile();

  const [vista, setVista] = useState(VISTA_INICIAL);
  const [imgError, setImgError] = useState(false);

  const escenarioRef = useRef(null);
  const naturalRef = useRef(null); // { w, h } tamaño real del archivo
  const cajaRef = useRef(null); // { w, h } tamaño ya ajustado al escenario
  const punterosRef = useRef(new Map());
  const arrastreRef = useRef(null);
  const pellizcoRef = useRef(null);
  const ultimoToqueRef = useRef(0);
  // Espejo síncrono de `vista`: pointermove dispara más rápido de lo que React
  // re-renderiza, y leer el estado daría posiciones atrasadas a media arrastrada.
  const vistaRef = useRef(VISTA_INICIAL);

  const esImagen = mimeType.startsWith("image/");
  const esPdf = mimeType === "application/pdf";

  /** Recalcula el tamaño con el que la imagen entra en el escenario. */
  const medir = useCallback(() => {
    const escenario = escenarioRef.current;
    const natural = naturalRef.current;
    if (!escenario || !natural) return;
    // Nunca se agranda una imagen pequeña: mismo criterio que `max-w-full
    // max-h-full` en CSS, para que la caja calculada y la pintada coincidan.
    const ajuste = Math.min(
      escenario.clientWidth / natural.w,
      escenario.clientHeight / natural.h,
      1
    );
    cajaRef.current = { w: natural.w * ajuste, h: natural.h * ajuste };
  }, []);

  /** Acota escala y desplazamiento para que la imagen no se salga del encuadre. */
  const limitar = useCallback(({ escala, x, y }) => {
    const s = acotar(escala, ESCALA_MIN, ESCALA_MAX);
    const caja = cajaRef.current;
    const escenario = escenarioRef.current;
    if (!caja || !escenario) return { escala: s, x: 0, y: 0 };
    const maxX = Math.max(0, (caja.w * s - escenario.clientWidth) / 2);
    const maxY = Math.max(0, (caja.h * s - escenario.clientHeight) / 2);
    return { escala: s, x: acotar(x, -maxX, maxX), y: acotar(y, -maxY, maxY) };
  }, []);

  const aplicar = useCallback(
    (siguiente) => {
      const v = limitar(siguiente);
      vistaRef.current = v;
      setVista(v);
    },
    [limitar]
  );

  const ajustar = useCallback(() => aplicar(VISTA_INICIAL), [aplicar]);

  /** Zoom conservando bajo el cursor/pellizco el punto que se está mirando. */
  const zoomHacia = useCallback(
    (escalaDestino, centro = { x: 0, y: 0 }) => {
      const v = vistaRef.current;
      const s = acotar(escalaDestino, ESCALA_MIN, ESCALA_MAX);
      const factor = s / v.escala;
      aplicar({
        escala: s,
        x: centro.x + (v.x - centro.x) * factor,
        y: centro.y + (v.y - centro.y) * factor,
      });
    },
    [aplicar]
  );

  /** Coordenadas de un evento relativas al centro del escenario. */
  const centroDe = useCallback((clientX, clientY) => {
    const escenario = escenarioRef.current;
    if (!escenario) return { x: 0, y: 0 };
    const r = escenario.getBoundingClientRect();
    return { x: clientX - (r.left + r.width / 2), y: clientY - (r.top + r.height / 2) };
  }, []);

  // Rueda del mouse. Listener nativo y no pasivo a propósito: React registra
  // `wheel` como pasivo en la raíz, así que un onWheel de JSX no puede
  // preventDefault() y la página seguiría haciendo scroll bajo el modal.
  useEffect(() => {
    const escenario = escenarioRef.current;
    if (!escenario || !esImagen) return undefined;
    const alGirar = (e) => {
      e.preventDefault();
      const v = vistaRef.current;
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      zoomHacia(v.escala * factor, centroDe(e.clientX, e.clientY));
    };
    escenario.addEventListener("wheel", alGirar, { passive: false });
    return () => escenario.removeEventListener("wheel", alGirar);
  }, [esImagen, zoomHacia, centroDe]);

  // Reajusta al rotar el teléfono o cambiar el tamaño de la ventana.
  useEffect(() => {
    const escenario = escenarioRef.current;
    if (!escenario || typeof ResizeObserver === "undefined") return undefined;
    const observador = new ResizeObserver(() => {
      medir();
      aplicar(vistaRef.current);
    });
    observador.observe(escenario);
    return () => observador.disconnect();
  }, [medir, aplicar]);

  // Teclado. Escape cierra incluso sobre un PDF; el resto solo aplica a imagen.
  useEffect(() => {
    const alPulsar = (e) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (!esImagen) return;
      const v = vistaRef.current;
      const paso = 40;
      if (e.key === "+" || e.key === "=") zoomHacia(v.escala + PASO_BOTON);
      else if (e.key === "-" || e.key === "_") zoomHacia(v.escala - PASO_BOTON);
      else if (e.key === "0") ajustar();
      else if (e.key === "ArrowLeft") aplicar({ ...v, x: v.x + paso });
      else if (e.key === "ArrowRight") aplicar({ ...v, x: v.x - paso });
      else if (e.key === "ArrowUp") aplicar({ ...v, y: v.y + paso });
      else if (e.key === "ArrowDown") aplicar({ ...v, y: v.y - paso });
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [esImagen, onClose, zoomHacia, ajustar, aplicar]);

  // Reinicia el encuadre al cambiar de archivo.
  useEffect(() => {
    naturalRef.current = null;
    cajaRef.current = null;
    vistaRef.current = VISTA_INICIAL;
    setVista(VISTA_INICIAL);
    setImgError(false);
  }, [url]);

  const alCargarImagen = (e) => {
    naturalRef.current = { w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight };
    medir();
    aplicar(VISTA_INICIAL);
  };

  const alternarZoom = useCallback(
    (clientX, clientY) => {
      if (vistaRef.current.escala > 1.05) ajustar();
      else zoomHacia(ESCALA_DOBLE_TOQUE, centroDe(clientX, clientY));
    },
    [ajustar, zoomHacia, centroDe]
  );

  const alBajarPuntero = (e) => {
    if (!esImagen) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    punterosRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (punterosRef.current.size === 1) {
      arrastreRef.current = { x: e.clientX, y: e.clientY, vista: vistaRef.current };
    } else if (punterosRef.current.size === 2) {
      arrastreRef.current = null;
      const [a, b] = [...punterosRef.current.values()];
      pellizcoRef.current = {
        dist: Math.hypot(a.x - b.x, a.y - b.y),
        escala: vistaRef.current.escala,
      };
    }
  };

  const alMoverPuntero = (e) => {
    if (!punterosRef.current.has(e.pointerId)) return;
    punterosRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    const pellizco = pellizcoRef.current;
    if (punterosRef.current.size >= 2 && pellizco && pellizco.dist > 0) {
      const [a, b] = [...punterosRef.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      zoomHacia(
        pellizco.escala * (dist / pellizco.dist),
        centroDe((a.x + b.x) / 2, (a.y + b.y) / 2)
      );
      return;
    }

    const arrastre = arrastreRef.current;
    if (!arrastre) return;
    aplicar({
      escala: arrastre.vista.escala,
      x: arrastre.vista.x + (e.clientX - arrastre.x),
      y: arrastre.vista.y + (e.clientY - arrastre.y),
    });
  };

  const alSoltarPuntero = (e) => {
    const eraToque = e.pointerType === "touch";
    const seArrastro =
      arrastreRef.current &&
      Math.hypot(e.clientX - arrastreRef.current.x, e.clientY - arrastreRef.current.y) > 8;

    punterosRef.current.delete(e.pointerId);
    if (punterosRef.current.size < 2) pellizcoRef.current = null;
    if (punterosRef.current.size === 0) {
      arrastreRef.current = null;
    } else {
      // Queda un dedo tras soltar el otro: se rebasa el arrastre para que la
      // imagen no salte por seguir midiendo contra el dedo que ya no está.
      const [p] = [...punterosRef.current.values()];
      arrastreRef.current = { x: p.x, y: p.y, vista: vistaRef.current };
    }

    // Doble toque: el `dblclick` sintético no es fiable con touch-action:none,
    // así que se detecta a mano. Un arrastre nunca cuenta como toque.
    if (eraToque && !seArrastro) {
      const ahora = e.timeStamp;
      if (ahora - ultimoToqueRef.current < 300) {
        alternarZoom(e.clientX, e.clientY);
        ultimoToqueRef.current = 0;
      } else {
        ultimoToqueRef.current = ahora;
      }
    }
  };

  const puedeAlejar = vista.escala > ESCALA_MIN;
  const puedeAcercar = vista.escala < ESCALA_MAX;

  const botonZoom = "flex h-9 w-9 items-center justify-center rounded-go text-base transition-colors disabled:opacity-30";

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center ${esMovil ? "" : "p-4"}`}
      style={{ background: "var(--go-overlay)" }}
      onClick={onClose}
    >
      <div
        className={`glass relative flex flex-col overflow-hidden ${
          esMovil
            ? "h-full w-full rounded-none"
            : "h-[min(760px,88vh)] w-[min(1100px,92vw)]"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="veil flex h-full flex-col">
          {/* ── Encabezado ──────────────────────────────────────────── */}
          <div
            className="flex flex-shrink-0 items-center justify-between gap-3 px-4 py-3 sm:px-6 sm:py-4"
            style={{ borderBottom: "1px solid var(--go-border)" }}
          >
            <h2
              className="truncate font-display text-sm font-bold uppercase tracking-[0.06em] sm:text-base"
              style={{ color: "var(--go-text-primary)" }}
              title={title || fileName}
            >
              {title || fileName}
            </h2>
            <div className="flex flex-shrink-0 items-center gap-2">
              {url && (
                <a
                  href={downloadUrl || url}
                  download={fileName}
                  className="btn-go-ghost px-2.5 py-1.5 text-xs"
                  title={`Descargar ${fileName}`}
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                    />
                  </svg>
                  <span className="hidden sm:inline">Descargar</span>
                </a>
              )}
              {/* type="button" explícito: el visor se monta en el árbol donde
                  lo pone quien lo llama (no en un portal), así que si algún día
                  cae dentro de un <form>, un botón sin type lo enviaría al
                  cerrarse. */}
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar"
                className="rounded-go p-1.5 transition-colors hover:bg-white/5"
                style={{ color: "var(--go-text-secondary)" }}
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* ── Escenario ───────────────────────────────────────────── */}
          <div
            ref={escenarioRef}
            className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden"
            style={{
              background: "var(--go-bg)",
              // Sin esto el navegador se queda con el pellizco y el arrastre y
              // el visor no recibe ningún gesto en móvil.
              touchAction: esImagen ? "none" : "auto",
              cursor: !esImagen ? "default" : vista.escala > 1 ? "grab" : "zoom-in",
            }}
            onPointerDown={alBajarPuntero}
            onPointerMove={alMoverPuntero}
            onPointerUp={alSoltarPuntero}
            onPointerCancel={alSoltarPuntero}
            onDoubleClick={(e) => esImagen && alternarZoom(e.clientX, e.clientY)}
          >
            {!url && <SkeletonShimmer className="h-full w-full" />}

            {url && esImagen && !imgError && (
              <img
                src={url}
                alt={title || fileName}
                onLoad={alCargarImagen}
                onError={() => setImgError(true)}
                draggable={false}
                className="max-h-full max-w-full select-none object-contain"
                style={{
                  transform: `translate(${vista.x}px, ${vista.y}px) scale(${vista.escala})`,
                  // Sin transición mientras se arrastra o se pellizca: el
                  // retardo se siente como lag en el dedo.
                  transition: arrastreRef.current || pellizcoRef.current ? "none" : "transform 120ms",
                }}
              />
            )}

            {url && esImagen && imgError && (
              <p className="px-6 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                No se pudo cargar la imagen. Es posible que el archivo ya no exista.
              </p>
            )}

            {url && esPdf && (
              <iframe
                title={fileName}
                src={url}
                className="h-full w-full"
                style={{ border: "none" }}
              />
            )}

            {url && !esImagen && !esPdf && (
              <p className="px-6 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                Este tipo de archivo no tiene vista previa. Usa Descargar para abrirlo.
              </p>
            )}

            {/* ── Controles flotantes ───────────────────────────────── */}
            {url && esImagen && !imgError && (
              <div
                className="glass absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1 px-2 py-1.5"
                style={{ background: "color-mix(in srgb, var(--veil-bg) 88%, transparent)" }}
                onPointerDown={(e) => e.stopPropagation()}
                onDoubleClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  onClick={() => zoomHacia(vista.escala - PASO_BOTON)}
                  disabled={!puedeAlejar}
                  className={botonZoom}
                  style={{ color: "var(--go-text-secondary)" }}
                  title="Alejar"
                  aria-label="Alejar"
                >
                  −
                </button>
                <span
                  className="min-w-[3.25rem] text-center font-mono text-xs tabular-nums"
                  style={{ color: "var(--go-text-secondary)" }}
                >
                  {Math.round(vista.escala * 100)}%
                </span>
                <button
                  type="button"
                  onClick={() => zoomHacia(vista.escala + PASO_BOTON)}
                  disabled={!puedeAcercar}
                  className={botonZoom}
                  style={{ color: "var(--go-text-secondary)" }}
                  title="Acercar"
                  aria-label="Acercar"
                >
                  +
                </button>
                <button
                  type="button"
                  onClick={ajustar}
                  disabled={!puedeAlejar}
                  className={`${botonZoom} w-auto px-2.5`}
                  style={{ color: "var(--go-text-secondary)" }}
                  title="Ajustar a la pantalla (tecla 0)"
                  aria-label="Ajustar a la pantalla"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 9V4.5M9 9H4.5M15 9h4.5M15 9V4.5M15 15v4.5M15 15h4.5M9 15H4.5M9 15v4.5"
                    />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
