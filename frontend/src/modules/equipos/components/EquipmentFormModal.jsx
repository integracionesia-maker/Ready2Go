import { useState } from "react";
import { GlassModal } from "@/design";
import { createEquipment, updateEquipment } from "../api";

// Metadata de inventario (equipos_inventario:crear/:editar). La condición
// (bueno/atencion), estado_fisico, comentario_auditoria y fecha_auditoria
// NO viven aquí: son el permiso y el formulario separado de "auditoria"
// (EquipmentAuditModal) — dos acciones del contrato, dos formularios.
export default function EquipmentFormModal({ equipo, onClose, onSuccess }) {
  const editando = Boolean(equipo);

  const [nombre, setNombre] = useState(equipo?.nombre || "");
  const [categoria, setCategoria] = useState(equipo?.categoria || "");
  const [marca, setMarca] = useState(equipo?.marca || "");
  const [modelo, setModelo] = useState(equipo?.modelo || "");
  const [numeroSerie, setNumeroSerie] = useState(equipo?.numero_serie || "");
  const [activoFijo, setActivoFijo] = useState(equipo?.activo_fijo || "");
  const [cuentaGmail, setCuentaGmail] = useState(equipo?.cuenta_gmail || "");
  const [espacioDisponible, setEspacioDisponible] = useState(equipo?.espacio_disponible || "");
  const [accesorios, setAccesorios] = useState((equipo?.accesorios_tipicos || []).join(", "));

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!nombre.trim() || !categoria.trim()) {
      setError("Nombre y categoría son obligatorios.");
      return;
    }

    const data = {
      nombre: nombre.trim(),
      categoria: categoria.trim(),
      marca: marca.trim() || null,
      modelo: modelo.trim() || null,
      numero_serie: numeroSerie.trim() || null,
      activo_fijo: activoFijo.trim() || null,
      cuenta_gmail: cuentaGmail.trim() || null,
      espacio_disponible: espacioDisponible.trim() || null,
      accesorios_tipicos: accesorios
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean),
    };
    // I8 lote 1/2: `EquipmentCreate` (schema real) no declara ni
    // `estado_operativo` ni `condicion` — Pydantic descarta cualquier clave
    // no declarada antes de que `crud_equipment.crear` la vea, así que
    // mandarlas desde aquí era inerte (el servidor ya default a "activo" y
    // "bueno" el mismo). Se deja de inventar campos que el servidor ignora;
    // el mock ahora pone esos mismos defaults por su cuenta.

    setSubmitting(true);
    setError(null);
    try {
      if (editando) {
        await updateEquipment(equipo.id, data);
      } else {
        await createEquipment(data);
      }
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <GlassModal
      open
      onClose={submitting ? undefined : onClose}
      title={editando ? "Editar equipo" : "Nuevo equipo"}
      footer={
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} disabled={submitting} className="btn-go-ghost">
            Cancelar
          </button>
          <button type="submit" form="equipment-form" disabled={submitting} className="btn-go">
            {submitting ? "Guardando..." : editando ? "Guardar cambios" : "Crear equipo"}
          </button>
        </div>
      }
    >
      <form id="equipment-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="go-eyebrow mb-1.5 block">Nombre</label>
          <input type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} className="go-input" required />
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Categoría</label>
          <input type="text" value={categoria} onChange={(e) => setCategoria(e.target.value)} className="go-input" required />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="go-eyebrow mb-1.5 block">Marca</label>
            <input type="text" value={marca} onChange={(e) => setMarca(e.target.value)} className="go-input" />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Modelo</label>
            <input type="text" value={modelo} onChange={(e) => setModelo(e.target.value)} className="go-input" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="go-eyebrow mb-1.5 block">Número de serie</label>
            <input type="text" value={numeroSerie} onChange={(e) => setNumeroSerie(e.target.value)} className="go-input" />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Activo fijo</label>
            <input type="text" value={activoFijo} onChange={(e) => setActivoFijo(e.target.value)} className="go-input" />
          </div>
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Cuenta de Gmail asociada</label>
          <input type="email" value={cuentaGmail} onChange={(e) => setCuentaGmail(e.target.value)} className="go-input" />
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Espacio disponible</label>
          <input
            type="text"
            value={espacioDisponible}
            onChange={(e) => setEspacioDisponible(e.target.value)}
            placeholder="ej. 87.43 GB de 256 GB"
            className="go-input"
          />
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Accesorios típicos (separados por coma)</label>
          <input
            type="text"
            value={accesorios}
            onChange={(e) => setAccesorios(e.target.value)}
            placeholder="Cargador, Funda"
            className="go-input"
          />
        </div>

        {error && (
          <div
            className="rounded-go border px-4 py-3 font-body text-sm"
            style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
          >
            {error}
          </div>
        )}
      </form>
    </GlassModal>
  );
}
