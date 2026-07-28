import { useState, useEffect, useMemo } from "react";
import { fetchTickets, softDeleteTicket, hardDeleteTicket } from "@/api";
import { PRIORITY_BADGE_CLASS, PRIORITY_LABELS } from "../utils/priority";
import MediaViewerModal from "./MediaViewerModal";
import DeleteConfirmModal from "./DeleteConfirmModal";
import RowActions from "./RowActions";
import { SortableHeaderCell } from "./SortableHeader";
import { useSortable } from "../hooks/useSortable";
import { useAuth } from "@/context/AuthContext";

const PAGE_SIZES = [10, 25, 50, 100];

const STATUS_LABELS = { pendiente: "Pendiente", aprobado: "Aprobado", rechazado: "Rechazado" };
const STATUS_BADGE_CLASS = {
  pendiente: "go-badge-warning",
  aprobado: "go-badge-success",
  rechazado: "go-badge-error",
};

/* Columnas ordenables: key = campo del ticket */
const SORTABLE_COLUMNS = [
  { key: "upload_date", label: "Fecha de carga", type: "date" },
  { key: "creator_name", label: "Creador", type: "string" },
  { key: "brand_name", label: "Marca", type: "string" },
  { key: "amount", label: "Monto", align: "right", type: "number" },
];

function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-MX", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function TransactionTable({ creators, brands, onChange }) {
  const { user } = useAuth();
  const canDelete = user?.role === "admin" || user?.role === "superadmin";

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filterCreator, setFilterCreator] = useState("");
  const [filterBrand, setFilterBrand] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPriority, setFilterPriority] = useState("");

  const [viewerTicket, setViewerTicket] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const filteredTickets = useMemo(() => {
    if (!filterPriority) return tickets;
    return tickets.filter((t) => t.brand_priority === filterPriority);
  }, [tickets, filterPriority]);

  const { sortedItems: sortedTickets, sortKey, sortDir, cycleSort: cycleSortRaw } = useSortable(
    filteredTickets,
    SORTABLE_COLUMNS
  );
  const cycleSort = (key) => {
    cycleSortRaw(key);
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(sortedTickets.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageTickets = sortedTickets.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );
  const rangeStart = sortedTickets.length === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const rangeEnd = Math.min(currentPage * pageSize, sortedTickets.length);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchTickets({
      creatorName: filterCreator || undefined,
      brandName: filterBrand || undefined,
      status: filterStatus || undefined,
    })
      .then((data) => {
        if (!cancelled) {
          setTickets(data);
          setPage(1); // los filtros cambiaron: volver a la primera página
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filterCreator, filterBrand, filterStatus, reloadToken]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2
          className="font-display text-lg font-bold uppercase tracking-[0.06em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Historial de Transacciones
        </h2>
        <span className="go-eyebrow">
          {sortedTickets.length} registros
        </span>
      </div>

      {/* ── Filters ──────────────────────────────────────────────────── */}
      <div
        className="flex flex-wrap gap-4 rounded-go-lg p-4"
        style={{ background: "var(--go-surface)", border: "1px solid var(--go-border)" }}
      >
        <div className="min-w-0 flex-1 sm:min-w-[200px]">
          <label className="go-eyebrow mb-1.5 block">Filtrar por Creador</label>
          <div className="relative">
            <input
              type="text"
              value={filterCreator}
              onChange={(e) => setFilterCreator(e.target.value)}
              placeholder="Nombre del creador..."
              className="go-input pl-9"
            />
            <svg
              className="absolute left-3 top-[11px] h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
              style={{ color: "var(--go-text-muted)" }}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        <div className="min-w-0 flex-1 sm:min-w-[180px]">
          <label className="go-eyebrow mb-1.5 block">Filtrar por Marca</label>
          <select
            value={filterBrand}
            onChange={(e) => setFilterBrand(e.target.value)}
            className="go-select"
          >
            <option value="">Todas las marcas</option>
            {brands.map((b) => (
              <option key={b.id} value={b.name}>
                {b.name}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-0 sm:min-w-[160px]">
          <label className="go-eyebrow mb-1.5 block">Prioridad</label>
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="go-select"
          >
            <option value="">Todas</option>
            <option value="alta">Alta</option>
            <option value="media">Media</option>
            <option value="baja">Baja</option>
          </select>
        </div>

        <div className="min-w-0 sm:min-w-[160px]">
          <label className="go-eyebrow mb-1.5 block">Estado</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="go-select"
          >
            <option value="">Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="aprobado">Aprobado</option>
            <option value="rechazado">Rechazado</option>
          </select>
        </div>

        {(filterCreator || filterBrand || filterPriority || filterStatus) && (
          <div className="flex items-end">
            <button
              onClick={() => {
                setFilterCreator("");
                setFilterBrand("");
                setFilterPriority("");
                setFilterStatus("");
              }}
              className="btn-go-ghost text-xs px-3 py-1.5"
            >
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {/* ── Error ─────────────────────────────────────────────────────── */}
      {error && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{
            background: "rgba(229,62,62,0.08)",
            borderColor: "rgba(229,62,62,0.25)",
            color: "var(--go-error)",
          }}
        >
          {error}
        </div>
      )}

      {/* ── Loading ───────────────────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div
            className="h-8 w-8 animate-spin rounded-full border-[3px]"
            style={{
              borderColor: "var(--go-border)",
              borderTopColor: "var(--go-orange)",
            }}
          />
          <span
            className="ml-3 font-body text-sm"
            style={{ color: "var(--go-text-secondary)" }}
          >
            Cargando transacciones...
          </span>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && sortedTickets.length === 0 && (
        <div
          className="flex flex-col items-center justify-center py-16 font-body text-sm"
          style={{ color: "var(--go-text-secondary)" }}
        >
          <svg
            className="mb-3 h-10 w-10"
            fill="none"
            stroke="currentColor"
            strokeWidth={1}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p>No hay transacciones registradas.</p>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────── */}
      {!loading && sortedTickets.length > 0 && (
        <div className="go-table-scroll-wrapper">
        <div
          className="overflow-x-auto rounded-go-lg border go-table-scroll"
          style={{ borderColor: "var(--go-border)" }}
        >
          <table className="go-table">
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
                <th className="text-center">Estado</th>
                <th className="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {pageTickets.map((t) => (
                <tr key={t.id}>
                  <td style={{ color: "var(--go-text-secondary)" }}>
                    {formatDate(t.upload_date)}
                  </td>
                  <td>
                    <span
                      className="font-display text-sm font-semibold"
                      style={{ color: "var(--go-text-primary)" }}
                    >
                      {t.creator_name || `ID ${t.creator_id}`}
                    </span>
                  </td>
                  <td style={{ color: "var(--go-text-primary)" }}>
                    <div className="flex items-center gap-2">
                      <span>{t.brand_name || `ID ${t.brand_id}`}</span>
                      {t.brand_priority && (
                        <span className={`go-badge ${PRIORITY_BADGE_CLASS[t.brand_priority] || "go-badge-warning"}`}>
                          {PRIORITY_LABELS[t.brand_priority] || t.brand_priority}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="num text-right font-semibold" style={{ color: "var(--go-warning)" }}>
                    {formatCurrency(t.amount)}
                  </td>
                  <td className="text-center">
                    <span
                      className={`go-badge ${STATUS_BADGE_CLASS[t.status] || "go-badge-warning"}`}
                      title={t.status === "rechazado" && t.rejection_reason ? `Motivo: ${t.rejection_reason}` : undefined}
                    >
                      {STATUS_LABELS[t.status] || t.status}
                    </span>
                  </td>
                  <td className="text-center">
                    <RowActions
                      actions={[
                        { key: "ver", label: "Ver", onClick: () => setViewerTicket(t) },
                        canDelete && {
                          key: "eliminar",
                          label: "Eliminar",
                          variant: "danger",
                          onClick: () => setDeleteTarget(t),
                        },
                      ]}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* ── Pagination footer ─────────────────────────────────────── */}
          <div
            className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
            style={{ borderTop: "1px solid var(--go-border)" }}
          >
            <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
              <span className="hidden sm:inline">
                Mostrando {rangeStart}–{rangeEnd} de {sortedTickets.length}
              </span>
              <span className="sm:hidden">
                {rangeStart}–{rangeEnd}/{sortedTickets.length}
              </span>
            </span>

            <div className="flex flex-wrap items-center gap-3">
              <label
                className="hidden sm:inline font-body text-xs"
                style={{ color: "var(--go-text-secondary)" }}
              >
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
                {PAGE_SIZES.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="btn-go-ghost px-2.5 py-1.5 disabled:opacity-40 disabled:pointer-events-none"
                  title="Página anterior"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span
                  className="font-body text-xs tabular-nums"
                  style={{ color: "var(--go-text-secondary)" }}
                >
                  Página {currentPage} de {totalPages}
                </span>
                <button
                  onClick={() => setPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="btn-go-ghost px-2.5 py-1.5 disabled:opacity-40 disabled:pointer-events-none"
                  title="Página siguiente"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        </div>
      )}

      {viewerTicket && <MediaViewerModal ticket={viewerTicket} onClose={() => setViewerTicket(null)} />}

      {deleteTarget && (
        <DeleteConfirmModal
          itemLabel={`el ticket de ${deleteTarget.creator_name || `ID ${deleteTarget.creator_id}`} por ${formatCurrency(deleteTarget.amount)}`}
          onClose={() => setDeleteTarget(null)}
          onSoftDelete={async () => {
            await softDeleteTicket(deleteTarget.id);
            setReloadToken((n) => n + 1);
            if (onChange) onChange();
          }}
          onHardDelete={async () => {
            await hardDeleteTicket(deleteTarget.id);
            setReloadToken((n) => n + 1);
            if (onChange) onChange();
          }}
        />
      )}
    </div>
  );
}
