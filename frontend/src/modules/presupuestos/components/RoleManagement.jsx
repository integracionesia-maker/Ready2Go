import { useEffect, useState } from "react";
import { fetchRoles } from "@/api";
import { SkeletonShimmer, EmptyState } from "@/design";

const KIND_LABELS = {
  piso: "Piso",
  base: "Base",
  aditivo: "Aditivo",
};

const KIND_BADGE_CLASS = {
  piso: "go-badge-neutral",
  base: "go-badge-success",
  aditivo: "go-badge-warning",
};

function groupConsecutiveByKind(roles) {
  const groups = [];
  for (const role of roles) {
    const last = groups[groups.length - 1];
    if (last && last.kind === role.kind) {
      last.roles.push(role);
    } else {
      groups.push({ kind: role.kind, roles: [role] });
    }
  }
  return groups;
}

export default function RoleManagement() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        setRoles(await fetchRoles());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const groups = groupConsecutiveByKind(roles);

  return (
    <div className="space-y-4">
      <h2 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
        Catalogo de Roles y Permisos
      </h2>

      {error && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          <SkeletonShimmer className="h-24 w-full" />
          <SkeletonShimmer className="h-24 w-full" />
          <SkeletonShimmer className="h-24 w-full" />
        </div>
      ) : roles.length === 0 ? (
        <EmptyState title="Sin paquetes de permisos" message="No hay roles sembrados en el catálogo." />
      ) : (
        <div className="space-y-6">
          {groups.map((group, idx) => (
            <div key={`${group.kind}-${idx}`} className="space-y-3">
              <h3 className="go-eyebrow mt-4">{KIND_LABELS[group.kind] || group.kind}</h3>
              <div className="space-y-3">
                {group.roles.map((role) => (
                  <div key={role.name} className="go-card">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-display text-base font-semibold" style={{ color: "var(--go-text-primary)" }}>
                        {role.name}
                      </span>
                      <span className={`go-badge ${KIND_BADGE_CLASS[role.kind] || "go-badge-neutral"}`}>
                        {KIND_LABELS[role.kind] || role.kind}
                      </span>
                    </div>

                    {role.descripcion && (
                      <p className="mt-1.5 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                        {role.descripcion}
                      </p>
                    )}

                    <div className="mt-3 space-y-1">
                      {Object.entries(role.permisos || {}).map(([modulo, acciones]) => (
                        <div key={modulo} className="font-mono text-xs" style={{ color: "var(--go-text-secondary)" }}>
                          <span style={{ color: "var(--go-text-primary)" }}>{modulo}</span>: {acciones.join(", ")}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
