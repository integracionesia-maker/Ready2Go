import { useEffect, useMemo, useState } from "react";
import Modal from "../components/Modal";
import DateRangeFilter from "../components/DateRangeFilter";
import { GlassPanel, ICONS } from "@/design";
import { fetchAuditLogs, fetchUsers } from "@/api";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

const METHOD_BADGE = {
  GET: "go-badge-success",
  POST: "go-badge-neutral",
  PUT: "go-badge-warning",
  PATCH: "go-badge-warning",
  DELETE: "go-badge-error",
};

function statusBadgeClass(status) {
  if (!status) return "go-badge-neutral";
  if (status < 300) return "go-badge-success";
  if (status < 400) return "go-badge-neutral";
  if (status < 500) return "go-badge-warning";
  return "go-badge-error";
}

function formatDate(iso) {
  if (!iso) return "—";
  // El backend ahora devuelve created_at con tzinfo (+00:00), y JS lo
  // convierte automaticamente a la zona local del navegador (CDMX = UTC-6).
  return new Date(iso).toLocaleDateString("es-MX", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}

function epochToLocal(epoch) {
  if (epoch == null) return "—";
  return new Date(epoch * 1000).toLocaleDateString("es-MX", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}

function fmtDateParam(d) {
  if (!d) return undefined;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const PAGE_SIZES = [10, 25, 50, 100];

function emptyFilters() {
  return { search: "", actor_user_id: "", http_method: "", response_status: "", startDate: null, endDate: null };
}

/**
 * Vista de auditoría (solo superadmin) — consulta de `audit_log`, que ahora
 * llena tanto el middleware automático (todo request, genérico) como las
 * llamadas manuales ya existentes en los routers (login, altas de usuario,
 * concesión de roles, etc. — con `action`/`target_type` curados).
 */
export default function AuditLogPage() {
  const [users, setUsers] = useState([]);
  const [filters, setFilters] = useState(emptyFilters());
  const [searchInput, setSearchInput] = useState("");

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [detailLog, setDetailLog] = useState(null);

  useEffect(() => {
    fetchUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  // Debounce de 300ms para el input de búsqueda global.
  useEffect(() => {
    const t = setTimeout(() => setFilters((f) => ({ ...f, search: searchInput })), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuditLogs({
        page,
        page_size: pageSize,
        search: filters.search || undefined,
        actor_user_id: filters.actor_user_id || undefined,
        http_method: filters.http_method || undefined,
        response_status: filters.response_status || undefined,
        start_date: fmtDateParam(filters.startDate),
        end_date: fmtDateParam(filters.endDate),
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, filters]);

  const handleFilterChange = (patch) => {
    setPage(1);
    setFilters((f) => ({ ...f, ...patch }));
  };

  const handleClearFilters = () => {
    setSearchInput("");
    setPage(1);
    setFilters(emptyFilters());
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, totalPages);
  const rangeStart = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const rangeEnd = Math.min(currentPage * pageSize, total);

  const userLabelById = useMemo(() => {
    const map = new Map();
    users.forEach((u) => map.set(u.id, `${u.full_name} (${u.username})`));
    return map;
  }, [users]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Auditoría del Sistema <span style={{ color: "var(--go-orange)" }}>({total})</span>
        </h1>
      </div>

      <GlassPanel className="p-4 sm:p-6 space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <label className="go-eyebrow mb-1.5 block">Buscar</label>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Acción, ruta, detalles..."
              className="go-input"
            />
          </div>
          <div className="min-w-[180px]">
            <label className="go-eyebrow mb-1.5 block">Usuario</label>
            <select
              value={filters.actor_user_id}
              onChange={(e) => handleFilterChange({ actor_user_id: e.target.value })}
              className="go-select"
            >
              <option value="">Todos</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.username})
                </option>
              ))}
            </select>
          </div>
          <div className="min-w-[140px]">
            <label className="go-eyebrow mb-1.5 block">Método</label>
            <select
              value={filters.http_method}
              onChange={(e) => handleFilterChange({ http_method: e.target.value })}
              className="go-select"
            >
              <option value="">Todos</option>
              {HTTP_METHODS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="min-w-[140px]">
            <label className="go-eyebrow mb-1.5 block">Status</label>
            <select
              value={filters.response_status}
              onChange={(e) => handleFilterChange({ response_status: e.target.value })}
              className="go-select"
            >
              <option value="">Todos</option>
              {[200, 201, 400, 401, 403, 404, 422, 500, 503].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <button type="button" onClick={handleClearFilters} className="btn-go-ghost">
            Limpiar filtros
          </button>
        </div>

        <DateRangeFilter
          startDate={filters.startDate}
          endDate={filters.endDate}
          onChange={(start, end) => handleFilterChange({ startDate: start, endDate: end })}
        />
      </GlassPanel>

      {error && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div
            className="h-8 w-8 animate-spin rounded-full border-[3px]"
            style={{ borderColor: "var(--go-border)", borderTopColor: "var(--go-orange)" }}
          />
          <span className="ml-3 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Cargando auditoría...
          </span>
        </div>
      ) : logs.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-16 font-body text-sm"
          style={{ color: "var(--go-text-secondary)" }}
        >
          <p>No hay entradas de auditoría con estos filtros.</p>
        </div>
      ) : (
        <GlassPanel className="p-4 sm:p-6">
          <div className="go-table-scroll-wrapper">
            <div className="overflow-x-auto rounded-go-lg border go-table-scroll" style={{ borderColor: "var(--go-border)" }}>
              <table className="go-table w-full">
                <thead>
                  <tr>
                    <th>Fecha/Hora</th>
                    <th>Usuario</th>
                    <th>Acción</th>
                    <th className="text-center">Método</th>
                    <th>Endpoint</th>
                    <th className="text-center">Status</th>
                    <th className="text-right">Duración</th>
                    <th aria-label="Acciones" />
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="cursor-pointer" onClick={() => setDetailLog(log)}>
                      <td className="font-mono text-xs" style={{ color: "var(--go-text-secondary)" }}>
                        {formatDate(log.created_at)}
                      </td>
                      <td style={{ color: "var(--go-text-primary)" }}>
                        {log.actor_full_name || (log.actor_user_id ? `ID ${log.actor_user_id}` : "—")}
                      </td>
                      <td className="font-mono text-xs">{log.action}</td>
                      <td className="text-center">
                        {log.http_method && (
                          <span className={`go-badge ${METHOD_BADGE[log.http_method] || "go-badge-neutral"}`}>
                            {log.http_method}
                          </span>
                        )}
                      </td>
                      <td className="font-mono text-xs" style={{ color: "var(--go-text-secondary)" }}>
                        {log.endpoint_path || "—"}
                      </td>
                      <td className="text-center">
                        {log.response_status != null && (
                          <span className={`go-badge ${statusBadgeClass(log.response_status)}`}>
                            {log.response_status}
                          </span>
                        )}
                      </td>
                      <td className="num text-right font-mono text-xs" style={{ color: "var(--go-text-secondary)" }}>
                        {log.duration_ms != null ? `${log.duration_ms} ms` : "—"}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => setDetailLog(log)}
                          title="Ver detalle"
                          className="btn-go-ghost px-2 py-1"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d={ICONS.ver} />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* ── Pagination footer ─────────────────────────────────────── */}
            <div
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              style={{ borderTop: "1px solid var(--go-border)" }}
            >
              <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                <span className="hidden sm:inline">
                  Mostrando {rangeStart}–{rangeEnd} de {total}
                </span>
                <span className="sm:hidden">
                  {rangeStart}–{rangeEnd}/{total}
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
                  {PAGE_SIZES.map((n) => (
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
          </div>
        </GlassPanel>
      )}

      {detailLog && (
        <Modal title={`Auditoría #${detailLog.id}`} onClose={() => setDetailLog(null)}>
          <div className="space-y-3 px-4 sm:px-6 py-5 font-mono text-xs" style={{ color: "var(--go-text-primary)" }}>
            {(() => {
              const sf = (() => { try { return typeof detailLog.standard_fields === "string" ? JSON.parse(detailLog.standard_fields) : detailLog.standard_fields; } catch { return null; } })();
              return [
              ["Fecha/Hora", formatDate(detailLog.created_at)],
              ["Usuario", detailLog.actor_full_name ? `${detailLog.actor_full_name} (${detailLog.actor_username})` : userLabelById.get(detailLog.actor_user_id) || "—"],
              ["Acción", detailLog.action],
              ["Método", detailLog.http_method || "—"],
              ["Endpoint", detailLog.endpoint_path || "—"],
              ["Status", detailLog.response_status ?? "—"],
              ["Duración", detailLog.duration_ms != null ? `${detailLog.duration_ms} ms` : "—"],
              ["IP", detailLog.ip_address || "—"],
              ["User-Agent", detailLog.user_agent || "—"],
              ["Tipo de objetivo", detailLog.target_type || "—"],
              ["ID de objetivo", detailLog.target_id ?? "—"],
              ...(sf ? [
                ["⏱ Epoch (time)", sf.time != null ? sf.time : "—"],
                ["📅 ISO 8601 (date)", sf.date || "—"],
                ["🖥 Host", sf.host?.name || "—"],
                ["📋 Endpoint type", sf.endpoint?.type || "—"],
              ] : []),
            ].map(([label, value]) => (
              <div key={label} className="grid grid-cols-3 gap-2">
                <span className="go-eyebrow col-span-1">{label}</span>
                <span className="col-span-2 break-all">{value}</span>
              </div>
            ));})()}

            {detailLog.details && (
              <div>
                <p className="go-eyebrow mb-1.5">Detalles</p>
                <pre className="go-input overflow-x-auto whitespace-pre-wrap">{detailLog.details}</pre>
              </div>
            )}
            {detailLog.request_params && (
              <div>
                <p className="go-eyebrow mb-1.5">Parámetros de la petición</p>
                <pre className="go-input overflow-x-auto whitespace-pre-wrap">{detailLog.request_params}</pre>
              </div>
            )}
            {detailLog.request_body_summary && (
              <div>
                <p className="go-eyebrow mb-1.5">Resumen del cuerpo</p>
                <pre className="go-input overflow-x-auto whitespace-pre-wrap">{detailLog.request_body_summary}</pre>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
