import { useState, useEffect, useCallback } from "react";
import DateRangeFilter from "../components/DateRangeFilter";
import DeleteConfirmModal from "../components/DeleteConfirmModal";
import GeneralExpenseModal from "../components/GeneralExpenseModal";
import GeneralExpensesExportModal from "../components/GeneralExpensesExportModal";
import { RowActions, ICONS } from "@/design";
import { fetchGeneralExpenses, softDeleteGeneralExpense, hardDeleteGeneralExpense, generalExpenseFileUrl } from "@/api";

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

function fmtDateParam(d) {
  if (!d) return undefined;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function firstOfMonth(y, m) {
  return new Date(y, m, 1);
}

function today() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}

export default function GeneralExpensesPage({ brands = [] }) {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [dateRange, setDateRange] = useState(() => {
    const t = today();
    return { start: firstOfMonth(t.getFullYear(), t.getMonth()), end: t };
  });

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const loadExpenses = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchGeneralExpenses({
      startDate: fmtDateParam(dateRange.start),
      endDate: fmtDateParam(dateRange.end),
    })
      .then((data) => {
        if (!cancelled) setExpenses(data);
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
            Nuevo Gasto General
          </button>
        </div>
      </div>

      {/* ── Date filter ──────────────────────────────────────────────── */}
      <DateRangeFilter
        startDate={dateRange.start}
        endDate={dateRange.end}
        onChange={(start, end) => setDateRange({ start, end })}
      />

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
            Cargando gastos generales...
          </span>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────────────── */}
      {!loading && expenses.length === 0 && (
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
          <p>No hay gastos generales registrados.</p>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────── */}
      {!loading && expenses.length > 0 && (
        <div className="go-table-scroll-wrapper">
          <div
            className="overflow-x-auto rounded-go-lg border go-table-scroll"
            style={{ borderColor: "var(--go-border)" }}
          >
            <table className="go-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Marca</th>
                  <th>Descripción</th>
                  <th className="text-right">Monto</th>
                  <th className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((expense) => (
                  <tr key={expense.id}>
                    <td style={{ color: "var(--go-text-secondary)" }}>
                      {formatDate(expense.upload_date)}
                    </td>
                    <td>
                      <span className="font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                        {expense.brand_name || `ID ${expense.brand_id}`}
                      </span>
                    </td>
                    <td style={{ color: "var(--go-text-primary)" }}>
                      {expense.description}
                    </td>
                    <td className="num text-right font-semibold" style={{ color: "var(--go-warning)" }}>
                      {formatCurrency(expense.amount)}
                    </td>
                    <td className="text-center">
                      <RowActions
                        actions={[
                          {
                            key: "ver",
                            label: "Ver",
                            icon: ICONS.ver,
                            onClick: () =>
                              window.open(generalExpenseFileUrl(expense.id), "_blank", "noopener,noreferrer"),
                          },
                          {
                            key: "eliminar",
                            label: "Eliminar",
                            icon: ICONS.eliminar,
                            variant: "danger",
                            onClick: () => setDeleteTarget(expense),
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
      )}

      {createModalOpen && (
        <GeneralExpenseModal brands={brands} onClose={() => setCreateModalOpen(false)} onSuccess={handleExpenseCreated} />
      )}

      {exportModalOpen && <GeneralExpensesExportModal onClose={() => setExportModalOpen(false)} />}

      {deleteTarget && (
        <DeleteConfirmModal
          itemLabel={`"${deleteTarget.description}" (${formatCurrency(deleteTarget.amount)})`}
          onClose={() => setDeleteTarget(null)}
          onSoftDelete={async () => {
            await softDeleteGeneralExpense(deleteTarget.id);
            loadExpenses();
          }}
          onHardDelete={async () => {
            await hardDeleteGeneralExpense(deleteTarget.id);
            loadExpenses();
          }}
        />
      )}
    </div>
  );
}
