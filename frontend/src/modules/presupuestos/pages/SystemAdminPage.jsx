import { useEffect, useState } from "react";
import { fetchUsers } from "@/api";
import { useAuth } from "@/context/AuthContext";
import UserManagement from "../components/UserManagement";
import RoleManagement from "../components/RoleManagement";
import UserRoleAssignment from "../components/UserRoleAssignment";

const TABS = [
  { key: "usuarios", label: "Usuarios" },
  { key: "roles", label: "Roles y Permisos" },
  { key: "asignaciones", label: "Asignaciones" },
];

/**
 * Administracion del Sistema — superadmin, o un admin con el paquete delegado
 * ADMIN_USUARIOS (ProtectedRoute en PresupuestosLayout). Separada de
 * /administracion (Creadores/Marcas, que admin tambien ve). El delegado ve
 * Usuarios y el catalogo de Roles (solo lectura); conceder/revocar paquetes
 * (Asignaciones) y las cuentas superadmin siguen siendo solo de superadmin (R4).
 */
import { usePageTitle } from "@/design";

export default function SystemAdminPage({ creators, onCreatorsChange }) {
  usePageTitle("Administración del Sistema");
  const { user: sesion } = useAuth();
  const esSuperadmin = sesion?.role === "superadmin";
  const tabs = esSuperadmin ? TABS : TABS.filter((t) => t.key !== "asignaciones");
  const [tab, setTab] = useState("usuarios");

  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState(null);

  useEffect(() => {
    // Solo la pestaña Asignaciones (superadmin) usa esta lista.
    if (!esSuperadmin) {
      setUsersLoading(false);
      return undefined;
    }
    let active = true;
    setUsersLoading(true);
    setUsersError(null);
    fetchUsers({ page_size: 200 })
      .then((data) => {
        if (active) setUsers(data.items);
      })
      .catch((err) => {
        if (active) setUsersError(err.message);
      })
      .finally(() => {
        if (active) setUsersLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Administración del Sistema
        </h1>
        <nav
          aria-label="Secciones de Administración del Sistema"
          className="flex items-center gap-1 rounded-go p-1"
          style={{ background: "var(--go-surface)" }}
        >
          {tabs.map((t) => {
            const isActive = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className="rounded-go px-3 sm:px-4 py-1.5 font-display text-xs sm:text-sm font-semibold tracking-wide transition-all duration-200"
                style={{
                  background: isActive ? "var(--go-surface-sunken)" : "transparent",
                  color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)",
                }}
              >
                {t.label}
              </button>
            );
          })}
        </nav>
      </div>

      {tab === "usuarios" && (
        <UserManagement creators={creators} onCreatorsChange={onCreatorsChange} />
      )}
      {tab === "roles" && <RoleManagement />}
      {esSuperadmin && tab === "asignaciones" &&
        (usersError ? (
          <div
            className="rounded-go border px-4 py-3 font-body text-sm"
            style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
          >
            {usersError}
          </div>
        ) : usersLoading ? (
          <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Cargando...
          </p>
        ) : (
          <UserRoleAssignment users={users} />
        ))}
    </div>
  );
}
