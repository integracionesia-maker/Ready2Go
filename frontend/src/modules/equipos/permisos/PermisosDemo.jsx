import { useState } from "react";
import { useToast } from "@/design";
import RequierePermiso from "./RequierePermiso";
import { usePermisos } from "./usePermisos";
import * as loansApi from "../api/loans";
import { setInjectedError } from "../api/mock/errorInjection";

// Demo/diagnóstico TEMPORAL de I5 — no es una vista de Equipos (esas son
// I4). Usuarios sintéticos vía `userOverride` de usePermisos/RequierePermiso
// (pensado justo para esto: probar los tres roles del cierre sin necesitar
// tres sesiones reales con esos permisos exactos).
const USUARIOS_DEMO = {
  colaborador_mkt: {
    etiqueta: "colaborador_mkt (puede solicitar)",
    user: { role: "colaborador_mkt", permisos: {} }, // {} => fuerza el fallback por rol
  },
  colaborador_mkt_aprobador: {
    etiqueta: "colaborador_mkt + APROBADOR_EQUIPO (ve autorizaciones)",
    user: {
      role: "colaborador_mkt",
      // permisos reales (no fallback): rol base + paquete aditivo ya resuelto,
      // tal como lo mandaría un /auth/me de WP1.
      permisos: {
        inicio: ["ver"],
        perfil: ["ver", "editar_propio"],
        equipos_inventario: ["ver"],
        equipos_prestamos: ["solicitar", "ver_propios", "registrar_devolucion", "ver_global"],
        equipos_aprobacion: ["autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"],
      },
    },
  },
  admin: {
    etiqueta: "admin (ve global, no autoriza)",
    user: { role: "admin", permisos: {} }, // {} => fallback por rol: admin no tiene equipos_aprobacion
  },
};

function Badge({ children, tone = "neutral" }) {
  const cls = tone === "success" ? "go-badge-success" : tone === "error" ? "go-badge-error" : "go-badge-neutral";
  return <span className={`go-badge ${cls}`}>{children}</span>;
}

export default function PermisosDemo() {
  const [usuarioKey, setUsuarioKey] = useState("colaborador_mkt");
  const usuario = USUARIOS_DEMO[usuarioKey].user;
  const { push } = useToast();
  const [resultado503, setResultado503] = useState(null);

  async function probar503() {
    setInjectedError("PERMISOS_NO_DISPONIBLES");
    setResultado503(null);
    try {
      await loansApi.fetchLoans();
      setResultado503({ ok: true });
    } catch (e) {
      // La regla dura: 503 PERMISOS_NO_DISPONIBLES nunca se pinta como "sin
      // acceso" (eso sería 403) ni desloguea — se pinta un estado de
      // reintento con el detail real del servidor.
      setResultado503({ status: e.status, codigo: e.codigo, message: e.message });
      push({ tone: "warning", title: `${e.status} ${e.codigo}`, message: e.message });
    } finally {
      setInjectedError(null);
    }
  }

  // Hook normal, con el usuario sintético actual (userOverride).
  const { puede } = usePermisos(usuario);

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-8">
      <div>
        <p className="go-eyebrow mb-2">I5 — demo temporal</p>
        <h1 className="font-display text-lg font-bold" style={{ color: "var(--go-text-primary)" }}>
          usePermisos / RequierePermiso
        </h1>
        <p className="mt-1 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          La UI solo pinta — ningún control de acceso real vive aquí.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(USUARIOS_DEMO).map(([key, { etiqueta }]) => (
          <button
            key={key}
            type="button"
            onClick={() => setUsuarioKey(key)}
            className="btn-go-ghost"
            disabled={usuarioKey === key}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      <div className="go-card space-y-3">
        <p className="go-eyebrow">Simulando: {USUARIOS_DEMO[usuarioKey].etiqueta}</p>

        <div className="flex items-center justify-between">
          <span className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
            Solicitar préstamo (equipos_prestamos:solicitar)
          </span>
          <RequierePermiso
            modulo="equipos_prestamos"
            accion="solicitar"
            userOverride={usuario}
            fallback={<Badge tone="error">Oculto</Badge>}
          >
            <Badge tone="success">Visible</Badge>
          </RequierePermiso>
        </div>

        <div className="flex items-center justify-between">
          <span className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
            Ver préstamos globales (equipos_prestamos:ver_global)
          </span>
          <RequierePermiso
            modulo="equipos_prestamos"
            accion="ver_global"
            userOverride={usuario}
            fallback={<Badge tone="error">Oculto</Badge>}
          >
            <Badge tone="success">Visible</Badge>
          </RequierePermiso>
        </div>

        <div className="flex items-center justify-between">
          <span className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
            Autorizar entrega (equipos_aprobacion:autorizar_entrega)
          </span>
          <RequierePermiso
            modulo="equipos_aprobacion"
            accion="autorizar_entrega"
            userOverride={usuario}
            fallback={<Badge tone="error">Oculto</Badge>}
          >
            <Badge tone="success">Visible</Badge>
          </RequierePermiso>
        </div>
      </div>

      <div className="go-card space-y-3">
        <p className="go-eyebrow">503 no es 403</p>
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Inyecta PERMISOS_NO_DISPONIBLES en el mock y llama a un endpoint de
          Equipos real. No debe desloguear ni pintarse como "sin acceso".
        </p>
        <button type="button" onClick={probar503} className="btn-go-ghost">
          Simular 503 al listar préstamos
        </button>
        {resultado503 && (
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs" style={{ color: "var(--go-text-primary)" }}>
            {JSON.stringify(resultado503, null, 2)}
          </pre>
        )}
      </div>

      <div className="go-card space-y-3">
        <p className="go-eyebrow">Modo diagnóstico</p>
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Dispara una clave inventada a propósito — revisa la consola del
          navegador para el aviso <code>[permisos] clave desconocida: ...</code>.
        </p>
        <button
          type="button"
          onClick={() => puede("equipos_prestamos", "teletransportar")}
          className="btn-go-ghost"
        >
          Probar clave inventada
        </button>
      </div>
    </div>
  );
}
