import { useMemo, useState } from "react";
import Modal from "./Modal";
import GeneralExpensesPdfTemplate from "./PdfReport/GeneralExpensesPdfTemplate";
import { generateGeneralExpensesPdf } from "./PdfReport/generateGeneralExpensesPdf";
import { useAuth } from "@/context/AuthContext";
import { fetchGeneralExpensesExport } from "@/api";
import { useMobile } from "@/design";

/** Genera los valores YYYY-MM para los últimos `count` meses (incluyendo el actual). */
function lastNMonths(count) {
  const now = new Date();
  const months = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return months;
}

const PRESETS = [
  { label: "Este mes", months: lastNMonths(1) },
  { label: "Últimos 3 meses", months: lastNMonths(3) },
  { label: "Últimos 6 meses", months: lastNMonths(6) },
  { label: "Todo el año", months: lastNMonths(12) },
];

export default function GeneralExpensesExportModal({ onClose }) {
  const { user } = useAuth();
  const isMobile = useMobile();
  const months = useMemo(() => lastNMonths(12), []);

  const [selectedMonths, setSelectedMonths] = useState([]);
  const [exportData, setExportData] = useState(null);
  const [pdfState, setPdfState] = useState("idle"); // idle | rendering | generating
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const toggleMonth = (value) => {
    setSelectedMonths((prev) =>
      prev.includes(value) ? prev.filter((m) => m !== value) : [...prev, value]
    );
  };

  const applyPreset = (presetMonths) => {
    setSelectedMonths([...presetMonths]);
  };

  const handleGenerate = async () => {
    if (selectedMonths.length === 0 || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await fetchGeneralExpensesExport(selectedMonths);
      setExportData(result);
      setPdfState("rendering");

      await new Promise((resolve) => requestAnimationFrame(resolve));
      await new Promise((resolve) => requestAnimationFrame(resolve));
      await new Promise((resolve) => setTimeout(resolve, 500));

      setPdfState("generating");
      const sortedMonths = [...selectedMonths].sort();
      const filename = `gastos-generales_${sortedMonths[0]}_a_${sortedMonths[sortedMonths.length - 1]}.pdf`;
      await generateGeneralExpensesPdf({ filename });
    } catch (err) {
      setError(err.message || "No se pudo generar el PDF.");
    } finally {
      setPdfState("idle");
      setSubmitting(false);
    }
  };

  const errorBanner = error && (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{
        background: "rgba(229,62,62,0.08)",
        borderColor: "rgba(229,62,62,0.25)",
        color: "var(--go-error)",
      }}
    >
      {error}
    </div>
  );

  const capitalize = (s) => {
    if (!s) return s;
    const [y, m] = s.split("-");
    const d = new Date(Number(y), Number(m) - 1, 1);
    // En móvil, "Jul 2026" en vez de "Julio 2026" — dos columnas de ~140px
    // no alcanzan para el nombre completo del mes (auditoría móvil, M5).
    const monthName = new Intl.DateTimeFormat("es-MX", { month: isMobile ? "short" : "long" }).format(d);
    return `${monthName.charAt(0).toUpperCase() + monthName.slice(1)} ${y}`;
  };

  const buttonLabel =
    pdfState === "rendering"
      ? "Preparando reporte..."
      : pdfState === "generating"
      ? "Generando PDF..."
      : "Generar PDF";

  return (
    <Modal title="Exportar Gastos Generales" onClose={onClose} submitting={submitting}>
      <div className="space-y-4 px-4 sm:px-6 py-5">
        <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          Selecciona los meses que quieres incluir en el reporte.
        </p>

        {/* ── Preset buttons ──────────────────────────────────────────── */}
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset.months)}
              disabled={submitting}
              className="btn-go-ghost text-xs px-3 py-1.5"
            >
              {preset.label}
            </button>
          ))}
        </div>

        {/* ── Month checkboxes ────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {months.map((m) => (
            <label
              key={m}
              className="flex items-center gap-2 rounded-go border px-3 py-2 font-body text-sm cursor-pointer"
              style={{
                borderColor: selectedMonths.includes(m) ? "var(--go-orange)" : "var(--go-border)",
                color: "var(--go-text-primary)",
                background: selectedMonths.includes(m) ? "var(--go-orange-tint)" : "transparent",
              }}
            >
              <input
                type="checkbox"
                checked={selectedMonths.includes(m)}
                onChange={() => toggleMonth(m)}
                disabled={submitting}
              />
              {capitalize(m)}
            </label>
          ))}
        </div>

        {errorBanner}

        <div className="flex items-center justify-between pt-2">
          <span className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
            {selectedMonths.length} mes(es) seleccionados
          </span>
          <div className="flex items-center gap-3">
            <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={submitting || selectedMonths.length === 0}
              className="btn-go"
            >
              {buttonLabel}
            </button>
          </div>
        </div>
      </div>

      {/* ── Plantilla off-screen para el PDF, solo montada al generar ── */}
      {pdfState !== "idle" && exportData && (
        <GeneralExpensesPdfTemplate
          months={exportData.months}
          items={exportData.items}
          total={exportData.total}
          generatedAt={new Date()}
          generatedByName={user?.full_name}
        />
      )}
    </Modal>
  );
}
