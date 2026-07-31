import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, GlassPanel, SkeletonShimmer, useToast } from "@/design";
import { esCodigo } from "@/api";
import { fetchLoans, fetchLoanById, authorizeDelivery } from "../api";
import { usePermisos } from "../permisos/usePermisos";
import ConfirmarDevolucionModal from "../components/ConfirmarDevolucionModal";
import CerrarIncidenciaModal from "../components/CerrarIncidenciaModal";

const ESTADOS_ABIERTOS_NO_TERMINALES = ["borrador", "cancelado"];

function ColaVacia({ mensaje }) {
  return (
    <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
      {mensaje}
    </p>
  );
}

export default function AprobacionesPage() {
  const { puede } = usePermisos();
  const { push } = useToast();

  const [todos, setTodos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);
  const [autorizandoId, setAutorizandoId] = useState(null);

  const [modalDevolucion, setModalDevolucion] = useState(null);
  const [modalIncidencia, setModalIncidencia] = useState(null);
  const [abriendoDevolucionId, setAbriendoDevolucionId] = useState(null);

  // GET /loans/ devuelve LoanRow (sin `items`) — ConfirmarDevolucionModal
  // necesita el detalle completo (LoanDetail) para decidir por renglon. El
  // mock nunca distinguio fila de ficha, por eso este desfase solo aparecio
  // al probar contra el servidor real (I8, lote 1/2).
  async function abrirConfirmarDevolucion(loan) {
    setAbriendoDevolucionId(loan.id);
    try {
      const detalle = await fetchLoanById(loan.id);
      setModalDevolucion(detalle);
    } catch (e) {
      push({ tone: "error", title: "No se pudo abrir la devolución", message: e.detail || e.message });
    } finally {
      setAbriendoDevolucionId(null);
    }
  }

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    try {
      const data = await fetchLoans({ limit: 200 });
      setTodos(data.items);
    } catch (e) {
      if (esCodigo(e, "PERMISOS_NO_DISPONIBLES")) setPermisosNoDisponibles(true);
      else setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  // Tres colas SEPARADAS a propósito (regla dura del prompt) — mezclarlas
  // en una sola tabla escondería que son tres permisos y tres acciones
  // distintas del contrato (§4).
  const entregasPendientes = useMemo(
    () => todos.filter((l) => !l.entrega_autorizada && !ESTADOS_ABIERTOS_NO_TERMINALES.includes(l.estado)),
    [todos]
  );
  const devolucionesPendientes = useMemo(() => todos.filter((l) => l.estado === "pendiente_confirmacion"), [todos]);
  const incidencias = useMemo(() => todos.filter((l) => l.estado === "incompleto"), [todos]);

  async function handleAutorizar(loan) {
    setAutorizandoId(loan.id);
    try {
      await authorizeDelivery(loan.id);
      push({ tone: "success", title: `Entrega autorizada — ${loan.folio}` });
      cargar();
    } catch (e) {
      push({ tone: "error", title: "No se pudo autorizar", message: e.detail || e.message });
    } finally {
      setAutorizandoId(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <SkeletonShimmer key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (permisosNoDisponibles) {
    return (
      <EmptyState
        title="No se pudieron resolver los permisos"
        message="Esto es temporal — reintenta en un momento. Tu sesión sigue activa."
        action={
          <button type="button" onClick={cargar} className="btn-go mt-2">
            Reintentar
          </button>
        }
      />
    );
  }

  if (error) {
    return (
      <div
        className="rounded-go border px-4 py-3 font-body text-sm"
        style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
      >
        {error}
      </div>
    );
  }

  const sinPermisoAlguno =
    !puede("equipos_aprobacion", "autorizar_entrega") &&
    !puede("equipos_aprobacion", "confirmar_devolucion") &&
    !puede("equipos_aprobacion", "cerrar_incidencia");

  if (sinPermisoAlguno) {
    return <EmptyState title="Sin acceso" message="Tu rol no tiene permisos de aprobación en Equipos." />;
  }

  return (
    <>
    <GlassPanel className="space-y-6 p-4 sm:p-6">
      {puede("equipos_aprobacion", "autorizar_entrega") && (
        <div>
          <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
            Autorizaciones de entrega ({entregasPendientes.length})
          </h2>
          {entregasPendientes.length === 0 ? (
            <ColaVacia mensaje="Nada pendiente de autorizar." />
          ) : (
            <ul className="space-y-2">
              {entregasPendientes.map((loan) => (
                <li key={loan.id} className="flex flex-wrap items-center justify-between gap-3 rounded-go border p-3" style={{ borderColor: "var(--go-border)", background: "var(--go-surface-sunken)" }}>
                  <div>
                    <Link to={`/equipos/prestamo/${loan.folio}`} className="font-mono text-sm font-semibold" style={{ color: "var(--go-orange)" }}>
                      {loan.folio}
                    </Link>
                    <span className="ml-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                      {loan.responsable?.nombre} · {loan.motivo}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAutorizar(loan)}
                    disabled={autorizandoId === loan.id}
                    className="btn-go text-xs px-3 py-1.5"
                  >
                    {autorizandoId === loan.id ? "Autorizando..." : "Autorizar entrega"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {puede("equipos_aprobacion", "confirmar_devolucion") && (
        <div>
          <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
            Devoluciones por confirmar ({devolucionesPendientes.length})
          </h2>
          {devolucionesPendientes.length === 0 ? (
            <ColaVacia mensaje="Nada pendiente de confirmar." />
          ) : (
            <ul className="space-y-2">
              {devolucionesPendientes.map((loan) => (
                <li key={loan.id} className="flex flex-wrap items-center justify-between gap-3 rounded-go border p-3" style={{ borderColor: "var(--go-border)", background: "var(--go-surface-sunken)" }}>
                  <div>
                    <Link to={`/equipos/prestamo/${loan.folio}`} className="font-mono text-sm font-semibold" style={{ color: "var(--go-orange)" }}>
                      {loan.folio}
                    </Link>
                    <span className="ml-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                      {loan.responsable?.nombre}
                    </span>
                    {!loan.entrega_autorizada && <span className="go-badge go-badge-warning ml-2">Entrega no autorizada</span>}
                  </div>
                  <button
                    type="button"
                    onClick={() => abrirConfirmarDevolucion(loan)}
                    disabled={abriendoDevolucionId === loan.id}
                    className="btn-go text-xs px-3 py-1.5"
                  >
                    {abriendoDevolucionId === loan.id ? "Abriendo..." : "Confirmar devolución"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {puede("equipos_aprobacion", "cerrar_incidencia") && (
        <div>
          <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
            Incidencias abiertas ({incidencias.length})
          </h2>
          {incidencias.length === 0 ? (
            <ColaVacia mensaje="Sin incidencias abiertas." />
          ) : (
            <ul className="space-y-2">
              {incidencias.map((loan) => (
                <li key={loan.id} className="flex flex-wrap items-center justify-between gap-3 rounded-go border p-3" style={{ borderColor: "var(--go-border)", background: "var(--go-surface-sunken)" }}>
                  <div>
                    <Link to={`/equipos/prestamo/${loan.folio}`} className="font-mono text-sm font-semibold" style={{ color: "var(--go-orange)" }}>
                      {loan.folio}
                    </Link>
                    <span className="ml-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                      {loan.responsable?.nombre}
                    </span>
                  </div>
                  <button type="button" onClick={() => setModalIncidencia(loan)} className="btn-go-ghost text-xs px-3 py-1.5" style={{ color: "var(--go-error)" }}>
                    Cerrar incidencia
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </GlassPanel>

      {modalDevolucion && (
        <ConfirmarDevolucionModal
          loan={modalDevolucion}
          onClose={() => setModalDevolucion(null)}
          onSuccess={() => {
            setModalDevolucion(null);
            push({ tone: "success", title: "Devolución confirmada" });
            cargar();
          }}
        />
      )}
      {modalIncidencia && (
        <CerrarIncidenciaModal
          loan={modalIncidencia}
          onClose={() => setModalIncidencia(null)}
          onSuccess={() => {
            setModalIncidencia(null);
            push({ tone: "success", title: "Incidencia cerrada" });
            cargar();
          }}
        />
      )}
    </>
  );
}
