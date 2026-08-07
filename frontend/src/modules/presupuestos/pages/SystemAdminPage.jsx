import { useEffect, useState } from "react";
import { fetchUsers } from "@/api";
import UserManagement from "../components/UserManagement";
import RoleManagement from "../components/RoleManagement";
import UserRoleAssignment from "../components/UserRoleAssignment";

const TABS = [
  { key: "usuarios", label: "Usuarios" },
  { key: "roles", label: "Roles y Permisos" },
  { key: "asignaciones", label: "Asignaciones" },
];

/**
 * Administracion del Sistema — exclusiva de superadmin (ProtectedRoute en
 * PresupuestosLayout). Separada de /administracion (Creadores/Marcas, que
 * admin tambien ve): gestion de usuarios y RBAC es SOLO de superadmin (R4).
 */
export default function SystemAdminPage({ creators }) {
  const [tab, setTab] = useState("usuarios");

  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState(null);

  useEffect(() => {
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
          {TABS.map((t) => {
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

      {tab === "usuarios" && <UserManagement creators={creators} />}
      {tab === "roles" && <RoleManagement />}
      {tab === "asignaciones" &&
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
