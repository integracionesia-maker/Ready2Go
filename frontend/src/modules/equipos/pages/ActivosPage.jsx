import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EmptyState, GlassPanel, SkeletonShimmer, useToast, RowActions, ICONS, usePageTitle, SortableHeaderCell, useSortable } from "@/design";
import { esCodigo } from "@/api";
import { fetchLoans, fetchLoanById, loanResponsivaUrl } from "../api";
import { usePermisos } from "../permisos/usePermisos";
import RegistrarDevolucionModal from "../components/RegistrarDevolucionModal";

const ESTADOS_ACTIVOS = ["prestado", "pendiente_confirmacion", "incompleto"];

const ESTADO_LABEL = {
  prestado: "Prestado",
  pendiente_confirmacion: "Pend. confirmación",
  incompleto: "Incompleto",
};
const ESTADO_BADGE = {
  prestado: "go-badge-neutral",
  pendiente_confirmacion: "go-badge-warning",
  incompleto: "go-badge-error",
};

const SORTABLE_COLUMNS = [
  { key: "folio", label: "Folio", type: "string" },
  { key: "responsable", label: "Responsable", type: "string", getValue: (l) => l.responsable?.nombre || "" },
  { key: "equipos", label: "Equipos", type: "string", getValue: (l) => (l.equipos || []).join(", ") },
  { key: "fecha_regreso_esperada", label: "Regreso esperado", type: "date" },
  { key: "estado", label: "Estado", type: "string", getValue: (l) => ESTADO_LABEL[l.estado] || l.estado },
];

export default function ActivosPage() {
  usePageTitle("Préstamos Activos");
  const { puede } = usePermisos();
  const navigate = useNavigate();
  const { push } = useToast();

  const [todos, setTodos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);

  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [estadoFiltro, setEstadoFiltro] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [devolucionLoan, setDevolucionLoan] = useState(null);
  const [cargandoDevolucion, setCargandoDevolucion] = useState(null); // id del loan en vuelo

  // GET /loans/ devuelve LoanRow (fila liviana: sin `items`, sin `firmas`,
  // sin `responsiva`) — el mock nunca distinguio fila de ficha y siempre
  // regreso el objeto completo, asi que este desfase no se vio hasta probar
  // contra el servidor real. RegistrarDevolucionModal necesita `items[]` con
  // media por renglon: hay que pedir el detalle (LoanDetail) antes de abrir
  // el modal, no pasarle la fila tal cual.
  async function abrirDevolucion(loan) {
    setCargandoDevolucion(loan.id);
    try {
      const detalle = await fetchLoanById(loan.id);
      setDevolucionLoan(detalle);
    } catch (e) {
      push({ tone: "error", title: "No se pudo abrir la devolución", message: e.detail || e.message });
    } finally {
      setCargandoDevolucion(null);
    }
  }

  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    try {
      // El contrato solo acepta un `estado` a la vez; "Activos" es la UNION
      // de tres estados, así que se filtra en el cliente sobre una página
      // razonablemente grande en vez de inventar un parámetro que el
      // contrato no tiene.
      const data = await fetchLoans({ limit: 200 });
      setTodos(data.items.filter((l) => ESTADOS_ACTIVOS.includes(l.estado)));
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

  const filtrados = useMemo(() => {
    let items = todos;
    if (estadoFiltro) items = items.filter((l) => l.estado === estadoFiltro);
    if (qDebounced) {
      const needle = qDebounced.toLowerCase();
      items = items.filter(
        (l) =>
          l.folio?.toLowerCase().includes(needle) ||
          l.motivo?.toLowerCase().includes(needle) ||
          l.responsable?.nombre?.toLowerCase().includes(needle)
      );
    }
    return items;
  }, [todos, estadoFiltro, qDebounced]);

  const { sortedItems: sortedFiltrados, sortKey, sortDir, cycleSort: cycleSortRaw } = useSortable(
    filtrados,
    SORTABLE_COLUMNS
  );
  const cycleSort = (key) => {
    cycleSortRaw(key);
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(sortedFiltrados.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageItems = sortedFiltrados.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const rangeStart = sortedFiltrados.length === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const rangeEnd = Math.min(currentPage * pageSize, sortedFiltrados.length);

  async function verResponsiva(loan) {
    const url = await loanResponsivaUrl(loan.id);
    window.open(url, "_blank", "noopener");
  }

  if (loading) {
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
      <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
        Préstamos activos <span style={{ color: "var(--go-orange)" }}>({filtrados.length})</span>
      </h1>

      <GlassPanel className="flex flex-wrap items-end gap-3 p-4 sm:p-5">
        <div className="min-w-[220px] flex-1">
          <label className="go-eyebrow mb-1.5 block">Buscar</label>
          <input
            type="text"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            placeholder="Folio, motivo o responsable..."
            className="go-input"
          />
        </div>
        <div className="min-w-[180px]">
          <label className="go-eyebrow mb-1.5 block">Estado</label>
          <select
            value={estadoFiltro}
            onChange={(e) => {
              setEstadoFiltro(e.target.value);
              setPage(1);
            }}
            className="go-select"
          >
            <option value="">Todos</option>
            {ESTADOS_ACTIVOS.map((e) => (
              <option key={e} value={e}>
                {ESTADO_LABEL[e]}
              </option>
            ))}
          </select>
        </div>
      </GlassPanel>

      {pageItems.length === 0 ? (
        <EmptyState title="Sin préstamos activos" message="Ningún préstamo coincide con estos filtros." />
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
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {pageItems.map((loan) => (
                  <tr
                    key={loan.id}
                    className={loan.folio ? "cursor-pointer" : undefined}
                    onClick={loan.folio ? () => navigate(`/equipos/prestamo/${loan.folio}`) : undefined}
                  >
                    <td className="font-mono" onClick={(e) => e.stopPropagation()}>
                      <Link to={`/equipos/prestamo/${loan.folio}`} style={{ color: "var(--go-orange)" }}>
                        {loan.folio}
                      </Link>
                    </td>
                    <td>{loan.responsable?.nombre || "—"}</td>
                    <td>{(loan.equipos || []).join(", ") || "—"}</td>
                    <td className="font-mono">{loan.fecha_regreso_esperada || "—"}</td>
                    <td>
                      <div className="flex flex-wrap gap-1.5">
                        <span className={`go-badge ${ESTADO_BADGE[loan.estado]}`}>{ESTADO_LABEL[loan.estado]}</span>
                        {loan.atrasado && <span className="go-badge go-badge-error">Atrasado {loan.dias_atraso}d</span>}
                        {!loan.entrega_autorizada && <span className="go-badge go-badge-neutral">Entrega no autorizada</span>}
                        {(loan.firma_entrega_pendiente || loan.firma_responsable_pendiente) && (
                          <span className="go-badge go-badge-warning">Firma pendiente</span>
                        )}
                      </div>
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <RowActions
                        actions={[
                          {
                            key: "ficha",
                            label: "Ver ficha",
                            icon: ICONS.ver,
                            onClick: () => navigate(`/equipos/prestamo/${loan.folio}`),
                          },
                          // `LoanRow` no trae `responsiva` (solo `LoanDetail` la
                          // tiene) — el folio se asigna en el mismo momento que
                          // la responsiva (al confirmar), así que su presencia
                          // es la señal disponible en la fila.
                          loan.folio && {
                            key: "responsiva",
                            label: "Ver responsiva",
                            icon: ICONS.responsiva,
                            onClick: () => verResponsiva(loan),
                          },
                          loan.estado === "prestado" &&
                            puede("equipos_prestamos", "registrar_devolucion") && {
                              key: "devolucion",
                              label: cargandoDevolucion === loan.id ? "Abriendo..." : "Registrar devolución",
                              icon: ICONS.devolucion,
                              onClick: () => abrirDevolucion(loan),
                            },
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        </GlassPanel>
      )}

      {pageItems.length > 0 && (
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3" style={{ borderTop: "1px solid var(--go-border)" }}>
        <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
          <span className="hidden sm:inline">
            Mostrando {rangeStart}–{rangeEnd} de {filtrados.length}
          </span>
          <span className="sm:hidden">
            {rangeStart}–{rangeEnd}/{filtrados.length}
          </span>
        </span>
        <div className="flex flex-wrap items-center gap-3">
          <label className="hidden sm:inline font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
            Filas por página
          </label>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
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
              disabled={currentPage === 1}
              onClick={() => setPage((p) => p - 1)}
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
              onClick={() => setPage((p) => p + 1)}
              className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>
      )}

      {devolucionLoan && (
        <RegistrarDevolucionModal
          loan={devolucionLoan}
          onClose={() => setDevolucionLoan(null)}
          onSuccess={() => {
            setDevolucionLoan(null);
            cargar();
          }}
        />
      )}
    </div>
  );
}
