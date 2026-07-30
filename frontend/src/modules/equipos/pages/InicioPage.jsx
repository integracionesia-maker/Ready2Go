import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchEquipmentDashboard, fetchLoans } from "../api";
import { esCodigo } from "@/api";
import { KpiTile, StatusDonut, EmptyState, SkeletonShimmer } from "@/design";
import LoansByMonthChart from "../components/charts/LoansByMonthChart";
import TopEquipmentChart from "../components/charts/TopEquipmentChart";

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

const TOP_EQUIPOS_LIMITE = 8;
// Límite máximo que acepta GET /loans/ (crud_loans.LIMITE_MAXIMO). No existe
// todavía un endpoint de agregados para estos 3 paneles (B3 en
// docs/asignaciones/beni-bugs-post-unificacion.md) — mientras tanto se
// procesan del lado del cliente sobre los préstamos más recientes. Si
// `loansTotal` supera esta muestra, los paneles avisan que es parcial.
const LOANS_SAMPLE_LIMIT = 200;

function mesDe(fechaISO) {
  return fechaISO ? fechaISO.slice(0, 7) : null; // "YYYY-MM"
}

function diasDesde(fechaISO, hoy) {
  const inicio = new Date(`${fechaISO}T00:00:00`);
  const ms = hoy.getTime() - inicio.getTime();
  return Math.max(0, ms / 86400000);
}

export default function InicioPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loans, setLoans] = useState(null);
  const [loansTotal, setLoansTotal] = useState(0);
  const [loansForbidden, setLoansForbidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    setLoansForbidden(false);
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
      setLoading(false);
      return;
    }

    try {
      const resp = await fetchLoans({ limit: LOANS_SAMPLE_LIMIT });
      setLoans(resp.items);
      setLoansTotal(resp.total);
    } catch (e) {
      // equipos_inventario:ver (dashboard) y equipos_prestamos:ver_propios/
      // ver_global (préstamos) son paquetes de permiso distintos — un rol de
      // solo-inventario puede tener el primero sin el segundo. En ese caso
      // los 3 paneles derivados de /loans/ se ocultan, no toda la pantalla.
      if (e.status === 403) {
        setLoansForbidden(true);
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
      <div className="space-y-8">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <SkeletonShimmer key={i} className="h-24" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <SkeletonShimmer className="h-80" />
          <SkeletonShimmer className="h-80" />
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

  const porEstadoData = Object.entries(dashboard.por_estado || {}).map(([estado, valor]) => ({
    label: ETIQUETA_POR_ESTADO[estado] || estado,
    value: valor,
    color: COLOR_POR_ESTADO[estado] || "#535353",
  }));
  const totalEnCiclo = porEstadoData.reduce((acc, d) => acc + d.value, 0);

  // ── Agregados client-side sobre la muestra de préstamos (ver nota en
  //    LOANS_SAMPLE_LIMIT) — ninguno de los tres depende de un endpoint que
  //    todavía no existe.
  const porMes = (() => {
    if (!loans) return [];
    const conteo = new Map();
    for (const loan of loans) {
      const mes = mesDe(loan.fecha_entrega);
      if (!mes) continue; // borrador/cancelado sin entrega: no cuenta como préstamo real
      conteo.set(mes, (conteo.get(mes) || 0) + 1);
    }
    return [...conteo.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, count]) => ({ month, count }));
  })();

  const topEquipos = (() => {
    if (!loans) return [];
    const conteo = new Map();
    for (const loan of loans) {
      for (const nombre of loan.equipos || []) {
        conteo.set(nombre, (conteo.get(nombre) || 0) + 1);
      }
    }
    return [...conteo.entries()]
      .sort(([, a], [, b]) => b - a)
      .slice(0, TOP_EQUIPOS_LIMITE)
      .map(([name, count]) => ({ name, count }))
      .reverse(); // barra horizontal: ApexCharts pinta la primera categoría abajo
  })();

  const tiempoPromedioActivo = (() => {
    if (!loans) return null;
    const hoy = new Date();
    const activos = loans.filter((l) => l.estado === "prestado" && l.fecha_entrega);
    if (activos.length === 0) return null;
    const total = activos.reduce((acc, l) => acc + diasDesde(l.fecha_entrega, hoy), 0);
    return total / activos.length;
  })();

  const tasaDevolucionData = (() => {
    if (!loans) return [];
    const finalizados = loans.filter((l) => l.fecha_regreso_real && l.fecha_regreso_esperada);
    if (finalizados.length === 0) return [];
    const aTiempo = finalizados.filter((l) => l.fecha_regreso_real <= l.fecha_regreso_esperada).length;
    const atrasados = finalizados.length - aTiempo;
    return [
      { label: "A tiempo", value: aTiempo, color: "#00A36E" },
      { label: "Atrasados", value: atrasados, color: "#E53E3E" },
    ];
  })();
  const totalFinalizados = tasaDevolucionData.reduce((acc, d) => acc + d.value, 0);

  const muestraParcial = loans && loansTotal > loans.length;

  return (
    <div className="space-y-8">
      <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
        Inicio
      </h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <KpiTile label="Prestados" value={dashboard.prestados} accentColor="#FB670B" />
        <KpiTile label="Atrasados" value={dashboard.atrasados} accentColor="#E53E3E" />
        <KpiTile label="Pend. confirmación" value={dashboard.pendientes_confirmacion} accentColor="#F59E0B" />
        <KpiTile label="Disponibles" value={dashboard.disponibles} accentColor="#00A36E" />
        <KpiTile
          label="Tiempo promedio"
          value={tiempoPromedioActivo != null ? Math.round(tiempoPromedioActivo) : "—"}
          hint="días, préstamos activos"
          accentColor="#A78BFA"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
        </section>
      </div>

      {loansForbidden ? (
        <EmptyState title="Sin permiso para ver préstamos" message="Estas métricas requieren acceso a préstamos de equipo." />
      ) : (
        <>
          <section className="go-card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
                Préstamos por mes
              </h2>
              {muestraParcial && <span className="go-eyebrow">Últimos {loans.length} de {loansTotal}</span>}
            </div>
            <LoansByMonthChart data={porMes} />
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section className="go-card">
              <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
                Top equipos prestados
              </h2>
              <TopEquipmentChart data={topEquipos} />
            </section>

            <section className="go-card">
              <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
                Tasa de devolución a tiempo
              </h2>
              {totalFinalizados === 0 ? (
                <EmptyState title="Sin préstamos finalizados" />
              ) : (
                <div className="flex flex-wrap items-center gap-6">
                  <StatusDonut data={tasaDevolucionData} centerValue={totalFinalizados} centerLabel="finalizados" />
                  <ul className="flex flex-col gap-2">
                    {tasaDevolucionData.map((d) => (
                      <li key={d.label} className="flex items-center gap-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: d.color }} aria-hidden="true" />
                        {d.label}: <span className="font-mono" style={{ color: "var(--go-text-primary)" }}>{d.value}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
