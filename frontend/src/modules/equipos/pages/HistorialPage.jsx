import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, SkeletonShimmer, useToast } from "@/design";
import { esCodigo, ApiError } from "@/api";
import { fetchLoans, fetchLoansExport } from "../api";
import { usePermisos } from "../permisos/usePermisos";

const LIMIT = 20;

const ESTADO_LABEL = {
  borrador: "Borrador",
  prestado: "Prestado",
  pendiente_confirmacion: "Pend. confirmación",
  incompleto: "Incompleto",
  completado: "Completado",
  cancelado: "Cancelado",
};
const ESTADO_BADGE = {
  borrador: "go-badge-neutral",
  prestado: "go-badge-neutral",
  pendiente_confirmacion: "go-badge-warning",
  incompleto: "go-badge-error",
  completado: "go-badge-success",
  cancelado: "go-badge-neutral",
};

export default function HistorialPage() {
  const { puede } = usePermisos();
  const { push } = useToast();

  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);
  const [exportando, setExportando] = useState(false);

  const [qInput, setQInput] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [estado, setEstado] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setQDebounced(qInput), 300);
    return () => clearTimeout(t);
  }, [qInput]);

  useEffect(() => {
    setOffset(0);
  }, [estado, desde, hasta, qDebounced]);

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    try {
      const data = await fetchLoans({
        estado: estado || undefined,
        q: qDebounced || undefined,
        desde: desde || undefined,
        hasta: hasta || undefined,
        limit: LIMIT,
        offset,
      });
      setResultado(data);
    } catch (e) {
      if (esCodigo(e, "PERMISOS_NO_DISPONIBLES")) setPermisosNoDisponibles(true);
      else setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, desde, hasta, qDebounced, offset]);

  async function handleExportar() {
    setExportando(true);
    try {
      const blob = await fetchLoansExport({
        estado: estado || undefined,
        q: qDebounced || undefined,
        desde: desde || undefined,
        hasta: hasta || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "prestamos.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      // fetch -> blob -> descarga (I4f): si el servidor responde 403/503,
      // esto muestra el error real en un toast en vez de dejar que el
      // navegador "descargue" un archivo .csv cuyo contenido es el JSON
      // del error.
      const mensaje = e instanceof ApiError ? e.detail || e.message : e.message;
      push({ tone: "error", title: "No se pudo exportar", message: mensaje });
    } finally {
      setExportando(false);
    }
  }

  const totalPages = resultado ? Math.max(1, Math.ceil(resultado.total / LIMIT)) : 1;
  const currentPage = Math.floor(offset / LIMIT) + 1;

  if (loading && !resultado) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <SkeletonShimmer key={i} className="h-16 w-full" />
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Historial <span style={{ color: "var(--go-orange)" }}>({resultado.total})</span>
        </h1>
        {puede("equipos_prestamos", "exportar") && (
          <button type="button" onClick={handleExportar} disabled={exportando} className="btn-go">
            {exportando ? "Exportando..." : "Exportar CSV"}
          </button>
        )}
      </div>

      <div className="go-card flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] flex-1">
          <label className="go-eyebrow mb-1.5 block">Buscar</label>
          <input
            type="text"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            placeholder="Folio, motivo o responsable..."
            className="go-input"
          />
        </div>
        <div className="min-w-[170px]">
          <label className="go-eyebrow mb-1.5 block">Estado</label>
          <select value={estado} onChange={(e) => setEstado(e.target.value)} className="go-select">
            <option value="">Todos</option>
            {Object.entries(ESTADO_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-[150px]">
          <label className="go-eyebrow mb-1.5 block">Desde</label>
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="go-input" />
        </div>
        <div className="min-w-[150px]">
          <label className="go-eyebrow mb-1.5 block">Hasta</label>
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="go-input" />
        </div>
      </div>

      {resultado.items.length === 0 ? (
        <EmptyState title="Sin resultados" message="Ningún préstamo coincide con estos filtros." />
      ) : (
        <div className="go-table-scroll-wrapper">
          <div className="overflow-x-auto rounded-go-lg border go-table-scroll" style={{ borderColor: "var(--go-border)" }}>
            <table className="go-table w-full">
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Responsable</th>
                  <th>Motivo</th>
                  <th>Entrega</th>
                  <th>Regreso esperado</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {resultado.items.map((loan) => (
                  <tr key={loan.id}>
                    <td className="font-mono">
                      <Link to={`/equipos/prestamo/${loan.folio}`} style={{ color: "var(--go-orange)" }}>
                        {loan.folio || "—"}
                      </Link>
                    </td>
                    <td>{loan.responsable?.nombre || "—"}</td>
                    <td>{loan.motivo || "—"}</td>
                    <td className="font-mono">{loan.fecha_entrega || "—"}</td>
                    <td className="font-mono">{loan.fecha_regreso_esperada || "—"}</td>
                    <td>
                      <div className="flex flex-wrap gap-1.5">
                        <span className={`go-badge ${ESTADO_BADGE[loan.estado]}`}>{ESTADO_LABEL[loan.estado] || loan.estado}</span>
                        {loan.atrasado && <span className="go-badge go-badge-error">Atrasado {loan.dias_atraso}d</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          <span>
            Página {currentPage} de {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - LIMIT))}
              className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
            >
              Anterior
            </button>
            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => setOffset((o) => o + LIMIT)}
              className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
