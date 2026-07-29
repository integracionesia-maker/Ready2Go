import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

const MAX_BYTES = 250 * 1024;
// Diagonal mínima del bounding box de los trazos, en px CSS: descarta un
// "casi vacío" (un tap o una rayita de 3px) sin exigir una firma elaborada.
const MIN_DIAGONAL = 40;

/**
 * Firma sobre <canvas>, Pointer Events (funciona con mouse/touch/stylus sin
 * duplicar handlers), escalado por devicePixelRatio para que no se vea
 * borrosa en pantallas retina. Deshacer por trazo completo. La detección de
 * "vacío" es real: mide el bounding box de los trazos, no un pixel-scan del
 * canvas ni un simple "¿hubo algún trazo?" (un tap cuenta como trazo pero no
 * como firma — hallazgo 8).
 *
 * API imperativa (`ref.current.getBlob()` / `.isEmpty()`) en vez de un
 * `onChange` con el dato — nunca se guarda base64 ni el Blob en el estado
 * de React; el wizard lo pide bajo demanda justo antes de subir.
 */
const SignaturePad = forwardRef(function SignaturePad(_props, ref) {
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const strokesRef = useRef([]); // Array<Array<{x,y}>> en coords CSS (no de dispositivo)
  const currentStrokeRef = useRef(null);
  const [hasContent, setHasContent] = useState(false);
  const [drawing, setDrawing] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = 2.2;
    ctx.strokeStyle = "#1a1a1a";
    ctxRef.current = ctx;
  }, []);

  function redrawAll() {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
    for (const stroke of strokesRef.current) {
      if (stroke.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(stroke[0].x, stroke[0].y);
      for (const p of stroke.slice(1)) ctx.lineTo(p.x, p.y);
      ctx.stroke();
    }
  }

  function computeHasContent() {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    let totalPoints = 0;
    for (const stroke of strokesRef.current) {
      totalPoints += stroke.length;
      for (const p of stroke) {
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      }
    }
    if (totalPoints < 2) return false;
    return Math.hypot(maxX - minX, maxY - minY) >= MIN_DIAGONAL;
  }

  function posFromEvent(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function handlePointerDown(e) {
    e.preventDefault();
    canvasRef.current.setPointerCapture(e.pointerId);
    currentStrokeRef.current = [posFromEvent(e)];
    setDrawing(true);
  }

  function handlePointerMove(e) {
    if (!currentStrokeRef.current) return;
    const pos = posFromEvent(e);
    const stroke = currentStrokeRef.current;
    const ctx = ctxRef.current;
    const prev = stroke[stroke.length - 1];
    ctx.beginPath();
    ctx.moveTo(prev.x, prev.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    stroke.push(pos);
  }

  function finishStroke() {
    if (!currentStrokeRef.current) return;
    strokesRef.current.push(currentStrokeRef.current);
    currentStrokeRef.current = null;
    setDrawing(false);
    setHasContent(computeHasContent());
  }

  function handleUndo() {
    strokesRef.current.pop();
    redrawAll();
    setHasContent(computeHasContent());
  }

  function handleClear() {
    strokesRef.current = [];
    redrawAll();
    setHasContent(false);
  }

  useImperativeHandle(ref, () => ({
    isEmpty: () => !computeHasContent(),
    // Nunca base64 en el estado (hallazgo 8): se exporta a Blob bajo demanda,
    // el wizard no guarda una copia serializada de la firma en ningún lado.
    async getBlob() {
      const canvas = canvasRef.current;
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
      if (blob && blob.size > MAX_BYTES) {
        throw new Error(`La firma pesa ${(blob.size / 1024).toFixed(0)} KB — el límite es 250 KB. Simplifica el trazo.`);
      }
      return blob;
    },
  }));

  return (
    <div>
      <canvas
        ref={canvasRef}
        style={{ width: "100%", height: "160px", touchAction: "none", background: "#fff", borderRadius: "var(--go-radius)" }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishStroke}
        onPointerLeave={drawing ? finishStroke : undefined}
      />
      <div className="mt-2 flex items-center justify-between">
        <p className="font-body text-xs" style={{ color: hasContent ? "var(--go-success)" : "var(--go-text-muted)" }}>
          {hasContent ? "Firma capturada" : "Dibuja tu firma arriba"}
        </p>
        <div className="flex gap-2">
          <button type="button" onClick={handleUndo} className="btn-go-ghost text-xs px-3 py-1">
            Deshacer
          </button>
          <button type="button" onClick={handleClear} className="btn-go-ghost text-xs px-3 py-1">
            Borrar
          </button>
        </div>
      </div>
    </div>
  );
});

export default SignaturePad;
