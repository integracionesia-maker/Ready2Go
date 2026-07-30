import { useEffect, useState } from "react";
import { GlassModal, useToast } from "@/design";
import { fetchEquipmentById, dischargeEquipment } from "../api";
import { usePermisos } from "../permisos/usePermisos";
import RequierePermiso from "../permisos/RequierePermiso";

const CAMPOS = [
  ["marca", "Marca"],
  ["modelo", "Modelo"],
  ["numero_serie", "Número de serie", true],
  ["activo_fijo", "Activo fijo", true],
  ["cuenta_gmail", "Cuenta de Gmail"],
  ["espacio_disponible", "Espacio disponible"],
];

/** Ficha de un equipo: GET /api/equipment/{id} fresco (no reusa la fila del
 * listado) — para que auditoria/edicion recientes se reflejen sin recargar
 * toda la pagina. */
export default function EquipmentFichaModal({ equipoId, onClose, onEditar, onAuditar, onCambio }) {
  const { puede } = usePermisos();
  const { push } = useToast();
  const [equipo, setEquipo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dandoBaja, setDandoBaja] = useState(false);

  async function cargar() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEquipmentById(equipoId);
      setEquipo(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [equipoId]);

  async function handleBaja() {
    setDandoBaja(true);
    try {
      await dischargeEquipment(equipoId);
      push({ tone: "success", title: "Equipo dado de baja" });
      onCambio?.();
      await cargar();
    } catch (e) {
      // 409 EQUIPO_OCUPADO: se pinta el detail del servidor tal cual, no un
      // texto propio que pueda quedar desalineado con la regla de negocio.
      push({ tone: "error", title: "No se pudo dar de baja", message: e.detail || e.message });
    } finally {
      setDandoBaja(false);
    }
  }

  return (
    <GlassModal open onClose={onClose} title={equipo ? equipo.nombre : "Ficha de equipo"}>
      {loading && <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>Cargando...</p>}

      {error && (
        <div
          className="rounded-go border px-4 py-3 font-body text-sm"
          style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
        >
          {error}
        </div>
      )}

      {equipo && !loading && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-1.5">
            <span className="go-badge go-badge-neutral">{equipo.categoria}</span>
            <span className={`go-badge ${equipo.condicion === "bueno" ? "go-badge-success" : "go-badge-warning"}`}>
              {equipo.condicion || "sin auditar"}
            </span>
            <span className={`go-badge ${equipo.disponible ? "go-badge-success" : "go-badge-neutral"}`}>
              {equipo.disponible ? "Disponible" : "No disponible"}
            </span>
            {equipo.estado_operativo !== "activo" && (
              <span className="go-badge go-badge-warning">{equipo.estado_operativo}</span>
            )}
          </div>

          <dl className="grid grid-cols-2 gap-3 font-body text-sm">
            {CAMPOS.map(([campo, label, mono]) => (
              <div key={campo}>
                <dt className="font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
                  {label}
                </dt>
                <dd className={mono ? "font-mono" : undefined} style={{ color: "var(--go-text-primary)" }}>
                  {equipo[campo] || "—"}
                </dd>
              </div>
            ))}
          </dl>

          {equipo.accesorios_tipicos?.length > 0 && (
            <div>
              <p className="mb-1 font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
                Accesorios típicos
              </p>
              <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                {equipo.accesorios_tipicos.join(", ")}
              </p>
            </div>
          )}

          {equipo.tenedor_actual && (
            <div className="go-card font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
              Con <span style={{ color: "var(--go-text-primary)" }}>{equipo.tenedor_actual.nombre}</span>
              {equipo.fecha_regreso_esperada && (
                <>
                  {" "}· regresa <span className="font-mono">{equipo.fecha_regreso_esperada}</span>
                </>
              )}
              {equipo.atrasado && (
                <span className="go-badge go-badge-error ml-2">Atrasado {equipo.dias_atraso}d</span>
              )}
            </div>
          )}

          {/* estado_fisico/comentario_auditoria/fecha_auditoria: solo si
              vienen (R-I10) — no estan en el contrato congelado. */}
          {(equipo.estado_fisico || equipo.comentario_auditoria) && (
            <div className="border-t pt-3" style={{ borderColor: "var(--go-border)" }}>
              <p className="mb-1 font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
                Última auditoría{" "}
                {equipo.fecha_auditoria && <>· <span className="font-mono">{equipo.fecha_auditoria}</span></>}
              </p>
              {equipo.estado_fisico && (
                <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                  Estado físico: {equipo.estado_fisico}
                </p>
              )}
              {equipo.comentario_auditoria && (
                <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                  {equipo.comentario_auditoria}
                </p>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-4" style={{ borderColor: "var(--go-border)" }}>
            <RequierePermiso modulo="equipos_inventario" accion="editar">
              <button type="button" onClick={() => onEditar(equipo)} className="btn-go-ghost text-xs px-3 py-1.5">
                Editar
              </button>
            </RequierePermiso>
            <RequierePermiso modulo="equipos_inventario" accion="auditar_condicion">
              <button type="button" onClick={() => onAuditar(equipo)} className="btn-go-ghost text-xs px-3 py-1.5">
                Auditar condición
              </button>
            </RequierePermiso>
            {puede("equipos_inventario", "dar_de_baja") && equipo.estado_operativo === "activo" && (
              <button
                type="button"
                onClick={handleBaja}
                disabled={dandoBaja}
                className="btn-go-ghost text-xs px-3 py-1.5"
                style={{ color: "var(--go-error)" }}
              >
                {dandoBaja ? "Dando de baja..." : "Dar de baja"}
              </button>
            )}
          </div>
        </div>
      )}
    </GlassModal>
  );
}
