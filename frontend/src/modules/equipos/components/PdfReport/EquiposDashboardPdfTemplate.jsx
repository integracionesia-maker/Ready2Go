import LoansByMonthChart from "../charts/LoansByMonthChart";
import TopEquipmentChart from "../charts/TopEquipmentChart";
import { StatusDonut } from "@/design";
import KpiCard from "@/modules/presupuestos/components/KpiCard";
import isotipoNaranja from "@/assets/logos/isotipo-go-naranja.png";

function formatDateLong(d) {
  if (!d) return "—";
  return new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "long", year: "numeric" }).format(d);
}

function formatDateTimeLong(d) {
  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

const SECTION_STYLE = {
  width: "900px",
  padding: "28px 32px",
  background: "#ffffff",
  boxSizing: "border-box",
};

/**
 * Plantilla de impresión del Dashboard de Equipos (C2), renderizada fuera de
 * pantalla y capturada sección por sección con html2canvas. Mismo patrón que
 * `presupuestos/components/PdfReport/DashboardPdfTemplate.jsx`: fuerza tema
 * claro vía `data-theme="light"` en el contenedor raíz.
 */
export default function EquiposDashboardPdfTemplate({
  dashboard,
  porEstadoData,
  totalEnCiclo,
  porMes,
  topEquipos,
  tasaDevolucionData,
  totalFinalizados,
  loansForbidden,
  dateRange,
  generatedAt,
  generatedByName,
}) {
  const periodLabel =
    dateRange.start && dateRange.end
      ? `${formatDateLong(dateRange.start)} — ${formatDateLong(dateRange.end)}`
      : "Todo el historial";

  return (
    <div id="equipos-pdf-report-root" data-theme="light" style={{ position: "fixed", top: 0, left: "-10000px", zIndex: -1 }}>
      {/* ── Sección 1: encabezado + KPIs ────────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
          <img
            src={isotipoNaranja}
            alt="Grupo Ortiz"
            style={{ height: "36px", width: "auto", display: "block" }}
          />
          <div>
            <h1
              className="font-display"
              style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#262626", textTransform: "uppercase", letterSpacing: "0.06em" }}
            >
              Grupo Ortiz — Control de Equipos
            </h1>
            <p className="font-body" style={{ margin: 0, fontSize: "11px", color: "#535353" }}>
              Reporte de préstamos de equipo de grabación
            </p>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "11px",
            color: "#535353",
            borderTop: "1px solid #dcdbd0",
            borderBottom: "1px solid #dcdbd0",
            padding: "8px 0",
            margin: "12px 0 20px",
          }}
        >
          <span>Período: {periodLabel}</span>
          <span>Generado: {formatDateTimeLong(generatedAt)}{generatedByName ? ` por ${generatedByName}` : ""}</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
          <KpiCard title="Prestados" value={dashboard.prestados} accent="orange" />
          <KpiCard title="Atrasados" value={dashboard.atrasados} accent="turquoise" />
          <KpiCard title="Pend. confirmación" value={dashboard.pendientes_confirmacion} accent="sky" />
          <KpiCard title="Disponibles" value={dashboard.disponibles} accent="violet" />
        </div>
      </div>

      {/* ── Sección 2: préstamos por mes ────────────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Préstamos por Mes
        </h2>
        {loansForbidden ? (
          <p style={{ fontSize: "12px", color: "#535353" }}>Sin permiso para ver préstamos.</p>
        ) : (
          <LoansByMonthChart data={porMes} forceTheme="light" />
        )}
      </div>

      {/* ── Sección 3: top equipos + tasa de devolución ──────────────────── */}
      <div className="pdf-section" style={{ ...SECTION_STYLE, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        <div>
          <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
            Top Equipos Prestados
          </h2>
          {loansForbidden ? (
            <p style={{ fontSize: "12px", color: "#535353" }}>Sin permiso para ver préstamos.</p>
          ) : (
            <TopEquipmentChart data={topEquipos} forceTheme="light" />
          )}
        </div>
        <div>
          <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
            Tasa de Devolución a Tiempo
          </h2>
          {loansForbidden ? (
            <p style={{ fontSize: "12px", color: "#535353" }}>Sin permiso para ver préstamos.</p>
          ) : totalFinalizados === 0 ? (
            <p style={{ fontSize: "12px", color: "#535353" }}>Sin préstamos finalizados en este período.</p>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
              <StatusDonut data={tasaDevolucionData} centerValue={totalFinalizados} centerLabel="finalizados" />
              <ul style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", color: "#535353", listStyle: "none", margin: 0, padding: 0 }}>
                {tasaDevolucionData.map((d) => (
                  <li key={d.label}>
                    <span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "50%", background: d.color, marginRight: "6px" }} />
                    {d.label}: <strong style={{ color: "#262626" }}>{d.value}</strong>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* ── Sección 4: distribución de estados ───────────────────────────── */}
      <div className="pdf-section" style={SECTION_STYLE}>
        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Distribución de Estados (Estado Actual)
        </h2>
        {totalEnCiclo === 0 ? (
          <p style={{ fontSize: "12px", color: "#535353" }}>Sin préstamos en curso.</p>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
            <StatusDonut data={porEstadoData} centerValue={totalEnCiclo} centerLabel="préstamos" />
            <ul style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", color: "#535353", listStyle: "none", margin: 0, padding: 0 }}>
              {porEstadoData.map((d) => (
                <li key={d.label}>
                  <span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "50%", background: d.color, marginRight: "6px" }} />
                  {d.label}: <strong style={{ color: "#262626" }}>{d.value}</strong>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
