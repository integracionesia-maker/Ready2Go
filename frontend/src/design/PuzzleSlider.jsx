import { useCallback, useRef, useState } from "react";

/**
 * Rompecabezas casero de "arrastra la pieza a su lugar" para el
 * auto-desbloqueo de cuenta (ver `docs/presupuestos/auth/`). Sin imagenes ni
 * dependencias externas: el objetivo (`targetPercent`) llega del backend y se
 * dibuja como una muesca visible en la pista — igual que un slider-captcha
 * real, el número nunca es el secreto, la interacción sí lo es.
 *
 * No es defensa seria contra un navegador automatizado de verdad; es fricción
 * suficiente para separar un typo humano de un script de una sola llamada, y
 * requiere que el backend vea un arrastre real (ver `security.py`).
 *
 * `onComplete(posicionPercent, trail)` se llama al soltar. El padre decide si
 * fue correcto (la respuesta viene del servidor, nunca se evalúa aquí).
 */
export default function PuzzleSlider({ targetPercent, onComplete, disabled = false }) {
  const pistaRef = useRef(null);
  const [posicion, setPosicion] = useState(0);
  const [arrastrando, setArrastrando] = useState(false);
  const trailRef = useRef([]);
  const inicioRef = useRef(0);

  const percentDesdeEvento = useCallback((clientX) => {
    const pista = pistaRef.current;
    if (!pista) return 0;
    const rect = pista.getBoundingClientRect();
    const crudo = ((clientX - rect.left) / rect.width) * 100;
    return Math.max(0, Math.min(100, crudo));
  }, []);

  const empezar = (clientX, pointerId, target) => {
    if (disabled) return;
    target.setPointerCapture?.(pointerId);
    inicioRef.current = performance.now();
    trailRef.current = [{ x: percentDesdeEvento(clientX), t: 0 }];
    setArrastrando(true);
  };

  const mover = (clientX) => {
    if (!arrastrando) return;
    const p = percentDesdeEvento(clientX);
    setPosicion(p);
    trailRef.current.push({ x: p, t: performance.now() - inicioRef.current });
  };

  const soltar = () => {
    if (!arrastrando) return;
    setArrastrando(false);
    onComplete(posicion, trailRef.current);
  };

  const conTeclado = (e) => {
    if (disabled) return;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      const delta = e.key === "ArrowLeft" ? -2 : 2;
      const ahora = performance.now();
      if (trailRef.current.length === 0) {
        inicioRef.current = ahora;
        trailRef.current.push({ x: posicion, t: 0 });
      }
      const nueva = Math.max(0, Math.min(100, posicion + delta));
      setPosicion(nueva);
      trailRef.current.push({ x: nueva, t: ahora - inicioRef.current });
    } else if (e.key === "Enter" && trailRef.current.length > 1) {
      onComplete(posicion, trailRef.current);
    }
  };

  return (
    <div className="select-none">
      <p className="go-eyebrow mb-2">Arrastra la pieza hasta el hueco</p>
      <div
        ref={pistaRef}
        className="relative h-14 w-full touch-none rounded-go border"
        style={{ background: "var(--go-surface-sunken)", borderColor: "var(--go-border)" }}
      >
        {/* Muesca objetivo: visible a propósito, es lo que se ve en un slider-captcha real */}
        <div
          className="pointer-events-none absolute top-1/2 h-9 w-9 -translate-y-1/2 rounded-full border-2 border-dashed"
          style={{ left: `calc(${targetPercent}% - 18px)`, borderColor: "var(--go-orange)" }}
          aria-hidden="true"
        />
        <div
          role="slider"
          tabIndex={disabled ? -1 : 0}
          aria-label="Posición de la pieza del rompecabezas"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(posicion)}
          aria-disabled={disabled}
          onKeyDown={conTeclado}
          onPointerDown={(e) => empezar(e.clientX, e.pointerId, e.currentTarget)}
          onPointerMove={(e) => mover(e.clientX)}
          onPointerUp={soltar}
          onPointerCancel={() => setArrastrando(false)}
          className="absolute top-1/2 h-10 w-10 -translate-y-1/2 cursor-grab rounded-full shadow-lg outline-none active:cursor-grabbing"
          style={{
            left: `calc(${posicion}% - 20px)`,
            background: "var(--go-orange)",
            boxShadow: arrastrando ? "0 0 0 4px var(--go-orange-tint)" : undefined,
          }}
        >
          <svg viewBox="0 0 24 24" className="h-full w-full p-2.5" fill="none" stroke="white" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 5l-5 7 5 7M16 5l5 7-5 7" />
          </svg>
        </div>
      </div>
    </div>
  );
}
