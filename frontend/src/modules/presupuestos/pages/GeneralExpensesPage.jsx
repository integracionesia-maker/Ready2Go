import { useState, useEffect, useCallback } from "react";
import DateRangeFilter from "../components/DateRangeFilter";
import DeleteConfirmModal from "../components/DeleteConfirmModal";
import GeneralExpenseModal from "../components/GeneralExpenseModal";
import GeneralExpensesExportModal from "../components/GeneralExpensesExportModal";
import RubrosManagerModal from "../components/RubrosManagerModal";
import { GlassPanel, RowActions, ICONS, MediaViewer, usePageTitle, SortableHeaderCell, useSortable } from "@/design";
import {
  fetchGeneralExpenses,
  softDeleteGeneralExpense,
  hardDeleteGeneralExpense,
  generalExpenseFileUrl,
  listOperationalExpenses,
  softDeleteOperationalExpense,
  operationalExpenseFileUrl,
  listRubros,
} from "@/api";

import { formatMXN } from "@/design";

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

// `fecha_gasto` de un gasto operativo es solo fecha ("YYYY-MM-DD"), sin hora —
// a diferencia de `upload_date` (general), que sí trae hora.
function formatDateSolo(iso) {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("es-MX", { year: "numeric", month: "short", day: "numeric" });
}

function fmtDateParam(d) {
  if (!d) return undefined;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const SORTABLE_COLUMNS = [
  { key: "tipo", label: "Tipo", type: "string" },
  { key: "fechaOrden", label: "Fecha", type: "date" },
  { key: "etiqueta", label: "Marca / Rubro", type: "string" },
  { key: "description", label: "Descripción", type: "string" },
  { key: "amount", label: "Monto", type: "number", align: "right" },
];

function firstOfMonth(y, m) {
  return new Date(y, m, 1);
}

function today() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}

// Normaliza gastos generales y operativos a una forma común de fila. La
// "fecha que manda" difiere por tipo: `upload_date` para general (fecha de
// subida), `fecha_gasto` para operativo (fecha manual, define el mes) — cada
// tipo ya se filtró/ordenó en el backend por su propio campo semántico; aquí
// solo se elige qué campo mostrar en la columna "Fecha".
function normalizeGeneral(e) {
  return {
    id: e.id,
    tipo: "general",
    fechaOrden: e.upload_date,
    fechaLabel: formatDate(e.upload_date),
    etiqueta: e.brand_name || `ID ${e.brand_id}`,
    description: e.description,
    amount: e.amount,
    raw: e,
  };
}

function normalizeOperativo(e) {
  return {
    id: e.id,
    tipo: "operativo",
    fechaOrden: e.fecha_gasto,
    fechaLabel: formatDateSolo(e.fecha_gasto),
    etiqueta: e.rubro_nombre || `ID ${e.rubro_id}`,
    description: e.description,
    amount: e.amount,
    raw: e,
  };
}

export default function GeneralExpensesPage({ brands = [] }) {
  usePageTitle("Gastos Generales");
  const [rows, setRows] = useState([]);
  const [rubros, setRubros] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [dateRange, setDateRange] = useState(() => {
    const t = today();
    return { start: firstOfMonth(t.getFullYear(), t.getMonth()), end: t };
  });

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [rubrosModalOpen, setRubrosModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [viewerRow, setViewerRow] = useState(null);

  const { sortedItems: sortedRows, sortKey, sortDir, cycleSort } = useSortable(rows, SORTABLE_COLUMNS);

  const loadRubros = useCallback(() => {
    listRubros(false)
      .then(setRubros)
      .catch(() => {}); // el selector del modal simplemente queda vacío si falla
  }, []);

  const loadExpenses = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const startDate = fmtDateParam(dateRange.start);
    const endDate = fmtDateParam(dateRange.end);

    Promise.all([
      fetchGeneralExpenses({ startDate, endDate }),
      listOperationalExpenses({ startDate, endDate }),
    ])
      .then(([generales, operativos]) => {
        if (cancelled) return;
        const combinados = [
          ...generales.map(normalizeGeneral),
          ...operativos.map(normalizeOperativo),
        ].sort((a, b) => (a.fechaOrden < b.fechaOrden ? 1 : a.fechaOrden > b.fechaOrden ? -1 : 0));
        setRows(combinados);
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
  }, [dateRange]);

  useEffect(() => {
    const cancel = loadExpenses();
    return cancel;
  }, [loadExpenses]);

  useEffect(() => {
    loadRubros();
  }, [loadRubros]);

  const handleExpenseCreated = () => {
    setCreateModalOpen(false);
    loadExpenses();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h2
          className="font-display text-lg font-bold uppercase tracking-[0.06em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Gastos Generales
        </h2>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <button type="button" onClick={() => setRubrosModalOpen(true)} className="btn-go-ghost w-full sm:w-auto">
            Gestionar rubros
          </button>
          <button type="button" onClick={() => setExportModalOpen(true)} className="btn-go-ghost w-full sm:w-auto">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Exportar
          </button>
          <button type="button" onClick={() => setCreateModalOpen(true)} className="btn-go w-full sm:w-auto">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Nuevo Gasto
          </button>
        </div>
      </div>

      {/* ── Date filter ──────────────────────────────────────────────── */}
      <GlassPanel className="p-4 sm:p-6">
        <DateRangeFilter
          startDate={dateRange.start}
          endDate={dateRange.end}
          onChange={(start, end) => setDateRange({ start, end })}
        />
      </GlassPanel>

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
            Cargando gastos...
          </span>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && rows.length === 0 && (
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
          <p>No hay gastos registrados.</p>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────── */}
      {!loading && rows.length > 0 && (
        <GlassPanel className="p-4 sm:p-6">
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
                  <th className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row) => (
                  <tr key={`${row.tipo}-${row.id}`}>
                    <td>
                      {/* Distintivo visual: naranja GO para general, turquesa para operativo. */}
                      <span
                        className="go-badge whitespace-nowrap"
                        style={
                          row.tipo === "general"
                            ? { background: "rgba(251,103,11,0.12)", color: "var(--go-orange)" }
                            : { background: "rgba(0,163,182,0.12)", color: "#00A3B6" }
                        }
                      >
                        {row.tipo === "general" ? "General" : "Operativo"}
                      </span>
                    </td>
                    <td style={{ color: "var(--go-text-secondary)" }}>{row.fechaLabel}</td>
                    <td>
                      <span className="font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                        {row.etiqueta}
                      </span>
                    </td>
                    <td style={{ color: "var(--go-text-primary)" }}>{row.description}</td>
                    <td className="num text-right font-semibold" style={{ color: "var(--go-warning)" }}>
                      {formatMXN(row.amount)}
                    </td>
                    <td className="text-center">
                      <RowActions
                        actions={[
                          {
                            key: "ver",
                            label: "Ver",
                            icon: ICONS.ver,
                            onClick: () => setViewerRow(row),
                          },
                          {
                            key: "eliminar",
                            label: "Eliminar",
                            icon: ICONS.eliminar,
                            variant: "danger",
                            onClick: () => setDeleteTarget(row),
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

      {createModalOpen && (
        <GeneralExpenseModal
          brands={brands}
          rubros={rubros}
          onClose={() => setCreateModalOpen(false)}
          onSuccess={handleExpenseCreated}
        />
      )}

      {exportModalOpen && <GeneralExpensesExportModal onClose={() => setExportModalOpen(false)} />}

      {rubrosModalOpen && (
        <RubrosManagerModal onClose={() => setRubrosModalOpen(false)} onChange={loadRubros} />
      )}

      {viewerRow && (
        <MediaViewer
          url={viewerRow.tipo === "general" ? generalExpenseFileUrl(viewerRow.id) : operationalExpenseFileUrl(viewerRow.id)}
          fileName={viewerRow.raw.file_name}
          mimeType={viewerRow.raw.mime_type || ""}
          title={`Comprobante — ${viewerRow.description}`}
          onClose={() => setViewerRow(null)}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmModal
          itemLabel={`"${deleteTarget.description}" (${formatMXN(deleteTarget.amount)})`}
          onClose={() => setDeleteTarget(null)}
          onSoftDelete={async () => {
            if (deleteTarget.tipo === "general") await softDeleteGeneralExpense(deleteTarget.id);
            else await softDeleteOperationalExpense(deleteTarget.id);
            loadExpenses();
          }}
          // Gastos operativos: solo borrado lógico (sin `onHardDelete`, el
          // modal omite la opción de borrado físico — ver DeleteConfirmModal.jsx).
          onHardDelete={
            deleteTarget.tipo === "general"
              ? async () => {
                  await hardDeleteGeneralExpense(deleteTarget.id);
                  loadExpenses();
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
