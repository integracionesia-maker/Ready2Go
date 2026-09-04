import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, GlassPanel, SkeletonShimmer, useToast, usePageTitle, SortableHeaderCell, useSortable } from "@/design";
import { esCodigo, ApiError } from "@/api";
import { fetchLoans, fetchLoansExport } from "../api";
import { usePermisos } from "../permisos/usePermisos";

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

const SORTABLE_COLUMNS = [
  { key: "folio", label: "Folio", type: "string" },
  { key: "responsable", label: "Responsable", type: "string", getValue: (l) => l.responsable?.nombre || "" },
  { key: "motivo", label: "Motivo", type: "string" },
  { key: "fecha_entrega", label: "Entrega", type: "date" },
  { key: "fecha_regreso_esperada", label: "Regreso esperado", type: "date" },
  { key: "estado", label: "Estado", type: "string", getValue: (l) => ESTADO_LABEL[l.estado] || l.estado },
];

export default function HistorialPage() {
  usePageTitle("Historial");
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
  const [limit, setLimit] = useState(20);

  const { sortedItems: sortedLoans, sortKey, sortDir, cycleSort } = useSortable(
    resultado?.items || [],
    SORTABLE_COLUMNS
  );

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
        limit,
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
  }, [estado, desde, hasta, qDebounced, offset, limit]);

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

  const totalPages = resultado ? Math.max(1, Math.ceil(resultado.total / limit)) : 1;
  const currentPage = Math.floor(offset / limit) + 1;
  const rangeStart = resultado && resultado.total !== 0 ? offset + 1 : 0;
  const rangeEnd = resultado ? Math.min(offset + limit, resultado.total) : 0;

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
          <button type="button" onClick={handleExportar} disabled={exportando} className="btn-go flex items-center gap-1.5">
            {exportando ? (
              "Exportando..."
            ) : (
              <>
                <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                </svg>
                Exportar CSV
              </>
            )}
          </button>
        )}
      </div>

      <GlassPanel className="flex flex-wrap items-end gap-3 p-4 sm:p-5">
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
      </GlassPanel>

      {resultado.items.length === 0 ? (
        <EmptyState title="Sin resultados" message="Ningún préstamo coincide con estos filtros." />
      ) : (
        <GlassPanel className="p-4 sm:p-6">
        <div className="go-table-scroll-wrapper">
          <div className="overflow-x-auto rounded-go-lg border go-table-scroll" style={{ borderColor: "var(--go-border)" }}>
            <table className="go-table w-full">
              <thead>
                <tr>
                  {SORTABLE_COLUMNS.map((col) => (
                    <SortableHeaderCell
                      key={col.key}
                      label={col.label}
                      columnKey={col.key}
                      activeKey={sortKey}
                      dir={sortDir}
                      onSort={cycleSort}
                      align={col.align}
                    />
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedLoans.map((loan) => (
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
        </GlassPanel>
      )}

      {resultado.items.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3" style={{ borderTop: "1px solid var(--go-border)" }}>
          <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
            <span className="hidden sm:inline">
              Mostrando {rangeStart}–{rangeEnd} de {resultado.total}
            </span>
            <span className="sm:hidden">
              {rangeStart}–{rangeEnd}/{resultado.total}
            </span>
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <label className="hidden sm:inline font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
              Filas por página
            </label>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setOffset(0);
              }}
              className="go-select w-auto py-1.5 text-xs"
            >
              {[10, 25, 50, 100].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - limit))}
                className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
              >
                Anterior
              </button>
              <span className="font-body text-xs tabular-nums" style={{ color: "var(--go-text-secondary)" }}>
                Página {currentPage} de {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setOffset((o) => o + limit)}
                className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
              >
                Siguiente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
