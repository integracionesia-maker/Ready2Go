import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchEquipmentDashboard } from "../api";
import { esCodigo } from "@/api";
import { KpiTile, StatusDonut, EmptyState, SkeletonShimmer } from "@/design";

const COLOR_POR_ESTADO = {
  prestado: "#FB670B",
  pendiente_confirmacion: "#F59E0B",
  completado: "#00A36E",
  incompleto: "#E53E3E",
};

const ETIQUETA_POR_ESTADO = {
  prestado: "Prestado",
  pendiente_confirmacion: "Pend. confirmación",
  completado: "Completado",
  incompleto: "Incompleto",
};

export default function InicioPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    try {
      const data = await fetchEquipmentDashboard();
      setDashboard(data);
    } catch (e) {
      // 503 PERMISOS_NO_DISPONIBLES NUNCA se pinta como "sin acceso" (eso
      // es 403) ni desloguea — se ofrece reintentar.
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
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonShimmer key={i} className="h-24" />
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

  const porEstadoData = Object.entries(dashboard.por_estado || {}).map(([estado, valor]) => ({
    label: ETIQUETA_POR_ESTADO[estado] || estado,
    value: valor,
    color: COLOR_POR_ESTADO[estado] || "#535353",
  }));
  const totalEnCiclo = porEstadoData.reduce((acc, d) => acc + d.value, 0);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiTile label="Prestados" value={dashboard.prestados} accentColor="#FB670B" />
        <KpiTile label="Atrasados" value={dashboard.atrasados} accentColor="#E53E3E" glass />
        <KpiTile label="Pend. confirmación" value={dashboard.pendientes_confirmacion} accentColor="#F59E0B" glass />
        <KpiTile label="Disponibles" value={dashboard.disponibles} accentColor="#00A36E" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="go-card">
          <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
            Distribución de estados
          </h2>
          {totalEnCiclo === 0 ? (
            <EmptyState title="Sin préstamos en curso" />
          ) : (
            <div className="flex flex-wrap items-center gap-6">
              <StatusDonut data={porEstadoData} centerValue={totalEnCiclo} centerLabel="préstamos" />
              <ul className="flex flex-col gap-2">
                {porEstadoData.map((d) => (
                  <li key={d.label} className="flex items-center gap-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: d.color }} aria-hidden="true" />
                    {d.label}: <span className="font-mono" style={{ color: "var(--go-text-primary)" }}>{d.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="go-card">
          <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
            Requiere atención
          </h2>
          {(dashboard.requiere_atencion || []).length === 0 ? (
            <EmptyState title="Nada pendiente de atención" />
          ) : (
            <ul className="flex flex-col divide-y" style={{ borderColor: "var(--go-border)" }}>
              {dashboard.requiere_atencion.map((r) => (
                <li key={r.loan_id} className="py-3">
                  <Link
                    to={`/equipos/prestamo/${r.folio}`}
                    className="flex items-center justify-between gap-3 font-body text-sm transition-colors hover:text-[var(--go-orange)]"
                    style={{ color: "var(--go-text-primary)" }}
                  >
                    <span>
                      <span className="font-mono font-semibold" style={{ color: "var(--go-orange)" }}>
                        {r.folio}
                      </span>{" "}
                      — {r.motivo} ({r.responsable})
                    </span>
                    <span className="shrink-0 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                      {(r.equipos || []).join(", ")}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
