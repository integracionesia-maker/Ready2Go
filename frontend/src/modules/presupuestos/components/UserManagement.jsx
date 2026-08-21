import { useEffect, useState } from "react";
import {
  createUser,
  fetchUserRoles,
  fetchUsers,
  resetSuperadminPassword,
  resetUserPassword,
  setUserActive,
  updateUser,
} from "@/api";
import { useAuth } from "@/context/AuthContext";
import Modal from "./Modal";
import PasswordTemporal from "./PasswordTemporal";
import { GlassPanel, RowActions, ICONS, useToast } from "@/design";
import { SortableHeaderCell } from "./SortableHeader";
import { useSortable } from "../hooks/useSortable";

const ROLE_LABELS = {
  superadmin: "Superadministrador",
  admin: "Administrador",
  creador: "Creador",
  marketing_presupuestos: "Marketing (Presupuestos)",
  marketing_equipos: "Marketing (Equipos)",
  marketing_admin: "Marketing (Administrador)",
  marketing_basico: "Marketing (Básico)",
  colaborador_mkt: "Marketing",
  usuario: "Usuario",
  operativo: "Gastos Operativos",
};

const ROLE_OPTIONS = [
  { value: "admin", label: "Administrador" },
  { value: "creador", label: "Creador" },
  { value: "marketing_presupuestos", label: "Marketing (Presupuestos)" },
  { value: "marketing_equipos", label: "Marketing (Equipos)" },
  { value: "marketing_admin", label: "Marketing (Administrador)" },
  { value: "marketing_basico", label: "Marketing (Básico)" },
  { value: "colaborador_mkt", label: "Marketing (legacy)" },
  { value: "usuario", label: "Usuario" },
  { value: "operativo", label: "Gastos Operativos" },
];

const USER_COLUMNS = [
  { key: "full_name", label: "Nombre", type: "string" },
  { key: "role", label: "Rol", type: "string", getValue: (u) => ROLE_LABELS[u.role] || u.role },
  { key: "is_active", label: "Estado", type: "string", getValue: (u) => (u.is_active ? "Activo" : "Inactivo") },
  { key: "last_login", label: "Último acceso", type: "date" },
];

function formatLastLogin(iso) {
  if (!iso) return "Nunca";
  return new Date(iso).toLocaleDateString("es-MX", { year: "numeric", month: "short", day: "numeric" });
}

function emptyForm() {
  return { username: "", email: "", full_name: "", role: "creador", creator_id: "", password: "" };
}

// Reseteo de contraseña: idle → confirmando → enviando → listo. Vive dentro del
// modal de edición (no como acción de fila ni como segundo modal), así que la
// contraseña temporal aparece en el mismo lugar donde se pidió.
const RESET_INICIAL = { fase: "idle", password: null, error: null };

/** Renglón etiqueta/valor del modal informativo. */
function DetalleFila({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2" style={{ borderBottom: "1px solid var(--go-border)" }}>
      <span className="go-eyebrow flex-shrink-0 pt-0.5">{label}</span>
      <span className="text-right font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
        {children}
      </span>
    </div>
  );
}

// Evita disparar un GET /roles por usuario en paralelo sin limite (18 usuarios
// = 18 requests simultaneos, suficiente para saturar el pool de conexiones del
// backend). Un pool fijo de workers procesa la lista de a poco.
const ROLES_FETCH_CONCURRENCY = 4;

async function mapWithConcurrencyLimit(items, limit, fn) {
  const results = new Array(items.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < items.length) {
      const current = nextIndex++;
      results[current] = await fn(items[current], current);
    }
  }

  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

export default function UserManagement({ creators }) {
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rolesPorUsuario, setRolesPorUsuario] = useState({});

  // Paginación y filtros
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState({ role: "", is_active: "" });

  const [formOpen, setFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState(emptyForm());
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const [confirmToggle, setConfirmToggle] = useState(null);

  // Modal informativo (solo lectura) que abre al hacer clic en cualquier fila.
  const [detalleUser, setDetalleUser] = useState(null);

  const [reset, setReset] = useState(RESET_INICIAL);

  // ── Superadministradores: tabla separada + reset entre pares (2026-08-19) ──
  // Los superadmin no se editan ni desactivan por API; su única gestión es el
  // reset de contraseña ENTRE pares. Viven fuera de la tabla principal (que
  // los excluye vía exclude_role) con confirmación fuerte en modal propio.
  const toast = useToast();
  const [superAdmins, setSuperAdmins] = useState([]);
  const [superAdminLoading, setSuperAdminLoading] = useState(true);
  const [resetSaTarget, setResetSaTarget] = useState(null);
  const [saConfirmInput, setSaConfirmInput] = useState("");
  const [saReset, setSaReset] = useState({ fase: "confirmando", password: null, error: null });

  const { sortedItems: sortedUsers, sortKey, sortDir, cycleSort } = useSortable(users, USER_COLUMNS);

  // Debounce de 300ms para la búsqueda
  useEffect(() => {
    const t = setTimeout(() => {
      setPage(1);
      setFilters((f) => ({ ...f, search: searchInput }));
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      // Los superadmin viven en su propia tabla: excluidos del listado
      // principal y de su paginación (filtro server-side, 2026-08-19).
      params.exclude_role = "superadmin";
      if (filters.search) params.search = filters.search;
      if (filters.role) params.role = filters.role;
      if (filters.is_active) params.is_active = filters.is_active === "1";
      const data = await fetchUsers(params);
      setUsers(data.items);
      setTotal(data.total);
      loadRolesPorUsuario(data.items);
    } catch (err) {
      setError(err.message);
      setUsers([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const loadSuperAdmins = async () => {
    try {
      const data = await fetchUsers({ role: "superadmin", page_size: 200 });
      setSuperAdmins(data.items);
    } catch {
      setSuperAdmins([]);
    } finally {
      setSuperAdminLoading(false);
    }
  };

  const openResetSa = (u) => {
    setResetSaTarget(u);
    setSaConfirmInput("");
    setSaReset({ fase: "confirmando", password: null, error: null });
  };

  const handleResetSa = async () => {
    if (!resetSaTarget) return;
    setSaReset({ fase: "enviando", password: null, error: null });
    try {
      const result = await resetSuperadminPassword(resetSaTarget.id);
      setSaReset({ fase: "listo", password: result.temporary_password, error: null });
      setSuperAdmins((prev) =>
        prev.map((x) => (x.id === resetSaTarget.id ? { ...x, must_change_password: true } : x))
      );
      toast.push({ tone: "success", title: `Contraseña de ${resetSaTarget.username} reseteada` });
    } catch (err) {
      setSaReset({ fase: "confirmando", password: null, error: err.message });
    }
  };

  const loadRolesPorUsuario = async (usersToLoad) => {
    const entries = await mapWithConcurrencyLimit(usersToLoad, ROLES_FETCH_CONCURRENCY, async (u) => {
      try {
        const detalle = await fetchUserRoles(u.id);
        return [u.id, detalle.aditivos || []];
      } catch {
        return [u.id, []];
      }
    });
    setRolesPorUsuario(Object.fromEntries(entries));
  };

  useEffect(() => { load(); }, [page, pageSize, filters]);

  useEffect(() => { loadSuperAdmins(); }, []);

  const openCreateForm = () => {
    setEditingUser(null);
    setFormData(emptyForm());
    setFormError(null);
    setReset(RESET_INICIAL);
    setFormOpen(true);
  };

  const openEditForm = (u) => {
    setEditingUser(u);
    setFormData({
      username: u.username,
      email: u.email,
      full_name: u.full_name,
      role: u.role,
      creator_id: u.creator_id || "",
      password: "",
    });
    setFormError(null);
    setReset(RESET_INICIAL);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingUser(null);
    setFormError(null);
    setReset(RESET_INICIAL);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const creatorId = formData.role === "creador" ? Number(formData.creator_id) || null : null;
      if (editingUser) {
        await updateUser(editingUser.id, {
          full_name: formData.full_name,
          email: formData.email,
          role: formData.role,
          creator_id: creatorId,
        });
      } else {
        await createUser({
          username: formData.username,
          email: formData.email,
          full_name: formData.full_name,
          role: formData.role,
          creator_id: creatorId,
          password: formData.password || undefined,
        });
      }
      closeForm();
      load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPassword = async () => {
    if (!editingUser) return;
    setReset({ fase: "enviando", password: null, error: null });
    try {
      const result = await resetUserPassword(editingUser.id);
      setReset({ fase: "listo", password: result.temporary_password, error: null });
      // El backend deja `must_change_password=true`; se refleja en la fila que ya
      // está en memoria en vez de recargar la página entera detrás del modal.
      setUsers((prev) =>
        prev.map((x) => (x.id === editingUser.id ? { ...x, must_change_password: true } : x))
      );
    } catch (err) {
      setReset({ fase: "idle", password: null, error: err.message });
    }
  };

  const openToggleConfirm = (u) => {
    setConfirmToggle({ user: u, newActive: !u.is_active });
  };

  const handleToggleConfirm = async () => {
    if (!confirmToggle) return;
    const { user: target, newActive } = confirmToggle;
    setSubmitting(true);
    setError(null);
    try {
      await setUserActive(target.id, newActive);
      setConfirmToggle(null);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, totalPages);
  const rangeStart = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const rangeEnd = Math.min(currentPage * pageSize, total);

  const errorBanner = error && (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
    >
      {error}
    </div>
  );

  return (
    <>
    <GlassPanel className="space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <span className="go-eyebrow">{total} usuarios</span>
        <button onClick={openCreateForm} className="btn-go">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Usuario
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] flex-1">
          <label className="go-eyebrow mb-1.5 block">Buscar</label>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Nombre, usuario o correo..."
            className="go-input"
          />
        </div>
        <div className="min-w-[140px]">
          <label className="go-eyebrow mb-1.5 block">Rol</label>
          <select
            value={filters.role}
            onChange={(e) => { setPage(1); setFilters((f) => ({ ...f, role: e.target.value })); }}
            className="go-select"
          >
            <option value="">Todos</option>
            {ROLE_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>
        <div className="min-w-[120px]">
          <label className="go-eyebrow mb-1.5 block">Estado</label>
          <select
            value={filters.is_active}
            onChange={(e) => { setPage(1); setFilters((f) => ({ ...f, is_active: e.target.value })); }}
            className="go-select"
          >
            <option value="">Todos</option>
            <option value="1">Activo</option>
            <option value="0">Inactivo</option>
          </select>
        </div>
        <button
          type="button"
          onClick={() => { setSearchInput(""); setPage(1); setFilters({ role: "", is_active: "" }); }}
          className="btn-go-ghost"
        >
          Limpiar
        </button>
      </div>

      {errorBanner}

      {loading ? (
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Cargando...
        </p>
      ) : users.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-16 font-body text-sm"
          style={{ color: "var(--go-text-secondary)" }}
        >
          <p>No hay usuarios registrados.</p>
        </div>
      ) : (
        <>
        <div className="go-table-scroll-wrapper">
        <div className="overflow-x-auto go-table-scroll rounded-go-lg border" style={{ borderColor: "var(--go-border)" }}>
          <table className="go-table w-full table-fixed">
            <colgroup>
              <col className="w-[100px]" />
              <col className="w-[130px]" />
              <col className="w-[170px]" />
              <col className="w-[85px]" />
              <col className="w-[120px]" />
              <col className="w-[75px]" />
              <col className="w-[95px]" />
              <col className="w-[105px]" />
            </colgroup>
            <thead>
              <tr>
                <th>Usuario</th>
                <SortableHeaderCell label="Nombre" columnKey="full_name" activeKey={sortKey} dir={sortDir} onSort={cycleSort} />
                <th>Correo</th>
                <SortableHeaderCell label="Rol" columnKey="role" activeKey={sortKey} dir={sortDir} onSort={cycleSort} />
                <th>Paquetes</th>
                <SortableHeaderCell
                  label="Estado"
                  columnKey="is_active"
                  activeKey={sortKey}
                  dir={sortDir}
                  onSort={cycleSort}
                  align="center"
                />
                <SortableHeaderCell
                  label="Acceso"
                  columnKey="last_login"
                  activeKey={sortKey}
                  dir={sortDir}
                  onSort={cycleSort}
                />
                <th className="text-right" />
              </tr>
            </thead>
            <tbody>
              {sortedUsers.map((u) => {
                const isSelf = u.id === currentUser.id;
                const isTargetSuperadmin = u.role === "superadmin";
                return (
                  <tr
                    key={u.id}
                    onClick={() => setDetalleUser(u)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setDetalleUser(u);
                      }
                    }}
                    tabIndex={0}
                    title="Ver detalle"
                    className="cursor-pointer"
                  >
                    <td className="font-mono text-xs truncate" title={u.username}>{u.username}</td>
                    <td>
                      <span className="truncate block font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }} title={u.full_name}>
                        {u.full_name}
                      </span>
                      {isSelf && <span className="go-badge go-badge-warning ml-1 flex-shrink-0">Tú</span>}
                    </td>
                    <td className="font-body text-xs truncate" style={{ color: "var(--go-text-secondary)" }} title={u.email}>
                      {u.email}
                    </td>
                    <td>
                      <span
                        className="go-badge whitespace-nowrap"
                        style={{ background: "var(--go-surface-sunken)", color: "var(--go-text-secondary)" }}
                      >
                        {ROLE_LABELS[u.role] || u.role}
                      </span>
                    </td>
                    <td>
                      {(rolesPorUsuario[u.id] || []).length === 0 ? (
                        <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>—</span>
                      ) : (
                        <span className="go-badge go-badge-warning whitespace-nowrap" title={rolesPorUsuario[u.id].map(a => a.role_name).join(", ")}>
                          {rolesPorUsuario[u.id].map(a => a.role_name).join(", ")}
                        </span>
                      )}
                    </td>
                    <td className="text-center">
                      <span className={`go-badge whitespace-nowrap ${u.is_active ? "go-badge-success" : "go-badge-error"}`}>
                        {u.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="font-body text-xs whitespace-nowrap" style={{ color: "var(--go-text-secondary)" }}>
                      {formatLastLogin(u.last_login)}
                    </td>
                    {/* stopPropagation: un clic en una acción no debe abrir además
                        el modal informativo de la fila. */}
                    <td onClick={(e) => e.stopPropagation()}>
                      <RowActions
                        actions={[
                          !isTargetSuperadmin && {
                            key: "editar",
                            label: "Editar",
                            icon: ICONS.editar,
                            onClick: () => openEditForm(u),
                          },
                          !isTargetSuperadmin && {
                            key: "toggle",
                            label: u.is_active ? "Desactivar" : "Activar",
                            icon: ICONS.toggle,
                            variant: u.is_active ? "danger" : undefined,
                            onClick: () => openToggleConfirm(u),
                          },
                        ]}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
              {rangeStart}–{rangeEnd} de {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
              >
                Anterior
              </button>
              <span className="font-body text-xs tabular-nums" style={{ color: "var(--go-text-secondary)" }}>
                Página {page} de {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
        </>
      )}

      {/* ── Superadministradores: tabla separada (2026-08-19), al FONDO de la
          sección (decisión de producto): rol y estado son inmutables por API;
          la única gestión entre pares es el reset de contraseña con
          confirmación fuerte — el botón solo se habilita tecleando el
          username exacto del objetivo. */}
      <div className="rounded-go-lg border p-4" style={{ borderColor: "var(--go-border)" }}>
        <div className="flex items-center justify-between">
          <span className="go-eyebrow">Superadministradores</span>
          <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
            {superAdmins.length} cuenta{superAdmins.length !== 1 ? "s" : ""}
          </span>
        </div>

        {superAdminLoading ? (
          <p className="py-3 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Cargando...
          </p>
        ) : superAdmins.length === 0 ? (
          <p className="py-3 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Sin superadministradores registrados.
          </p>
        ) : (
          <div className="go-table-scroll-wrapper mt-2">
            <div className="go-table-scroll overflow-x-auto">
              <table className="go-table w-full table-fixed">
                <colgroup>
                  <col className="w-[120px]" />
                  <col className="w-[150px]" />
                  <col className="w-[190px]" />
                  <col className="w-[120px]" />
                  <col className="w-[110px]" />
                  <col className="w-[75px]" />
                </colgroup>
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Nombre</th>
                    <th>Correo</th>
                    <th>Contraseña</th>
                    <th>Último acceso</th>
                    <th className="text-right" />
                  </tr>
                </thead>
                <tbody>
                  {superAdmins.map((u) => {
                    const isSelf = u.id === currentUser.id;
                    return (
                      <tr
                        key={u.id}
                        onClick={() => setDetalleUser(u)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setDetalleUser(u);
                          }
                        }}
                        tabIndex={0}
                        title="Ver detalle"
                        className="cursor-pointer"
                      >
                        <td className="truncate font-mono text-xs" title={u.username}>
                          {u.username}
                          {isSelf && <span className="go-badge go-badge-warning ml-1 flex-shrink-0">Tú</span>}
                        </td>
                        <td
                          className="block truncate font-display text-sm font-semibold"
                          style={{ color: "var(--go-text-primary)" }}
                          title={u.full_name}
                        >
                          {u.full_name}
                        </td>
                        <td
                          className="truncate font-body text-xs"
                          style={{ color: "var(--go-text-secondary)" }}
                          title={u.email}
                        >
                          {u.email}
                        </td>
                        <td className="whitespace-nowrap font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                          {u.must_change_password ? "Debe cambiarla" : "Definitiva"}
                        </td>
                        <td className="whitespace-nowrap font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                          {formatLastLogin(u.last_login)}
                        </td>
                        {/* stopPropagation: la acción no debe abrir el modal
                            informativo de la fila. */}
                        <td onClick={(e) => e.stopPropagation()}>
                          {/* El backend 400a el reset sobre uno mismo: la UI ni
                              siquiera ofrece la acción. */}
                          {!isSelf && (
                            <RowActions
                              actions={[
                                {
                                  key: "reset-sa",
                                  label: "Resetear contraseña",
                                  icon: ICONS.resetear,
                                  variant: "danger",
                                  onClick: () => openResetSa(u),
                                },
                              ]}
                            />
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

    </GlassPanel>

    {formOpen && (
      <Modal title={editingUser ? "Editar Usuario" : "Crear Usuario"} onClose={closeForm} submitting={submitting}>
        {/* max-h + scroll propio: el bloque de contraseña alargó el formulario y
            `Modal` es `overflow-hidden` sin altura máxima — sin esto, en una
            pantalla baja los botones quedan recortados y sin forma de llegar. */}
        <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-4 overflow-y-auto px-4 sm:px-6 py-5">
          {!editingUser && (
            <div>
              <label className="go-eyebrow mb-1.5 block">Usuario</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="go-input"
                minLength={3}
                maxLength={50}
                required
              />
            </div>
          )}
          <div>
            <label className="go-eyebrow mb-1.5 block">Nombre completo</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="go-input"
              maxLength={150}
              required
            />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Correo</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="go-input"
              required
            />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Rol</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value, creator_id: "" })}
              className="go-select"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
          {formData.role === "creador" && (
            <div>
              <label className="go-eyebrow mb-1.5 block">Creador vinculado</label>
              <select
                value={formData.creator_id}
                onChange={(e) => setFormData({ ...formData, creator_id: e.target.value })}
                className="go-select"
                required
              >
                <option value="">Selecciona un creador...</option>
                {creators.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          {!editingUser && (
            <div>
              <label className="go-eyebrow mb-1.5 block">Contraseña (opcional)</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="go-input"
                placeholder="Dejar en blanco para generar una temporal"
                minLength={10}
              />
            </div>
          )}

          {/* Reseteo de contraseña: sale de las acciones de la fila (estaba a un
              clic de distancia, sin confirmación) y vive aquí, con confirmación
              y con la contraseña temporal en línea. */}
          {editingUser && (
            <div
              className="space-y-3 rounded-go border p-4"
              style={{ borderColor: "var(--go-border)", background: "var(--go-surface-sunken)" }}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="go-eyebrow">Contraseña</p>
                  <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                    Genera una temporal y cierra las sesiones activas del usuario.
                  </p>
                </div>
                {reset.fase === "idle" && (
                  <button
                    type="button"
                    onClick={() => setReset({ fase: "confirmando", password: null, error: null })}
                    className="btn-go-ghost flex-shrink-0 whitespace-nowrap text-xs"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d={ICONS.resetear} />
                    </svg>
                    Resetear
                  </button>
                )}
              </div>

              {reset.error && (
                <p className="font-body text-xs" style={{ color: "var(--go-error)" }}>
                  {reset.error}
                </p>
              )}

              {(reset.fase === "confirmando" || reset.fase === "enviando") && (
                <div
                  className="space-y-3 rounded-go border p-3"
                  style={{ background: "rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.25)" }}
                >
                  <p className="font-body text-xs" style={{ color: "var(--go-text-primary)" }}>
                    ¿Resetear la contraseña de <strong>{editingUser.full_name}</strong>? Su contraseña
                    actual dejará de funcionar de inmediato y se cerrarán todas sus sesiones.
                  </p>
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setReset(RESET_INICIAL)}
                      disabled={reset.fase === "enviando"}
                      className="btn-go-ghost text-xs"
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      onClick={handleResetPassword}
                      disabled={reset.fase === "enviando"}
                      className="btn-go text-xs"
                    >
                      {reset.fase === "enviando" ? "Reseteando..." : "Sí, resetear"}
                    </button>
                  </div>
                </div>
              )}

              {reset.fase === "listo" && (
                <PasswordTemporal username={editingUser.username} password={reset.password} />
              )}
            </div>
          )}

          {formError && (
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
            >
              {formError}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={closeForm} disabled={submitting} className="btn-go-ghost">
              Cancelar
            </button>
            <button type="submit" disabled={submitting} className="btn-go">
              {submitting ? "Guardando..." : editingUser ? "Guardar" : "Crear"}
            </button>
          </div>
        </form>
      </Modal>
    )}

    {confirmToggle && (
      <Modal title="Confirmar cambio de estado" onClose={() => setConfirmToggle(null)} submitting={submitting}>
        <div className="space-y-4 px-4 sm:px-6 py-5">
          <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
            {confirmToggle.newActive
              ? `¿Reactivar a ${confirmToggle.user.full_name}?`
              : `¿Desactivar a ${confirmToggle.user.full_name}? No podrá iniciar sesión hasta que sea reactivado.`}
          </p>

          {errorBanner}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setConfirmToggle(null)}
              disabled={submitting}
              className="btn-go-ghost"
            >
              Cancelar
            </button>
            <button type="button" onClick={handleToggleConfirm} disabled={submitting} className="btn-go">
              {submitting ? "Aplicando..." : "Confirmar"}
            </button>
          </div>
        </div>
      </Modal>
    )}

    {/* Modal informativo: solo lectura. Cualquier cambio se hace desde "Editar". */}
    {detalleUser && (
      <Modal title="Detalle del usuario" onClose={() => setDetalleUser(null)}>
        <div className="max-h-[70vh] space-y-4 overflow-y-auto px-4 sm:px-6 py-5">
          <div>
            <DetalleFila label="Usuario">
              <span className="font-mono text-xs">{detalleUser.username}</span>
            </DetalleFila>
            <DetalleFila label="Nombre">{detalleUser.full_name}</DetalleFila>
            <DetalleFila label="Correo">
              <span className="break-all">{detalleUser.email}</span>
            </DetalleFila>
            <DetalleFila label="Rol">
              <span
                className="go-badge whitespace-nowrap"
                style={{ background: "var(--go-surface-sunken)", color: "var(--go-text-secondary)" }}
              >
                {ROLE_LABELS[detalleUser.role] || detalleUser.role}
              </span>
            </DetalleFila>
            <DetalleFila label="Paquetes">
              {(rolesPorUsuario[detalleUser.id] || []).length === 0 ? (
                <span style={{ color: "var(--go-text-secondary)" }}>—</span>
              ) : (
                <span className="flex flex-wrap justify-end gap-1">
                  {rolesPorUsuario[detalleUser.id].map((a) => (
                    <span key={a.role_name} className="go-badge go-badge-warning whitespace-nowrap">
                      {a.role_name}
                    </span>
                  ))}
                </span>
              )}
            </DetalleFila>
            {detalleUser.creator_id && (
              <DetalleFila label="Creador">
                {creators.find((c) => c.id === detalleUser.creator_id)?.name || `#${detalleUser.creator_id}`}
              </DetalleFila>
            )}
            <DetalleFila label="Estado">
              <span className={`go-badge whitespace-nowrap ${detalleUser.is_active ? "go-badge-success" : "go-badge-error"}`}>
                {detalleUser.is_active ? "Activo" : "Inactivo"}
              </span>
            </DetalleFila>
            <DetalleFila label="Contraseña">
              {detalleUser.must_change_password ? "Debe cambiarla al entrar" : "Definitiva"}
            </DetalleFila>
            <DetalleFila label="Último acceso">{formatLastLogin(detalleUser.last_login)}</DetalleFila>
            <DetalleFila label="Alta">{formatLastLogin(detalleUser.created_at)}</DetalleFila>
          </div>

          <div className="flex justify-end">
            <button type="button" onClick={() => setDetalleUser(null)} className="btn-go">
              Cerrar
            </button>
          </div>
        </div>
      </Modal>
    )}

    {/* Reset de contraseña ENTRE superadmins: confirmación fuerte — el botón
        solo se habilita tecleando el username exacto del objetivo. */}
    {resetSaTarget && (
      <Modal
        title="Resetear contraseña de superadministrador"
        onClose={() => setResetSaTarget(null)}
        submitting={saReset.fase === "enviando"}
      >
        <div className="max-h-[70vh] space-y-4 overflow-y-auto px-4 sm:px-6 py-5">
          {saReset.fase !== "listo" ? (
            <>
              <div
                className="space-y-3 rounded-go border p-3"
                style={{ background: "rgba(245,158,11,0.08)", borderColor: "rgba(245,158,11,0.25)" }}
              >
                <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                  Vas a resetear la contraseña de <strong>{resetSaTarget.username}</strong>{" "}
                  ({resetSaTarget.full_name}).
                </p>
                <ul className="list-disc space-y-1 pl-5 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                  <li>Su contraseña actual dejará de funcionar de inmediato.</li>
                  <li>Se cerrarán todas sus sesiones activas.</li>
                  <li>Recibirá una contraseña temporal y deberá cambiarla en su primer acceso.</li>
                  <li>Si estaba bloqueada por intentos fallidos, quedará desbloqueada.</li>
                </ul>
              </div>

              <div>
                <label className="go-eyebrow mb-1.5 block">
                  Escribe <span className="font-mono">{resetSaTarget.username}</span> para confirmar
                </label>
                <input
                  type="text"
                  value={saConfirmInput}
                  onChange={(e) => setSaConfirmInput(e.target.value)}
                  className="go-input font-mono"
                  placeholder={resetSaTarget.username}
                  autoComplete="off"
                />
              </div>

              {saReset.error && (
                <p className="font-body text-xs" style={{ color: "var(--go-error)" }}>
                  {saReset.error}
                </p>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setResetSaTarget(null)}
                  disabled={saReset.fase === "enviando"}
                  className="btn-go-ghost"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleResetSa}
                  disabled={saReset.fase === "enviando" || saConfirmInput.trim() !== resetSaTarget.username}
                  className="btn-go"
                >
                  {saReset.fase === "enviando" ? "Reseteando..." : "Resetear contraseña"}
                </button>
              </div>
            </>
          ) : (
            <>
              <PasswordTemporal username={resetSaTarget.username} password={saReset.password} />
              <div className="flex justify-end pt-2">
                <button type="button" onClick={() => setResetSaTarget(null)} className="btn-go">
                  Cerrar
                </button>
              </div>
            </>
          )}
        </div>
      </Modal>
    )}
    </>
  );
}
