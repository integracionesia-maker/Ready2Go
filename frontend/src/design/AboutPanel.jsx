import { createPortal } from "react-dom";
import FlappyMkt from "./FlappyMkt";
import GlassModal from "./GlassModal";
import { APP_VERSION, BUILD_DATE, COMMIT_HASH, entornoActual } from "./buildInfo";

/**
 * Panel "acerca de" — el easter egg del menú de perfil.
 *
 * Se abre con 7 clics sobre la etiqueta de versión (`ProfilePopover.jsx`), al
 * estilo del número de build de Android. Se eligió el tap y no una combinación
 * de teclas por dos razones: Equipos se usa desde el celular (fotos con la
 * cámara, firma con el dedo), y la paleta de comandos Ctrl+K se eliminó el
 * 18/08/2026 justamente porque nadie encontraba las funciones de teclado.
 *
 * Contenido: identidad del build, créditos y un minijuego (`FlappyMkt.jsx`).
 *
 * **Cero datos de negocio, a propósito.** Nada de totales (tickets, montos,
 * creadores): el panel lo ve cualquier sesión autenticada, incluidos los roles
 * `creador` y `marketing_basico`, que por diseño solo ven lo suyo. Meter cifras
 * globales aquí sería reabrir el hallazgo A1 del diagnóstico de seguridad del
 * 18/08 (`GET /api/tickets/` listaba todo a cualquiera) por la puerta de atrás.
 * Si algún día se quieren números en vivo, van detrás de
 * `presupuestos:ver_global` y con su propio endpoint.
 *
 * **Portal obligatorio, no estilístico.** El `<header>` que contiene el
 * popover es `glass fixed ... z-40`, y `.glass` aplica `backdrop-filter`
 * (`design/glass.css:11`). Un `backdrop-filter` crea bloque contenedor para
 * los descendientes `position: fixed`, así que sin el portal el `fixed inset-0`
 * de GlassModal se recortaría a la caja del header (56 px de alto) y quedaría
 * atrapado bajo su `z-40`, por debajo del resto de la app.
 */

const CREDITOS = [
  { nombre: "José Aguilar", papel: "supervisor" },
  { nombre: "Damián Morales", papel: "owner" },
  { nombre: "Beni", papel: "apoyo" },
];

export default function AboutPanel({ open, onClose }) {
  if (typeof document === "undefined") return null;

  return createPortal(
    <GlassModal open={open} onClose={onClose} title="Acerca de GOCreate" refract>
      <div className="space-y-5">
        {/* Identidad — la mitad útil del panel: es lo que se le pide en captura
            a quien reporta un bug ("¿qué versión ves?"). */}
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-go font-display text-lg font-bold"
            style={{ background: "var(--go-orange)", color: "#fff" }}
            aria-hidden="true"
          >
            GO
          </div>
          <div className="min-w-0">
            <p className="font-display text-base font-bold" style={{ color: "var(--go-text-primary)" }}>
              GOCreate
            </p>
            <p className="font-mono text-[11px] leading-relaxed" style={{ color: "var(--go-text-secondary)" }}>
              v{APP_VERSION} · {COMMIT_HASH}
            </p>
            <p className="font-mono text-[11px] leading-relaxed" style={{ color: "var(--go-text-muted)" }}>
              {entornoActual()} · build {BUILD_DATE}
            </p>
          </div>
        </div>

        <div className="border-t pt-4" style={{ borderColor: "var(--go-border)" }}>
          <p className="go-eyebrow mb-2.5">Hecho por</p>
          <ul className="space-y-1.5">
            {CREDITOS.map((c) => (
              <li key={c.nombre} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                <span className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                  {c.nombre}
                </span>
                <span className="font-body text-xs" style={{ color: "var(--go-text-muted)" }}>
                  {c.papel}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* El minijuego solo se monta cuando el panel está abierto: GlassModal
            desmonta a sus hijos al cerrar (AnimatePresence), así que el bucle de
            animación no queda corriendo detrás. */}
        <div className="border-t pt-4" style={{ borderColor: "var(--go-border)" }}>
          <FlappyMkt />
        </div>
      </div>
    </GlassModal>,
    document.body
  );
}
