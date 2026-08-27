import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Minijuego del panel "acerca de" (`AboutPanel.jsx`): un Flappy Bird donde el
 * pájaro es un **megáfono** — el icono de marketing por antonomasia. Se dibuja
 * en canvas con primitivas, sin assets: no engorda el bundle y escala solo.
 *
 * Cuatro decisiones que no son obvias:
 *
 * 1. **Espacio y flechas se capturan en `window` con `capture: true` y
 *    `preventDefault`.** GlassModal enfoca el botón de cerrar al abrirse, así
 *    que sin eso la primera pulsación de Espacio activaría ese botón y cerraría
 *    el panel en vez de aletear. El `preventDefault` corta también el scroll
 *    del contenedor, que en un modal con `overflow-y-auto` da un salto muy raro.
 *
 * 2. **No arranca solo.** Espera el primer toque. Si arrancara al montar, el
 *    megáfono se estrellaría mientras la persona todavía está leyendo los
 *    créditos, y el panel abriría en estado "perdiste".
 *
 * 3. **`pintar` se declara antes del efecto de tamaño y ese efecto lo llama.**
 *    Asignar `canvas.width` BORRA el canvas, y el callback inicial del
 *    ResizeObserver llega DESPUÉS del primer pintado: sin ese repintado el panel
 *    abría con el canvas en un color plano, sin megáfono ni suelo. El orden
 *    importa además por la TDZ — usar `pintar` en el array de dependencias de un
 *    efecto declarado más arriba revienta en render con ReferenceError.
 *
 * 4. **Los colores salen de las variables CSS del tema**, no hardcodeados, y se
 *    releen cuando cambia `data-theme` en `<html>`. Un canvas con colores fijos
 *    se ve roto en cuanto alguien usa el interruptor de tema.
 */

const ALTO = 180;            // alto lógico del mundo; el ancho lo da el contenedor
// Gravedad e impulso están atados: la cadencia de aleteo que mantiene el vuelo
// plano es ~2*|IMPULSO|/GRAVEDAD frames. Con 0.42/-6 salían ~460 ms, demasiado
// flotante — a un ritmo humano normal (~320 ms) el megáfono trepaba 40 px por
// ciclo y se estrellaba en el techo en dos aleteos. Con 0.55/-5.6 la cadencia
// neutra cae en ~320 ms, que es la que sale sola al jugar.
const GRAVEDAD = 0.55;
const IMPULSO = -5.6;
const CAIDA_MAX = 7;
const AVATAR_X = 62;         // el megáfono no avanza: el mundo se mueve hacia él
const RADIO = 11;            // radio de colisión del megáfono
const BARRA_ANCHO = 26;
const HUECO = 66;
const VELOCIDAD = 1.9;
const SEPARACION = 132;      // distancia horizontal entre barras
const MARGEN_HUECO = 14;     // el hueco nunca pega a los bordes
const SUELO = 3;
const CLAVE_RECORD = "gocreate-flappy-record";
// Las constantes de arriba están calibradas a 60 fps. La física se normaliza por
// tiempo transcurrido, NO por frame: atarla al frame hace que el juego corra al
// doble en una pantalla de 120 Hz (las de los Mac, justo a donde migra esto) y a
// un quinto cuando el navegador limita el rAF — medido: 24 px/s en vez de 114.
const MS_POR_FRAME = 1000 / 60;
// Techo del salto temporal: tras un cambio de pestaña o un tirón, un dt enorme
// teletransportaría el megáfono al otro lado de una barra sin detectar el choque.
const DT_MAX = 2.5;

function leerRecord() {
  // localStorage puede lanzar (ventana privada, cookies bloqueadas), no solo
  // devolver null: va envuelto.
  try {
    return Number(window.localStorage.getItem(CLAVE_RECORD)) || 0;
  } catch {
    return 0;
  }
}

function guardarRecord(valor) {
  try {
    window.localStorage.setItem(CLAVE_RECORD, String(valor));
  } catch {
    /* sin persistencia; el juego sigue funcionando igual */
  }
}

function leerTema(elemento) {
  const css = getComputedStyle(elemento);
  const v = (nombre, respaldo) => css.getPropertyValue(nombre).trim() || respaldo;
  // El fondo y las barras NO pueden salir del mismo token: en tema oscuro
  // `--go-surface-sunken` y `--go-border` son ambos `--go-dark-600`, así que las
  // barras se pintaban del color del fondo y solo se veían sus labios naranjas
  // flotando. Fondo = la superficie más honda; barras = la elevada, que sí
  // contrasta contra ella en los dos temas.
  return {
    fondo: v("--go-bg", "#09090b"),
    barra: v("--go-surface-raised", "#18181b"),
    borde: v("--go-border", "#27272a"),
    acento: v("--go-orange", "#fb670b"),
    texto: v("--go-text-primary", "#fafafa"),
  };
}

/** El megáfono, apuntando a la derecha, inclinado según la velocidad. */
function dibujarMegafono(ctx, x, y, inclinacion, color) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(inclinacion);

  ctx.fillStyle = color;
  ctx.beginPath();                  // bocina
  ctx.moveTo(-9, -6);
  ctx.lineTo(8, -12);
  ctx.lineTo(8, 12);
  ctx.lineTo(-9, 6);
  ctx.closePath();
  ctx.fill();

  ctx.fillRect(-13, -3.5, 5, 7);    // mango

  ctx.strokeStyle = color;           // ondas de sonido
  ctx.lineWidth = 1.6;
  ctx.globalAlpha = 0.7;
  ctx.beginPath();
  ctx.arc(11, 0, 5, -0.9, 0.9);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(11, 0, 9, -0.8, 0.8);
  ctx.stroke();

  ctx.restore();
}

export default function FlappyMkt() {
  const canvasRef = useRef(null);
  const contenedorRef = useRef(null);
  const temaRef = useRef(null);
  const frameRef = useRef(0);

  // El estado del juego vive en un ref, no en useState: se muta 60 veces por
  // segundo y un re-render por frame tiraría el rendimiento del modal entero.
  // Solo el marcador y la fase suben a React, y cambian pocas veces.
  const juego = useRef({ ancho: 320, y: ALTO / 2, vy: 0, barras: [], puntos: 0 });

  const [fase, setFase] = useState("listo");   // listo | jugando | perdio
  const [puntos, setPuntos] = useState(0);
  const [record, setRecord] = useState(0);

  useEffect(() => setRecord(leerRecord()), []);

  // ── Pintado ───────────────────────────────────────────────────────────────
  const pintar = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const g = juego.current;
    const t = temaRef.current || leerTema(canvas);

    ctx.clearRect(0, 0, g.ancho, ALTO);
    ctx.fillStyle = t.fondo;
    ctx.fillRect(0, 0, g.ancho, ALTO);

    for (const barra of g.barras) {
      ctx.fillStyle = t.barra;
      ctx.fillRect(barra.x, 0, BARRA_ANCHO, barra.hueco);
      ctx.fillRect(barra.x, barra.hueco + HUECO, BARRA_ANCHO, ALTO - barra.hueco - HUECO);
      ctx.fillStyle = t.acento;                       // labio naranja del hueco
      ctx.fillRect(barra.x, barra.hueco - 3, BARRA_ANCHO, 3);
      ctx.fillRect(barra.x, barra.hueco + HUECO, BARRA_ANCHO, 3);
    }

    ctx.fillStyle = t.borde;
    ctx.fillRect(0, ALTO - SUELO, g.ancho, SUELO);

    const inclinacion = Math.max(-0.5, Math.min(1.1, g.vy / 9));
    dibujarMegafono(ctx, AVATAR_X, g.y, inclinacion, t.acento);

    ctx.fillStyle = t.texto;
    ctx.font = "bold 22px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.textAlign = "right";
    ctx.fillText(String(g.puntos), g.ancho - 10, 28);
    ctx.textAlign = "left";
  }, []);

  // ── Tamaño (declara ancho lógico y repinta) ───────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    const contenedor = contenedorRef.current;
    if (!canvas || !contenedor) return undefined;

    function medir() {
      const ancho = Math.max(240, Math.round(contenedor.clientWidth));
      const dpr = window.devicePixelRatio || 1;
      juego.current.ancho = ancho;
      canvas.width = Math.round(ancho * dpr);
      canvas.height = Math.round(ALTO * dpr);
      canvas.style.height = `${ALTO}px`;
      canvas.getContext("2d").setTransform(dpr, 0, 0, dpr, 0, 0);
      pintar();   // la asignación de canvas.width de arriba dejó el canvas vacío
    }
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(contenedor);
    return () => observador.disconnect();
  }, [pintar]);

  // ── Tema ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const releer = () => {
      temaRef.current = leerTema(canvas);
      pintar();
    };
    releer();
    const observador = new MutationObserver(releer);
    observador.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observador.disconnect();
  }, [pintar]);

  // ── Controles ─────────────────────────────────────────────────────────────
  const reiniciar = useCallback(() => {
    const g = juego.current;
    g.y = ALTO / 2;
    g.vy = 0;
    g.barras = [];
    g.puntos = 0;
    setPuntos(0);
  }, []);

  const aletear = useCallback(() => {
    if (fase === "jugando") {
      juego.current.vy = IMPULSO;
      return;
    }
    // "listo" y "perdio" arrancan partida nueva.
    reiniciar();
    setFase("jugando");
    juego.current.vy = IMPULSO;
  }, [fase, reiniciar]);

  // Capture en window para llegar antes que el botón de cerrar del modal, que
  // tiene el foco al abrirse (ver el punto 1 del docstring).
  useEffect(() => {
    function alPulsar(e) {
      if (e.key === " " || e.key === "Spacebar" || e.key === "ArrowUp") {
        e.preventDefault();
        e.stopPropagation();
        aletear();
      }
    }
    window.addEventListener("keydown", alPulsar, true);
    return () => window.removeEventListener("keydown", alPulsar, true);
  }, [aletear]);

  // ── Bucle ─────────────────────────────────────────────────────────────────
  // Se remonta al cambiar de fase, que es justo lo que se quiere: en "listo" y
  // "perdio" pinta un solo cuadro y no consume nada.
  useEffect(() => {
    if (fase !== "jugando") {
      pintar();
      return undefined;
    }

    let vivo = true;
    let ultimoT = null;

    function paso(ahora) {
      if (!vivo) return;
      const g = juego.current;

      // Primer frame: no hay intervalo con el que comparar, se asume uno de 60 fps.
      const dt = ultimoT === null ? 1 : Math.min(DT_MAX, (ahora - ultimoT) / MS_POR_FRAME);
      ultimoT = ahora;

      g.vy = Math.min(CAIDA_MAX, g.vy + GRAVEDAD * dt);
      g.y += g.vy * dt;

      const ultima = g.barras[g.barras.length - 1];
      // La PRIMERA barra entra más adentro: si naciera en el borde tardaría
      // ~3.5 s en cruzar el megáfono, más de lo que sobrevive un aleteo suelto,
      // y la partida se sentía vacía antes del primer punto. Las siguientes ya
      // llegan cada ~1.2 s por SEPARACION.
      if (!ultima) {
        const hueco = MARGEN_HUECO + Math.random() * (ALTO - HUECO - MARGEN_HUECO * 2);
        g.barras.push({ x: g.ancho * 0.6, hueco, contada: false });
      } else if (g.ancho - ultima.x >= SEPARACION) {
        const hueco = MARGEN_HUECO + Math.random() * (ALTO - HUECO - MARGEN_HUECO * 2);
        g.barras.push({ x: g.ancho, hueco, contada: false });
      }
      for (const barra of g.barras) barra.x -= VELOCIDAD * dt;
      g.barras = g.barras.filter((b) => b.x + BARRA_ANCHO > -4);

      let choco = g.y + RADIO >= ALTO - SUELO || g.y - RADIO <= 0;
      for (const barra of g.barras) {
        const solapaX = AVATAR_X + RADIO > barra.x && AVATAR_X - RADIO < barra.x + BARRA_ANCHO;
        if (solapaX && (g.y - RADIO < barra.hueco || g.y + RADIO > barra.hueco + HUECO)) {
          choco = true;
        }
        if (!barra.contada && barra.x + BARRA_ANCHO < AVATAR_X - RADIO) {
          barra.contada = true;
          g.puntos += 1;
          setPuntos(g.puntos);
        }
      }

      pintar();

      if (choco) {
        vivo = false;
        setFase("perdio");
        setRecord((previo) => {
          const mejor = Math.max(previo, g.puntos);
          if (mejor > previo) guardarRecord(mejor);
          return mejor;
        });
        return;
      }
      frameRef.current = requestAnimationFrame(paso);
    }

    frameRef.current = requestAnimationFrame(paso);
    return () => {
      vivo = false;
      cancelAnimationFrame(frameRef.current);
    };
  }, [fase, pintar]);

  return (
    <div ref={contenedorRef}>
      <div className="mb-1.5 flex items-baseline justify-between">
        <p className="go-eyebrow">Megáfono volador</p>
        <p className="font-mono text-[11px]" style={{ color: "var(--go-text-muted)" }}>
          récord {record}
        </p>
      </div>

      <div className="relative overflow-hidden rounded-go" style={{ border: "1px solid var(--go-border)" }}>
        <canvas
          ref={canvasRef}
          onPointerDown={(e) => {
            e.preventDefault();
            aletear();
          }}
          className="block w-full cursor-pointer touch-none select-none"
          role="img"
          aria-label={`Minijuego: megáfono volador. Puntos: ${puntos}. Récord: ${record}.`}
        />

        {fase !== "jugando" && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 px-4 text-center">
            <p
              className="font-display text-sm font-bold"
              style={{ color: "var(--go-text-primary)", textShadow: "0 1px 6px rgba(0,0,0,0.7)" }}
            >
              {fase === "listo" ? "Toca o pulsa Espacio" : `Chocaste con ${puntos} punto${puntos === 1 ? "" : "s"}`}
            </p>
            <p
              className="font-body text-[11px]"
              style={{ color: "var(--go-text-secondary)", textShadow: "0 1px 6px rgba(0,0,0,0.7)" }}
            >
              {fase === "listo" ? "Esquiva las barras" : "Toca para reintentar"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
