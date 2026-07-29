import { useState } from "react";
import { useToast } from "@/design";
import * as loansApi from "./api/loans";
import * as mediaApi from "./api/media";
import * as permisosApi from "./api/permisos";
import { setInjectedError, getInjectedError } from "./api/mock/errorInjection";

// Panel de diagnóstico TEMPORAL de I3 — no es una vista de Equipos (esas son
// I4). Su único trabajo es probar, con algo visible en pantalla, que el mock
// + ApiError pintan bien los cinco códigos feos del contrato, ya que I4
// (donde vivirían las vistas reales) todavía no existe. Se borra cuando I4
// tenga sus propias pantallas reaccionando a estos mismos códigos.
const CODES = [
  { codigo: "EQUIPO_OCUPADO", etiqueta: "409 EQUIPO_OCUPADO (agregar item)" },
  { codigo: "SIN_PERMISO", etiqueta: "403 SIN_PERMISO (cualquier acción)" },
  { codigo: "PERMISOS_NO_DISPONIBLES", etiqueta: "503 PERMISOS_NO_DISPONIBLES (catálogo)" },
  { codigo: "MEDIA_MUY_GRANDE", etiqueta: "413 MEDIA_MUY_GRANDE (subir foto)" },
  { codigo: "SESION_EXPIRADA", etiqueta: "401 a mitad del wizard (confirmar)" },
];

const TONE_POR_STATUS = { 503: "warning", 403: "error", 409: "warning", 413: "error", 401: "warning" };

export default function DevMockHarness() {
  const { push } = useToast();
  const [active, setActive] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  async function trigger(codigo) {
    setInjectedError(codigo);
    setActive(codigo);
    setLastResult(null);
    try {
      if (codigo === "EQUIPO_OCUPADO") {
        // El equipment_id=1 del fixture ya está en el loan 7 (prestado).
        await loansApi.addLoanItem(7, { equipmentId: 1 });
      } else if (codigo === "SIN_PERMISO") {
        await loansApi.fetchLoans();
      } else if (codigo === "PERMISOS_NO_DISPONIBLES") {
        await permisosApi.fetchPermisosCatalogo();
      } else if (codigo === "MEDIA_MUY_GRANDE") {
        const bigFile = new File([new Uint8Array(4 * 1024 * 1024)], "foto.jpg", { type: "image/jpeg" });
        await mediaApi.uploadMedia(7, { file: bigFile, kind: "foto_entrega_frente" });
      } else if (codigo === "SESION_EXPIRADA") {
        await loansApi.confirmLoan(7);
      }
      setLastResult({ ok: true });
      push({ tone: "success", title: "Sin error", message: "La llamada no truena — revisa la inyección." });
    } catch (e) {
      setLastResult({ status: e.status, codigo: e.codigo, message: e.message });
      push({
        tone: TONE_POR_STATUS[e.status] || "error",
        title: `${e.status ?? "Error"} ${e.codigo ?? ""}`.trim(),
        message: e.message,
      });
    } finally {
      setInjectedError(null);
      setActive(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-8">
      <div>
        <p className="go-eyebrow mb-2">I3 — diagnóstico temporal</p>
        <h1 className="font-display text-lg font-bold" style={{ color: "var(--go-text-primary)" }}>
          Códigos feos del contrato de Equipos
        </h1>
        <p className="mt-1 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Dispara cada código contra el mock (localStorage["equipos-mock-error"]) y
          muestra el resultado real vía Toast. Reemplazado por las vistas de I4.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {CODES.map(({ codigo, etiqueta }) => (
          <button
            key={codigo}
            type="button"
            onClick={() => trigger(codigo)}
            disabled={active === codigo}
            className="btn-go-ghost justify-start"
          >
            {active === codigo ? "Disparando…" : etiqueta}
          </button>
        ))}
      </div>

      {lastResult && (
        <div className="go-card">
          <p className="go-eyebrow">Último resultado</p>
          <pre
            className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs"
            style={{ color: "var(--go-text-primary)" }}
          >
            {JSON.stringify(lastResult, null, 2)}
          </pre>
        </div>
      )}

      <p className="font-mono text-xs" style={{ color: "var(--go-text-muted)" }}>
        getInjectedError() ahora mismo: {String(getInjectedError())}
      </p>
    </div>
  );
}
