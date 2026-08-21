import { useCallback, useEffect, useState } from "react";
import { GlassPanel, RowActions, ICONS, MediaViewer } from "@/design";
import DateRangeFilter from "@/modules/presupuestos/components/DateRangeFilter";
import DeleteConfirmModal from "@/modules/presupuestos/components/DeleteConfirmModal";
import GastoModal from "../components/GastoModal";
import {
  listRubros,
  listOperationalExpenses,
  operationalExpenseFileUrl,
  softDeleteOperationalExpense,
} from "../api";

function formatCurrency(n) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", minimumFractionDigits: 2 }).format(n || 0);
}

function formatDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-MX", { year: "numeric", month: "short", day: "numeric" });
}

function firstOfMonth() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), 1);
}

export default function RegistroPage() {
  const [rubros, setRubros] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [viewer, setViewer] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [rubroFiltro, setRubroFiltro] = useState("");
  const [range, setRange] = useState({ start: firstOfMonth(), end: new Date() });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rbs, exp] = await Promise.all([
        listRubros(false),
        listOperationalExpenses({ rubroId: rubroFiltro || undefined, startDate: range.start, endDate: range.end }),
      ]);
      setRubros(rbs);
      setExpenses(exp);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [rubroFiltro, range]);

  useEffect(() => { load(); }, [load]);

  const total = expenses.reduce((s, e) => s + (e.amount || 0), 0);
  const rubrosActivos = rubros.filter((r) => r.is_active);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-xl font-bold uppercase tracking-[0.04em]" style={{ color: "var(--go-text-primary)" }}>
          Gastos Operativos
        </h1>
        <button onClick={() => setModalOpen(true)} className="btn-go" disabled={rubrosActivos.length === 0}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Gasto
        </button>
      </div>

      {rubrosActivos.length === 0 && !loading && (
        <GlassPanel className="p-4 font-body text-sm" >
          <span style={{ color: "var(--go-text-secondary)" }}>
            No hay rubros activos. Crea uno en la sección Rubros antes de registrar gastos.
          </span>
        </GlassPanel>
      )}

      <GlassPanel className="space-y-4 p-4 sm:p-6">
        <div className="flex flex-wrap items-end gap-3">
          <DateRangeFilter startDate={range.start} endDate={range.end} onChange={(s, e) => setRange({ start: s, end: e })} />
          <div className="min-w-[160px]">
            <label className="go-eyebrow mb-1.5 block">Rubro</label>
            <select value={rubroFiltro} onChange={(e) => setRubroFiltro(e.target.value)} className="go-select">
              <option value="">Todos</option>
              {rubros.map((r) => (
                <option key={r.id} value={r.id}>{r.nombre}</option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="rounded-go border px-4 py-3 font-body text-sm" style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}>
            {error}
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="go-eyebrow">{expenses.length} gastos</span>
          <span className="font-mono text-lg font-semibold" style={{ color: "var(--go-warning)" }}>
            Total: {formatCurrency(total)}
          </span>
        </div>

        {loading ? (
          <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Cargando...</p>
        ) : expenses.length === 0 ? (
          <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Sin gastos en este periodo.
          </p>
        ) : (
          <div className="go-table-scroll-wrapper">
            <div className="overflow-x-auto go-table-scroll rounded-go-lg border" style={{ borderColor: "var(--go-border)" }}>
              <table className="go-table w-full">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Rubro</th>
                    <th>Descripción</th>
                    <th className="text-right">Monto</th>
                    <th className="text-right" />
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((e) => (
                    <tr key={e.id}>
                      <td className="whitespace-nowrap">{formatDate(e.fecha_gasto)}</td>
                      <td>
                        <span className="go-badge whitespace-nowrap" style={{ background: "var(--go-surface-sunken)", color: "var(--go-text-secondary)" }}>
                          {e.rubro_nombre || `#${e.rubro_id}`}
                        </span>
                      </td>
                      <td style={{ color: "var(--go-text-primary)" }}>{e.description}</td>
                      <td className="num text-right font-semibold" style={{ color: "var(--go-warning)" }}>{formatCurrency(e.amount)}</td>
                      <td>
                        <RowActions
                          actions={[
                            { key: "ver", label: "Ver comprobante", icon: ICONS.ver, onClick: () => setViewer(e) },
                            { key: "eliminar", label: "Eliminar", icon: ICONS.eliminar, variant: "danger", onClick: () => setDeleteTarget(e) },
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
      </GlassPanel>

      {modalOpen && (
        <GastoModal
          rubros={rubrosActivos}
          onClose={() => setModalOpen(false)}
          onSuccess={() => { setModalOpen(false); load(); }}
        />
      )}

      {viewer && (
        <MediaViewer
          url={operationalExpenseFileUrl(viewer.id)}
          fileName={viewer.file_name}
          mimeType={viewer.mime_type || ""}
          title={`Comprobante — ${viewer.description}`}
          onClose={() => setViewer(null)}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmModal
          itemLabel={`"${deleteTarget.description}" (${formatCurrency(deleteTarget.amount)})`}
          onClose={() => setDeleteTarget(null)}
          onSoftDelete={async () => {
            await softDeleteOperationalExpense(deleteTarget.id);
            load();
          }}
        />
      )}
    </div>
  );
}
