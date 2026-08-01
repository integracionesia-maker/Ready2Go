import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchEquipmentDashboard } from "../api";
import { esCodigo } from "@/api";
import { GlassPanel, EmptyState, SkeletonShimmer, SectionCard } from "@/design";

// Mismos paths SVG que EquiposSidebar.jsx NAV_ITEMS — una sola fuente de
// verdad visual para "a dónde puedo ir en Equipos", solo que aquí sin
// filtrar por permiso (igual que AdminHome en HomePage.jsx de Presupuestos):
// cada página de destino ya se degrada con gracia si falta el permiso.
const EQUIPOS_SECTIONS = [
  {
    to: "/equipos/dashboard",
    title: "Dashboard",
    description: "KPIs, gráficas y tendencias de préstamos.",
    icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
  },
  {
    to: "/equipos/inventario",
    title: "Inventario",
    description: "Catálogo de equipos disponible.",
    icon: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
  },
  {
    to: "/equipos/nuevo",
    title: "Nuevo préstamo",
    description: "Solicitar equipo con firma y fotos.",
    icon: "M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    to: "/equipos/activos",
    title: "Préstamos activos",
    description: "Equipos prestados actualmente.",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    to: "/equipos/aprobaciones",
    title: "Aprobaciones",
    description: "Autorizar entregas y confirmar devoluciones.",
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    to: "/equipos/historial",
    title: "Historial",
    description: "Registro completo de préstamos.",
    icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];

/**
 * Inicio de Equipos (C2): solo cards de acceso rápido, mismo patrón que
 * HomePage.jsx de Presupuestos. El contenido analítico (KPIs, gráficas) se
 * movió a DashboardEquiposPage — "Requiere atención" se queda aquí porque es
 * operacional (acción pendiente), no analítico.
 */
export default function InicioPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <SkeletonShimmer key={i} className="h-32" />
          ))}
        </div>
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
    <div className="space-y-10">
      {/* ── Welcome ──────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-2xl pt-8 text-center">
        <p className="go-eyebrow mb-3">Grupo Ortiz</p>
        <h1
          className="font-display text-2xl font-bold uppercase tracking-[0.04em] sm:text-3xl"
          style={{ color: "var(--go-text-primary)" }}
        >
          Bienvenido al Control de Equipos
        </h1>
        <p className="mt-3 font-body text-sm sm:text-base" style={{ color: "var(--go-text-secondary)" }}>
          Gestiona el inventario de equipo de grabación, solicita préstamos,
          firma cartas responsiva y monitorea las devoluciones.
        </p>
      </div>

      {/* ── Acceso rápido ────────────────────────────────────────────────── */}
      <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-2">
        {EQUIPOS_SECTIONS.map((s) => (
          <SectionCard key={s.to} {...s} />
        ))}
      </div>

      {/* ── Requiere atención ────────────────────────────────────────────── */}
      <div className="mx-auto max-w-4xl">
        <GlassPanel as="section" className="p-4 sm:p-6">
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
                    className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-3 font-body text-sm transition-colors hover:text-[var(--go-orange)]"
                    style={{ color: "var(--go-text-primary)" }}
                  >
                    <span className="min-w-0">
                      <span className="font-mono font-semibold" style={{ color: "var(--go-orange)" }}>
                        {r.folio}
                      </span>{" "}
                      — {r.motivo} ({r.responsable})
                    </span>
                    <span className="font-body text-xs sm:shrink-0" style={{ color: "var(--go-text-secondary)" }}>
                      {(r.equipos || []).join(", ")}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
