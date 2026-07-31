import { useCallback, useEffect, useRef, useState } from "react";
import { fetchEquipmentDashboard, fetchLoans } from "../api";
import { esCodigo } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { GlassPanel, KpiTile, StatusDonut, EmptyState, SkeletonShimmer } from "@/design";
import DateRangeFilter from "@/modules/presupuestos/components/DateRangeFilter";
import LoansByMonthChart from "../components/charts/LoansByMonthChart";
import TopEquipmentChart from "../components/charts/TopEquipmentChart";
import EquiposDashboardPdfTemplate from "../components/PdfReport/EquiposDashboardPdfTemplate";
import { generateEquiposDashboardPdf } from "../components/PdfReport/generateEquiposDashboardPdf";

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
// procesan del lado del cliente sobre los préstamos del período filtrado.
const LOANS_SAMPLE_LIMIT = 200;

function mesDe(fechaISO) {
  return fechaISO ? fechaISO.slice(0, 7) : null; // "YYYY-MM"
}

function diasDesde(fechaISO, hoy) {
  const inicio = new Date(`${fechaISO}T00:00:00`);
  const ms = hoy.getTime() - inicio.getTime();
  return Math.max(0, ms / 86400000);
}

function firstOfMonth(y, m) {
  return new Date(y, m, 1);
}

function today() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}

function fmtDateParam(d) {
  if (!d) return undefined;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Dashboard analítico de Equipos (C2): KPIs de estado actual (endpoint
 * `/equipment/dashboard`, no depende de fecha) + 3 paneles derivados de
 * `/loans/` que sí respetan el filtro desde/hasta (mismo campo que filtra el
 * backend: `fecha_entrega`, ver `crud_loans.py`). Separado de InicioPage
 * (C2): eso se queda solo con las cards de acceso rápido.
 */
export default function DashboardEquiposPage() {
  const { user } = useAuth();

  const [dashboard, setDashboard] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [dashboardError, setDashboardError] = useState(null);

  const [loans, setLoans] = useState(null);
  const [loansTotal, setLoansTotal] = useState(0);
  const [loansForbidden, setLoansForbidden] = useState(false);
  const [loadingLoans, setLoadingLoans] = useState(true);
  const [loansError, setLoansError] = useState(null);

  const [dateRange, setDateRange] = useState(() => {
    const t = today();
    return { start: firstOfMonth(t.getFullYear(), t.getMonth()), end: t };
  });

  const [pdfState, setPdfState] = useState("idle"); // idle | rendering | generating
  const [pdfError, setPdfError] = useState(null);
  const pdfSnapshotRef = useRef(null);

  const cargarDashboard = useCallback(async () => {
    setLoadingDashboard(true);
    setDashboardError(null);
    setPermisosNoDisponibles(false);
    try {
      const data = await fetchEquipmentDashboard();
      setDashboard(data);
    } catch (e) {
      // 503 PERMISOS_NO_DISPONIBLES NUNCA se pinta como "sin acceso" (eso es
      // 403) ni desloguea — se ofrece reintentar.
      if (esCodigo(e, "PERMISOS_NO_DISPONIBLES")) {
        setPermisosNoDisponibles(true);
      } else {
        setDashboardError(e.message);
      }
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

  const cargarLoans = useCallback(async () => {
    setLoadingLoans(true);
    setLoansForbidden(false);
    setLoansError(null);
    try {
      const resp = await fetchLoans({
        desde: fmtDateParam(dateRange.start),
        hasta: fmtDateParam(dateRange.end),
        limit: LOANS_SAMPLE_LIMIT,
      });
      setLoans(resp.items);
      setLoansTotal(resp.total);
    } catch (e) {
      // equipos_inventario:ver (dashboard) y equipos_prestamos:ver_propios/
      // ver_global (préstamos) son paquetes de permiso distintos — un rol de
      // solo-inventario puede tener el primero sin el segundo. En ese caso
      // los 3 paneles derivados de /loans/ se ocultan, no todo el dashboard.
      if (e.status === 403) {
        setLoansForbidden(true);
      } else {
        setLoansError(e.message);
      }
    } finally {
      setLoadingLoans(false);
    }
  }, [dateRange]);

  useEffect(() => {
    cargarDashboard();
  }, [cargarDashboard]);

  useEffect(() => {
    cargarLoans();
  }, [cargarLoans]);

  if (loadingDashboard) {
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
          <button type="button" onClick={cargarDashboard} className="btn-go mt-2">
            Reintentar
          </button>
        }
      />
    );
  }

  if (dashboardError) {
    return (
      <div
        className="rounded-go border px-4 py-3 font-body text-sm"
        style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
      >
        {dashboardError}
      </div>
    );
  }

  const porEstadoData = Object.entries(dashboard.por_estado || {}).map(([estado, valor]) => ({
    label: ETIQUETA_POR_ESTADO[estado] || estado,
    value: valor,
    color: COLOR_POR_ESTADO[estado] || "#535353",
  }));
  const totalEnCiclo = porEstadoData.reduce((acc, d) => acc + d.value, 0);

  // ── Agregados client-side sobre la muestra de préstamos del período
  //    filtrado (ver nota en LOANS_SAMPLE_LIMIT).
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

  const handleDownloadPdf = async () => {
    if (pdfState !== "idle") return;
    setPdfError(null);
    pdfSnapshotRef.current = {
      dashboard,
      porEstadoData,
      totalEnCiclo,
      porMes,
      topEquipos,
      tasaDevolucionData,
      totalFinalizados,
      loansForbidden,
      dateRange,
      generatedAt: new Date(),
      generatedByName: user?.full_name,
    };
    setPdfState("rendering");
    try {
      // La plantilla off-screen se monta recién ahora; se espera un tick de
      // pintado (ApexCharts renderiza su SVG de forma asíncrona) antes de
      // capturarla con html2canvas.
      await new Promise((resolve) => requestAnimationFrame(resolve));
      await new Promise((resolve) => requestAnimationFrame(resolve));
      await new Promise((resolve) => setTimeout(resolve, 500));

      setPdfState("generating");
      const start = fmtDateParam(dateRange.start) || "historico";
      const end = fmtDateParam(dateRange.end) || "actual";
      await generateEquiposDashboardPdf({ filename: `reporte-equipos_${start}_a_${end}.pdf` });
    } catch (e) {
      setPdfError(e.message || "No se pudo generar el PDF.");
    } finally {
      setPdfState("idle");
    }
  };

  return (
    <div className="space-y-8">
      <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
        Dashboard
      </h1>

      {/* ── Filtro de fechas + exportación (patrón: Dashboard.jsx) ───────── */}
      <GlassPanel as="div" className="flex flex-wrap items-end justify-between gap-4 p-4 sm:p-6">
        <DateRangeFilter
          startDate={dateRange.start}
          endDate={dateRange.end}
          onChange={(start, end) => setDateRange({ start, end })}
        />
        <button
          type="button"
          onClick={handleDownloadPdf}
          disabled={loadingLoans || pdfState !== "idle"}
          className="btn-go-ghost shrink-0"
        >
          {pdfState === "idle" && "Descargar PDF"}
          {pdfState === "rendering" && "Preparando reporte…"}
          {pdfState === "generating" && "Generando PDF…"}
        </button>
      </GlassPanel>

      {pdfError && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
        >
          {pdfError}
        </div>
      )}

      {/* ── KPIs de estado actual (no dependen del filtro de fechas) ─────── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <KpiTile label="Prestados" value={dashboard.prestados} accentColor="#FB670B" glass />
        <KpiTile label="Atrasados" value={dashboard.atrasados} accentColor="#E53E3E" glass />
        <KpiTile label="Pend. confirmación" value={dashboard.pendientes_confirmacion} accentColor="#F59E0B" glass />
        <KpiTile label="Disponibles" value={dashboard.disponibles} accentColor="#00A36E" glass />
        <KpiTile
          label="Tiempo promedio"
          value={tiempoPromedioActivo != null ? Math.round(tiempoPromedioActivo) : "—"}
          hint="días, préstamos activos en el período"
          accentColor="#A78BFA"
          glass
        />
      </div>

      {loansError && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
        >
          {loansError}
        </div>
      )}

      {loansForbidden ? (
        <EmptyState title="Sin permiso para ver préstamos" message="Estas métricas requieren acceso a préstamos de equipo." />
      ) : loadingLoans ? (
        <div className="space-y-6">
          <SkeletonShimmer className="h-80" />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <SkeletonShimmer className="h-80" />
            <SkeletonShimmer className="h-80" />
          </div>
        </div>
      ) : (
        <>
          <GlassPanel as="section" className="p-4 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
                Préstamos por mes
              </h2>
              {muestraParcial && <span className="go-eyebrow">Últimos {loans.length} de {loansTotal}</span>}
            </div>
            <LoansByMonthChart data={porMes} />
          </GlassPanel>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <GlassPanel as="section" className="p-4 sm:p-6">
              <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
                Top equipos prestados
              </h2>
              <TopEquipmentChart data={topEquipos} />
            </GlassPanel>

            <GlassPanel as="section" className="p-4 sm:p-6">
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
            </GlassPanel>
          </div>
        </>
      )}

      {/* ── Distribución de estados: viene del snapshot, no del filtro ───── */}
      <GlassPanel as="section" className="p-4 sm:p-6">
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
      </GlassPanel>

      {/* ── Plantilla off-screen para el PDF, solo montada al generar ────── */}
      {pdfState !== "idle" && pdfSnapshotRef.current && (
        <EquiposDashboardPdfTemplate {...pdfSnapshotRef.current} />
      )}
    </div>
  );
}
