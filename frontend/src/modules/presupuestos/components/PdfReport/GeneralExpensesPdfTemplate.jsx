import isotipoNaranja from "@/assets/logos/isotipo-go-naranja.png";

function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount || 0);
}

function formatDateShort(iso) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "short", year: "numeric" }).format(
    new Date(iso)
  );
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

/* months: arreglo de strings "YYYY-MM" -> "julio 2026" */
function formatMonthLabel(monthStr) {
  const [year, month] = monthStr.split("-").map(Number);
  const d = new Date(year, (month || 1) - 1, 1);
  return new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" }).format(d);
}

const SECTION_STYLE = {
  width: "900px",
  padding: "28px 32px",
  background: "#ffffff",
  boxSizing: "border-box",
};

/**
 * Plantilla de impresión de Gastos Generales (R8), renderizada fuera de
 * pantalla y capturada con html2canvas para armar el PDF. Fuerza tema claro
 * vía el atributo `data-theme="light"` del contenedor raíz — ver la nota en
 * index.css sobre por qué ese selector ya no exige `:root`.
 */
export default function GeneralExpensesPdfTemplate({ months, items, total, generatedAt, generatedByName }) {
  const periodLabel = months && months.length > 0 ? months.map(formatMonthLabel).join(", ") : "Todo el historial";

  return (
    <div
      id="general-expenses-pdf-root"
      data-theme="light"
      style={{ position: "fixed", top: 0, left: "-10000px", zIndex: -1 }}
    >
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
              Grupo Ortiz — Reporte de Gastos Generales
            </h1>
            <p className="font-body" style={{ margin: 0, fontSize: "11px", color: "#535353" }}>
              Reporte de gastos operativos por marca
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

        <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#262626", marginBottom: "12px" }}>
          Detalle de Gastos Generales
        </h2>
        {!items || items.length === 0 ? (
          <p style={{ fontSize: "12px", color: "#535353" }}>Sin gastos generales en el periodo seleccionado.</p>
        ) : (
          <>
            <table className="go-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Marca</th>
                  <th>Descripción</th>
                  <th style={{ textAlign: "right" }}>Monto</th>
                  <th>Comprobante</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDateShort(item.upload_date)}</td>
                    <td>{item.brand_name || `ID ${item.brand_id}`}</td>
                    <td>{item.description}</td>
                    <td className="num" style={{ textAlign: "right" }}>{formatCurrency(item.amount)}</td>
                    <td>{item.file_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "12px",
                marginTop: "16px",
                paddingTop: "12px",
                borderTop: "1px solid #dcdbd0",
                fontSize: "13px",
                fontWeight: 700,
                color: "#262626",
              }}
            >
              <span>Total General:</span>
              <span className="num">{formatCurrency(total)}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
