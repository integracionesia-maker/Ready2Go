const OPCIONES_CARGADOR = [
  { value: "responsable", label: "Se lo lleva el responsable" },
  { value: "empresa", label: "Se queda en resguardo" },
];

/** `equipo.accesorios_tipicos` (contrato) + "otros" libre. `cargador_con` es
 * obligatorio si el equipo declara un accesorio que contiene "cargador"
 * (hallazgo 22) — sin eso, nadie sabe si el cargador viaja con el equipo o
 * se queda en la empresa. */
export default function AccesoriosPicker({ accesoriosTipicos = [], value, onChange }) {
  const requiereCargador = accesoriosTipicos.some((a) => a.toLowerCase().includes("cargador"));
  const { seleccionados = [], otros = "", cargadorCon = "" } = value || {};

  function toggle(acc) {
    const next = seleccionados.includes(acc) ? seleccionados.filter((a) => a !== acc) : [...seleccionados, acc];
    onChange({ seleccionados: next, otros, cargadorCon });
  }

  return (
    <div className="space-y-3">
      {accesoriosTipicos.length > 0 && (
        <div>
          <p className="go-eyebrow mb-1.5">Accesorios incluidos</p>
          <div className="flex flex-wrap gap-2">
            {accesoriosTipicos.map((acc) => (
              <label
                key={acc}
                className="flex cursor-pointer items-center gap-1.5 rounded-go border px-2.5 py-1 font-body text-xs"
                style={{
                  borderColor: seleccionados.includes(acc) ? "var(--go-orange)" : "var(--go-border)",
                  color: "var(--go-text-primary)",
                }}
              >
                <input
                  type="checkbox"
                  checked={seleccionados.includes(acc)}
                  onChange={() => toggle(acc)}
                  className="h-3.5 w-3.5"
                />
                {acc}
              </label>
            ))}
          </div>
        </div>
      )}

      <div>
        <label className="go-eyebrow mb-1.5 block">Otros accesorios (opcional)</label>
        <input
          type="text"
          value={otros}
          onChange={(e) => onChange({ seleccionados, otros: e.target.value, cargadorCon })}
          className="go-input"
        />
      </div>

      {requiereCargador && (
        <div>
          <label className="go-eyebrow mb-1.5 block">¿Con quién va el cargador?</label>
          <select
            value={cargadorCon}
            onChange={(e) => onChange({ seleccionados, otros, cargadorCon: e.target.value })}
            className="go-select"
            required
          >
            <option value="">Selecciona...</option>
            {OPCIONES_CARGADOR.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
