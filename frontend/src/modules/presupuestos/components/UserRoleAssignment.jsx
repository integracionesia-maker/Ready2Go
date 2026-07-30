import { useEffect, useMemo, useState } from "react";
import { fetchRoles, fetchUserRoles, grantUserRole, revokeUserRole } from "@/api";
import { EmptyState, useToast } from "@/design";

const ROLE_LABELS = {
  superadmin: "Superadministrador",
  admin: "Administrador",
  creador: "Creador",
  colaborador_mkt: "Marketing",
  usuario: "Usuario",
};

function ErrorBanner({ error }) {
  if (!error) return null;
  return (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
    >
      {error}
    </div>
  );
}

export default function UserRoleAssignment({ users }) {
  const { push } = useToast();

  // Catálogo de paquetes (para poblar el selector de "agregar paquete").
  const [rolesCatalog, setRolesCatalog] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState(null);

  // Usuario seleccionado + sus roles/permisos.
  const [selectedUserId, setSelectedUserId] = useState("");
  const [userRoles, setUserRoles] = useState(null);
  const [userRolesLoading, setUserRolesLoading] = useState(false);
  const [error, setError] = useState(null);

  // Selector + acción de "agregar paquete".
  const [packageToAdd, setPackageToAdd] = useState("");
  const [granting, setGranting] = useState(false);
  const [revokingRole, setRevokingRole] = useState(null);

  // La cuenta superadmin es inmutable por API: nunca debe ser seleccionable aquí.
  const selectableUsers = useMemo(() => users.filter((u) => u.role !== "superadmin"), [users]);

  useEffect(() => {
    let active = true;
    setCatalogLoading(true);
    setCatalogError(null);
    fetchRoles()
      .then((data) => {
        if (active) setRolesCatalog(data);
      })
      .catch((err) => {
        if (active) setCatalogError(err.message);
      })
      .finally(() => {
        if (active) setCatalogLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const loadUserRoles = async (userId) => {
    setUserRolesLoading(true);
    setError(null);
    try {
      setUserRoles(await fetchUserRoles(userId));
    } catch (err) {
      setError(err.message);
      setUserRoles(null);
    } finally {
      setUserRolesLoading(false);
    }
  };

  useEffect(() => {
    setPackageToAdd("");
    setError(null);
    if (!selectedUserId) {
      setUserRoles(null);
      return;
    }
    loadUserRoles(selectedUserId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUserId]);

  const paquetesDisponibles = useMemo(() => {
    const aditivos = rolesCatalog.filter((r) => r.kind === "aditivo");
    if (!userRoles) return aditivos;
    const yaConcedidos = new Set(userRoles.aditivos.map((a) => a.role_name));
    return aditivos.filter((r) => !yaConcedidos.has(r.name));
  }, [rolesCatalog, userRoles]);

  const handleGrant = async () => {
    if (!packageToAdd || !selectedUserId) return;
    setGranting(true);
    setError(null);
    try {
      const data = await grantUserRole(selectedUserId, packageToAdd);
      setUserRoles(data);
      push({ tone: "success", title: `Paquete concedido — ${packageToAdd}` });
      setPackageToAdd("");
    } catch (err) {
      setError(err.message);
    } finally {
      setGranting(false);
    }
  };

  const handleRevoke = async (roleName) => {
    if (!selectedUserId) return;
    setRevokingRole(roleName);
    setError(null);
    try {
      await revokeUserRole(selectedUserId, roleName);
      push({ tone: "success", title: `Paquete revocado — ${roleName}` });
      await loadUserRoles(selectedUserId);
    } catch (err) {
      setError(err.message);
    } finally {
      setRevokingRole(null);
    }
  };

  const permisosEfectivosEntries = userRoles ? Object.entries(userRoles.permisos_efectivos) : [];

  return (
    <div className="go-card space-y-6">
      <h2 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
        Asignación de paquetes
      </h2>

      <ErrorBanner error={catalogError} />

      <div>
        <label className="go-eyebrow mb-1.5 block">Usuario</label>
        <select value={selectedUserId} onChange={(e) => setSelectedUserId(e.target.value)} className="go-select">
          <option value="">Selecciona un usuario...</option>
          {selectableUsers.map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name} ({u.username})
            </option>
          ))}
        </select>
      </div>

      <ErrorBanner error={error} />

      {!selectedUserId && (
        <EmptyState
          title="Sin usuario seleccionado"
          message="Elige un usuario para ver y modificar sus paquetes aditivos."
        />
      )}

      {selectedUserId && userRolesLoading && (
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Cargando...
        </p>
      )}

      {selectedUserId && !userRolesLoading && userRoles && (
        <div className="space-y-6">
          <div>
            <p className="go-eyebrow mb-2">Rol base</p>
            <span className="go-badge go-badge-neutral">{ROLE_LABELS[userRoles.role_base] || userRoles.role_base}</span>
          </div>

          <div>
            <p className="go-eyebrow mb-2">Paquetes aditivos</p>
            {userRoles.aditivos.length === 0 ? (
              <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                Sin paquetes aditivos.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {userRoles.aditivos.map((a) => (
                  <span key={a.role_name} className="go-badge go-badge-neutral">
                    {a.role_name}
                    <button
                      type="button"
                      onClick={() => handleRevoke(a.role_name)}
                      disabled={revokingRole === a.role_name}
                      aria-label={`Revocar paquete ${a.role_name}`}
                      className="-mr-1 rounded-full p-0.5 transition-colors hover:bg-white/10 disabled:opacity-50"
                    >
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="go-eyebrow mb-2">Agregar paquete</p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <select
                value={packageToAdd}
                onChange={(e) => setPackageToAdd(e.target.value)}
                className="go-select sm:max-w-xs"
                disabled={catalogLoading || paquetesDisponibles.length === 0}
              >
                <option value="">
                  {paquetesDisponibles.length === 0 ? "Sin paquetes disponibles" : "Selecciona un paquete..."}
                </option>
                {paquetesDisponibles.map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
              <button type="button" onClick={handleGrant} disabled={!packageToAdd || granting} className="btn-go">
                {granting ? "Agregando..." : "Agregar"}
              </button>
            </div>
          </div>

          <div>
            <p className="go-eyebrow mb-2">Permisos efectivos resultantes</p>
            {permisosEfectivosEntries.length === 0 ? (
              <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                Este usuario no tiene acceso a ningún módulo todavía.
              </p>
            ) : (
              <div className="space-y-1">
                {permisosEfectivosEntries.map(([modulo, acciones]) => (
                  <p key={modulo} className="font-mono text-xs" style={{ color: "var(--go-text-secondary)" }}>
                    <span style={{ color: "var(--go-text-primary)" }}>{modulo}</span>: {acciones.join(", ")}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
