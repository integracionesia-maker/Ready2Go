import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { EmptyState, GlassPanel, SkeletonShimmer, RowActions, ICONS, usePageTitle, SortableHeaderCell, useSortable } from "@/design";
import { esCodigo } from "@/api";
import { fetchEquipmentList } from "../api";
import { usePermisos } from "../permisos/usePermisos";
import RequierePermiso from "../permisos/RequierePermiso";
import EquipmentCard from "../components/EquipmentCard";
import EquipmentFormModal from "../components/EquipmentFormModal";
import EquipmentAuditModal from "../components/EquipmentAuditModal";
import EquipmentFichaModal from "../components/EquipmentFichaModal";

const LIMIT = 20;

const CONDICION_BADGE = { bueno: "go-badge-success", atencion: "go-badge-warning" };

const SORTABLE_COLUMNS = [
  { key: "nombre", label: "Nombre", type: "string" },
  { key: "categoria", label: "Categoría", type: "string" },
  { key: "condicion", label: "Condición", type: "string", getValue: (e) => e.condicion || "sin auditar" },
  { key: "disponible", label: "Disponibilidad", type: "string", getValue: (e) => (e.disponible ? "Disponible" : "No disponible") },
  { key: "tenedor", label: "Con", type: "string", getValue: (e) => e.tenedor_actual?.nombre || "" },
];

function useUrlFilters() {
  const [params, setParams] = useSearchParams();

  const filtros = useMemo(
    () => ({
      q: params.get("q") || "",
      categoria: params.get("categoria") || "",
      condicion: params.get("condicion") || "",
      disponible: params.get("disponible") || "",
      offset: Number(params.get("offset") || 0),
      limit: Number(params.get("limit") || LIMIT),
    }),
    [params]
  );

  function set(patch) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(patch)) {
      if (value === "" || value == null) next.delete(key);
      else next.set(key, String(value));
    }
    // Cualquier cambio de filtro regresa a la primera página — un filtro
    // nuevo con un offset viejo puede caer fuera de rango y verse "vacío".
    if (!("offset" in patch)) next.delete("offset");
    setParams(next, { replace: true });
  }

  return { filtros, set };
}

export default function InventarioPage() {
  usePageTitle("Inventario");
  const { puede } = usePermisos();
  const { filtros, set } = useUrlFilters();

  // Input local + debounce: "q" es el único filtro que dispara una petición
  // por cada cambio, así que sincroniza a la URL 300ms después de que la
  // persona deja de teclear, no en cada tecla.
  const [qInput, setQInput] = useState(filtros.q);
  useEffect(() => {
    const t = setTimeout(() => {
      if (qInput !== filtros.q) set({ q: qInput });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qInput]);

  const [vista, setVista] = useState("grid");
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);

  const [categoriasConocidas, setCategoriasConocidas] = useState([]);

  const [modalCrear, setModalCrear] = useState(false);
  const [modalEditar, setModalEditar] = useState(null);
  const [modalAuditar, setModalAuditar] = useState(null);
  const [fichaId, setFichaId] = useState(null);

  const { sortedItems: sortedEquipos, sortKey, sortDir, cycleSort } = useSortable(
    resultado?.items || [],
    SORTABLE_COLUMNS
  );

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    try {
      const data = await fetchEquipmentList({
        q: filtros.q || undefined,
        categoria: filtros.categoria || undefined,
        condicion: filtros.condicion || undefined,
        disponible: filtros.disponible || undefined,
        limit: filtros.limit,
        offset: filtros.offset,
      });
      setResultado(data);
      if (categoriasConocidas.length === 0) {
        // Semilla única de opciones de filtro: no hay enum de categorías en
        // el contrato (es texto libre), así que se aprende del propio
        // inventario en vez de inventar una lista fija.
        const todas = await fetchEquipmentList({ limit: 200 });
        setCategoriasConocidas([...new Set(todas.items.map((i) => i.categoria))].sort());
      }
    } catch (e) {
      if (esCodigo(e, "PERMISOS_NO_DISPONIBLES")) {
        setPermisosNoDisponibles(true);
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.q, filtros.categoria, filtros.condicion, filtros.disponible, filtros.offset, filtros.limit]);

  const totalPages = resultado ? Math.max(1, Math.ceil(resultado.total / filtros.limit)) : 1;
  const currentPage = Math.floor(filtros.offset / filtros.limit) + 1;
  const rangeStart = resultado && resultado.total > 0 ? filtros.offset + 1 : 0;
  const rangeEnd = resultado ? Math.min(filtros.offset + filtros.limit, resultado.total) : 0;

  if (loading && !resultado) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonShimmer key={i} className="h-32" />
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
          Inventario <span style={{ color: "var(--go-orange)" }}>({resultado.total})</span>
        </h1>
        <div className="flex items-center gap-2">
          {/* Switch rejilla / tabla — solo iconos, estilo toggle */}
          <div className="flex items-center rounded-go p-0.5" style={{ background: "var(--go-surface)" }}>
            <button
              type="button"
              onClick={() => setVista("grid")}
              title="Vista en rejilla"
              aria-label="Vista en rejilla"
              aria-pressed={vista === "grid"}
              className={`flex h-8 w-8 items-center justify-center rounded-go transition-all duration-200 ${
                vista === "grid"
                  ? "text-white"
                  : "hover:text-white/70"
              }`}
              style={{ background: vista === "grid" ? "var(--go-orange)" : "transparent", color: vista === "grid" ? "#fff" : "var(--go-text-secondary)" }}
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => setVista("tabla")}
              title="Vista en tabla"
              aria-label="Vista en tabla"
              aria-pressed={vista === "tabla"}
              className={`flex h-8 w-8 items-center justify-center rounded-go transition-all duration-200 ${
                vista === "tabla"
                  ? "text-white"
                  : "hover:text-white/70"
              }`}
              style={{ background: vista === "tabla" ? "var(--go-orange)" : "transparent", color: vista === "tabla" ? "#fff" : "var(--go-text-secondary)" }}
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.6} viewBox="0 0 24 24">
                {/* Borde exterior — marco de la tabla */}
                <rect x="3" y="4" width="18" height="16" rx="2" strokeLinecap="round" strokeLinejoin="round" />
                {/* Header */}
                <path d="M3 9h18M8 4v16M14 4v16" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
          <RequierePermiso modulo="equipos_inventario" accion="crear">
            <button type="button" onClick={() => setModalCrear(true)} className="btn-go">
              <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Nuevo equipo
            </button>
          </RequierePermiso>
        </div>
      </div>

      {/* Filtros en la URL: sobreviven a un F5, se pueden compartir por link. */}
      <GlassPanel className="flex flex-wrap items-end gap-3 p-4 sm:p-5">
        <div className="min-w-[180px] flex-1">
          <label className="go-eyebrow mb-1.5 block">Buscar</label>
          <input
            type="text"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            placeholder="Nombre del equipo..."
            className="go-input"
          />
        </div>
        <div className="min-w-[160px]">
          <label className="go-eyebrow mb-1.5 block">Categoría</label>
          <select value={filtros.categoria} onChange={(e) => set({ categoria: e.target.value })} className="go-select">
            <option value="">Todas</option>
            {categoriasConocidas.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-[140px]">
          <label className="go-eyebrow mb-1.5 block">Condición</label>
          <select value={filtros.condicion} onChange={(e) => set({ condicion: e.target.value })} className="go-select">
            <option value="">Todas</option>
            <option value="bueno">Bueno</option>
            <option value="atencion">Atención</option>
          </select>
        </div>
        <div className="min-w-[140px]">
          <label className="go-eyebrow mb-1.5 block">Disponibilidad</label>
          <select value={filtros.disponible} onChange={(e) => set({ disponible: e.target.value })} className="go-select">
            <option value="">Todas</option>
            <option value="true">Disponible</option>
            <option value="false">No disponible</option>
          </select>
        </div>
      </GlassPanel>

      {resultado.items.length === 0 ? (
        <EmptyState title="Sin equipos" message="Ningún equipo coincide con estos filtros." />
      ) : vista === "grid" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {resultado.items.map((eq) => (
            <EquipmentCard key={eq.id} equipo={eq} onClick={(e) => setFichaId(e.id)} />
          ))}
        </div>
      ) : (
        <GlassPanel className="p-4 sm:p-6">
          <div className="go-table-scroll-wrapper">
            <div
              className="overflow-x-auto rounded-go-lg border go-table-scroll"
              style={{ borderColor: "var(--go-border)" }}
            >
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
                  {sortedEquipos.map((eq) => (
                    <tr key={eq.id} className="cursor-pointer" onClick={() => setFichaId(eq.id)}>
                      <td>{eq.nombre}</td>
                      <td>{eq.categoria}</td>
                      <td>
                        <span className={`go-badge ${CONDICION_BADGE[eq.condicion] || "go-badge-neutral"}`}>
                          {eq.condicion || "sin auditar"}
                        </span>
                      </td>
                      <td>
                        <span className={`go-badge ${eq.disponible ? "go-badge-success" : "go-badge-neutral"}`}>
                          {eq.disponible ? "Disponible" : "No disponible"}
                        </span>
                      </td>
                      <td>
                        {eq.tenedor_actual?.nombre || "—"}
                        {eq.atrasado && <span className="go-badge go-badge-error ml-2">Atrasado {eq.dias_atraso}d</span>}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <RowActions
                          actions={[
                            { key: "ficha", label: "Ver ficha", icon: ICONS.ver, onClick: () => setFichaId(eq.id) },
                            puede("equipos_inventario", "editar") && {
                              key: "editar",
                              label: "Editar",
                              icon: ICONS.editar,
                              onClick: () => setModalEditar(eq),
                            },
                            puede("equipos_inventario", "auditar_condicion") && {
                              key: "auditar",
                              label: "Auditar",
                              icon: ICONS.auditar,
                              onClick: () => setModalAuditar(eq),
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
            value={filtros.limit}
            onChange={(e) => set({ limit: Number(e.target.value) })}
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
              disabled={filtros.offset === 0}
              onClick={() => set({ offset: Math.max(0, filtros.offset - filtros.limit) })}
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
              onClick={() => set({ offset: filtros.offset + filtros.limit })}
              className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>
      )}

      {modalCrear && (
        <EquipmentFormModal
          onClose={() => setModalCrear(false)}
          onSuccess={() => {
            setModalCrear(false);
            cargar();
          }}
        />
      )}
      {modalEditar && (
        <EquipmentFormModal
          equipo={modalEditar}
          onClose={() => setModalEditar(null)}
          onSuccess={() => {
            setModalEditar(null);
            cargar();
          }}
        />
      )}
      {modalAuditar && (
        <EquipmentAuditModal
          equipo={modalAuditar}
          onClose={() => setModalAuditar(null)}
          onSuccess={() => {
            setModalAuditar(null);
            cargar();
          }}
        />
      )}
      {fichaId != null && (
        <EquipmentFichaModal
          equipoId={fichaId}
          onClose={() => setFichaId(null)}
          onEditar={(eq) => {
            setFichaId(null);
            setModalEditar(eq);
          }}
          onAuditar={(eq) => {
            setFichaId(null);
            setModalAuditar(eq);
          }}
          onCambio={cargar}
        />
      )}
    </div>
  );
}
