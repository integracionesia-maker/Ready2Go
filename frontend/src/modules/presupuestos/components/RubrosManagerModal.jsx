import { useCallback, useEffect, useState } from "react";
import { GlassPanel, RowActions, ICONS, SortableHeaderCell, useSortable } from "@/design";
import Modal from "./Modal";
import { listRubros, createRubro, updateRubro } from "@/api";

const SORTABLE_COLUMNS = [
  { key: "nombre", label: "Rubro", type: "string" },
  {
    key: "is_active",
    label: "Estado",
    type: "string",
    align: "center",
    getValue: (r) => (r.is_active ? "Activo" : "Inactivo"),
  },
];

function RubroFormModal({ rubro, onClose, onSuccess }) {
  const [nombre, setNombre] = useState(rubro?.nombre || "");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const editando = Boolean(rubro);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!nombre.trim()) return setError("El nombre es obligatorio.");
    setSubmitting(true);
    try {
      if (editando) await updateRubro(rubro.id, { nombre: nombre.trim() });
      else await createRubro(nombre.trim());
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title={editando ? "Editar rubro" : "Nuevo rubro"} onClose={onClose} submitting={submitting}>
      <form onSubmit={submit} className="space-y-4 px-4 sm:px-6 py-5">
        <div>
          <label className="go-eyebrow mb-1.5 block">Nombre del rubro</label>
          <input type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} className="go-input" maxLength={100} required autoFocus />
        </div>
        {error && (
          <div className="rounded-go border px-4 py-3 font-body text-sm" style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}>
            {error}
          </div>
        )}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">Cancelar</button>
          <button type="submit" disabled={submitting} className="btn-go">{submitting ? "Guardando..." : editando ? "Guardar" : "Crear"}</button>
        </div>
      </form>
    </Modal>
  );
}

/** Gestión de rubros (catálogo de Gastos Operativos), abierta como modal
 * desde Gastos Generales — crear/editar/activar-desactivar. */
export default function RubrosManagerModal({ onClose, onChange }) {
  const [rubros, setRubros] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [subModal, setSubModal] = useState(null); // null | "crear" | rubro (editar)

  const { sortedItems: sortedRubros, sortKey, sortDir, cycleSort } = useSortable(rubros, SORTABLE_COLUMNS);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRubros(await listRubros(false));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleActivo = async (r) => {
    setError(null);
    try {
      await updateRubro(r.id, { is_active: !r.is_active });
      load();
      onChange?.();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <Modal title="Gestionar rubros" onClose={onClose}>
      <div className="space-y-4 px-4 sm:px-6 py-5">
        <div className="flex items-center justify-end">
          <button type="button" onClick={() => setSubModal("crear")} className="btn-go">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Nuevo rubro
          </button>
        </div>

        {error && (
          <div className="rounded-go border px-4 py-3 font-body text-sm" style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}>
            {error}
          </div>
        )}

        {loading ? (
          <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Cargando...</p>
        ) : rubros.length === 0 ? (
          <p className="py-10 text-center font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            No hay rubros. Crea el primero.
          </p>
        ) : (
          <GlassPanel className="p-0">
            <div className="go-table-scroll-wrapper">
              <div className="overflow-x-auto go-table-scroll rounded-go-lg border" style={{ borderColor: "var(--go-border)" }}>
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
                      <th className="text-right" />
                    </tr>
                  </thead>
                  <tbody>
                    {sortedRubros.map((r) => (
                      <tr key={r.id}>
                        <td className="font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>{r.nombre}</td>
                        <td className="text-center">
                          <span className={`go-badge whitespace-nowrap ${r.is_active ? "go-badge-success" : "go-badge-error"}`}>
                            {r.is_active ? "Activo" : "Inactivo"}
                          </span>
                        </td>
                        <td>
                          <RowActions
                            actions={[
                              { key: "editar", label: "Editar", icon: ICONS.editar, onClick: () => setSubModal(r) },
                              {
                                key: "toggle",
                                label: r.is_active ? "Desactivar" : "Activar",
                                icon: ICONS.toggle,
                                variant: r.is_active ? "danger" : undefined,
                                onClick: () => toggleActivo(r),
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
      </div>

      {subModal && (
        <RubroFormModal
          rubro={subModal === "crear" ? null : subModal}
          onClose={() => setSubModal(null)}
          onSuccess={() => {
            setSubModal(null);
            load();
            onChange?.();
          }}
        />
      )}
    </Modal>
  );
}
