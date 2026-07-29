import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { EmptyState, SkeletonShimmer, useToast } from "@/design";
import { esCodigo } from "@/api";
import { useAuth } from "@/context/AuthContext";
import {
  createLoan,
  fetchLoans,
  fetchLoanById,
  addLoanItem,
  removeLoanItem,
  cancelLoan,
  confirmLoan,
  uploadMedia,
  fetchEmpresas,
  fetchEquipmentList,
} from "../api";
import AccesoriosPicker from "../components/AccesoriosPicker";
import PhotoCapture from "../components/PhotoCapture";
import SignaturePad from "../components/SignaturePad";

const PASOS = ["Datos", "Equipos", "Fotos", "Firmas"];

function itemListo(item) {
  return Boolean(item.media.foto_entrega_frente && item.media.foto_entrega_atras);
}

export default function NuevoPrestamoPage() {
  const { user, logout } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();

  const [cargandoInicial, setCargandoInicial] = useState(true);
  const [errorInicial, setErrorInicial] = useState(null);
  const [borradorPrevio, setBorradorPrevio] = useState(null);
  const [reanudando, setReanudando] = useState(false);
  const [empresas, setEmpresas] = useState([]);

  const [loan, setLoan] = useState(null);
  const [paso, setPaso] = useState(1);

  // Paso 1
  const [area, setArea] = useState("");
  const [empresaSel, setEmpresaSel] = useState("");
  const [motivo, setMotivo] = useState("");
  const [fechaRegreso, setFechaRegreso] = useState("");
  const [notas, setNotas] = useState("");
  const [enviandoPaso1, setEnviandoPaso1] = useState(false);
  const [errorPaso1, setErrorPaso1] = useState(null);

  // Paso 2
  const [disponibles, setDisponibles] = useState([]);
  const [cargandoDisponibles, setCargandoDisponibles] = useState(false);
  const [agregandoId, setAgregandoId] = useState(null);
  const [accesoriosTmp, setAccesoriosTmp] = useState({});
  const [guardandoItem, setGuardandoItem] = useState(false);

  const firmaEntregaRef = useRef(null);
  const firmaResponsableRef = useRef(null);
  const [confirmando, setConfirmando] = useState(false);
  const [errorConfirmar, setErrorConfirmar] = useState(null);

  // Sesión caída a mitad del wizard (real o simulada por el mock):
  // desloguea igual que cualquier 401 real — el borrador y lo ya subido
  // viven en el servidor, se recuperan al volver a entrar.
  async function conManejoDeSesion(fn) {
    try {
      return await fn();
    } catch (e) {
      if (e.status === 401) {
        push({ tone: "warning", title: "Tu sesión expiró", message: "Lo que ya guardaste sigue en el servidor. Vuelve a entrar para continuar." });
        await logout();
      }
      throw e;
    }
  }

  useEffect(() => {
    async function init() {
      try {
        const [emp, borradores] = await Promise.all([
          fetchEmpresas(),
          fetchLoans({ estado: "borrador", mios: true }),
        ]);
        setEmpresas(emp.filter((e) => e.is_active));
        if (borradores.items.length > 0) {
          setBorradorPrevio(borradores.items[0]);
        }
      } catch (e) {
        if (!esCodigo(e, "PERMISOS_NO_DISPONIBLES")) setErrorInicial(e.message);
        else setErrorInicial("No se pudieron resolver los permisos. Reintenta en un momento.");
      } finally {
        setCargandoInicial(false);
      }
    }
    init();
  }, []);

  async function reanudarBorrador(borradorRow) {
    // I8 lote 2 (hallazgo, mismo patrón que I8 lote 1): `fetchLoans(...)`
    // devuelve `LoanRow` (fila liviana del listado), sin `items[]` — esta
    // función asumía la ficha completa y tronaba en silencio ("Cannot read
    // properties of undefined (reading 'length')", un evento de click, no
    // de render, así que React no lo mostraba en ningún lado) apenas alguien
    // dejaba un préstamo a medias y volvía a /equipos/nuevo: el botón
    // "Continuar borrador" no hacía absolutamente nada contra el servidor
    // real. Se pide la ficha completa antes de reanudar, igual que
    // `ActivosPage`/`AprobacionesPage` ya hacen para sus modales.
    setReanudando(true);
    try {
      const borrador = await fetchLoanById(borradorRow.id);
      setLoan(borrador);
      setArea(borrador.area || "");
      setEmpresaSel(borrador.empresa || "");
      setMotivo(borrador.motivo || "");
      setFechaRegreso(borrador.fecha_regreso_esperada || "");
      setNotas(borrador.notas_responsiva || "");
      if (borrador.items.length === 0) setPaso(2);
      else if (!borrador.items.every(itemListo)) setPaso(3);
      else setPaso(4);
      setBorradorPrevio(null);
    } catch (e) {
      push({ tone: "error", title: "No se pudo continuar el borrador", message: e.detail || e.message });
    } finally {
      setReanudando(false);
    }
  }

  async function descartarBorrador(borrador) {
    try {
      await cancelLoan(borrador.id);
    } catch {
      // Si ya no se puede cancelar (p. ej. alguien más lo movió), igual se
      // sigue con uno nuevo — no vale la pena bloquear al usuario por esto.
    }
    setBorradorPrevio(null);
  }

  async function cargarDisponibles() {
    setCargandoDisponibles(true);
    try {
      const data = await fetchEquipmentList({ disponible: true, limit: 200 });
      setDisponibles(data.items);
    } catch (e) {
      push({ tone: "error", title: "No se pudo cargar el inventario", message: e.message });
    } finally {
      setCargandoDisponibles(false);
    }
  }

  useEffect(() => {
    if (paso === 2 && loan) cargarDisponibles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paso, loan?.id]);

  async function handleSubmitPaso1(e) {
    e.preventDefault();
    setErrorPaso1(null);
    setEnviandoPaso1(true);
    try {
      // I8 lote 1 (bug latente, R-I14): `LoanCreate` espera las tres claves
      // de responsable PLANAS (`responsable_user_id/nombre/email`), no un
      // objeto anidado. Pydantic ignora silenciosamente una clave `responsable`
      // desconocida y el servidor cae a `current_user` — hoy coincide
      // siempre (el wizard es autoservicio, nadie pide equipo para otra
      // persona), así que nada se ve roto. El día que exista un selector de
      // "pedir para alguien más", el préstamo se habría asignado a quien
      // llena el formulario, no a quien realmente lo va a usar, sin un solo
      // error visible.
      const nuevo = await conManejoDeSesion(() =>
        createLoan({
          responsable_user_id: user.id,
          responsable_nombre: user.full_name,
          responsable_email: user.email,
          area,
          empresa: empresaSel,
          motivo,
          fecha_regreso_esperada: fechaRegreso,
          notas_responsiva: notas || null,
        })
      );
      setLoan(nuevo);
      setPaso(2);
    } catch (e) {
      setErrorPaso1(e.message);
    } finally {
      setEnviandoPaso1(false);
    }
  }

  function abrirAgregar(equipo) {
    setAgregandoId(equipo.id);
    setAccesoriosTmp((prev) => ({ ...prev, [equipo.id]: prev[equipo.id] || { seleccionados: [], otros: "", cargadorCon: "" } }));
  }

  async function confirmarAgregar(equipo) {
    const acc = accesoriosTmp[equipo.id] || { seleccionados: [], otros: "", cargadorCon: "" };
    const requiereCargador = (equipo.accesorios_tipicos || []).some((a) => a.toLowerCase().includes("cargador"));
    if (requiereCargador && !acc.cargadorCon) {
      push({ tone: "error", title: "Falta un dato", message: "Indica con quién va el cargador de este equipo." });
      return;
    }
    setGuardandoItem(true);
    try {
      await conManejoDeSesion(() =>
        addLoanItem(loan.id, {
          equipmentId: equipo.id,
          accesoriosSeleccionados: acc.seleccionados,
          accesoriosOtros: acc.otros || null,
          cargadorCon: acc.cargadorCon || null,
        })
      );
      // Se refresca desde el servidor en vez de anexar `item` a mano: el
      // mock devuelve referencias vivas a su estado interno, no copias —
      // reconstruir el array del lado del cliente duplicaba el ítem
      // (el mock ya lo había empujado al mismo array que `loan.items`
      // referenciaba). Contra el backend real esto es, ademas, el patron
      // mas seguro de cualquier forma: la fuente de verdad es el servidor.
      setLoan(await fetchLoanById(loan.id));
      setAgregandoId(null);
    } catch (e) {
      if (esCodigo(e, "EQUIPO_OCUPADO")) {
        // No se tira la selección hecha hasta ahora — solo este equipo sale
        // de la lista de disponibles y se avisa; el resto del wizard sigue.
        push({ tone: "warning", title: "Ese equipo ya no está disponible", message: e.detail });
        setAgregandoId(null);
        cargarDisponibles();
      } else {
        push({ tone: "error", title: "No se pudo agregar el equipo", message: e.detail || e.message });
      }
    } finally {
      setGuardandoItem(false);
    }
  }

  async function handleQuitarItem(item) {
    try {
      await removeLoanItem(loan.id, item.id);
      setLoan(await fetchLoanById(loan.id));
      cargarDisponibles();
    } catch (e) {
      push({ tone: "error", title: "No se pudo quitar el equipo", message: e.message });
    }
  }

  async function handleUploadFoto(item, kind, blob) {
    const file = new File([blob], `${kind}.jpg`, { type: blob.type });
    await conManejoDeSesion(() => uploadMedia(loan.id, { file, kind, loanItemId: item.id }));
    setLoan(await fetchLoanById(loan.id));
  }

  async function handleConfirmar() {
    setErrorConfirmar(null);
    if (firmaEntregaRef.current.isEmpty() || firmaResponsableRef.current.isEmpty()) {
      setErrorConfirmar("Faltan una o las dos firmas.");
      return;
    }
    setConfirmando(true);
    try {
      const firmaEntregaBlob = await firmaEntregaRef.current.getBlob();
      const firmaResponsableBlob = await firmaResponsableRef.current.getBlob();

      await conManejoDeSesion(() =>
        uploadMedia(loan.id, { file: new File([firmaEntregaBlob], "firma_entrega.png", { type: "image/png" }), kind: "firma_entrega" })
      );
      await conManejoDeSesion(() =>
        uploadMedia(loan.id, { file: new File([firmaResponsableBlob], "firma_responsable.png", { type: "image/png" }), kind: "firma_responsable" })
      );
      const confirmado = await conManejoDeSesion(() => confirmLoan(loan.id));
      push({ tone: "success", title: "Préstamo confirmado", message: `Folio ${confirmado.folio}` });
      navigate(`/equipos/prestamo/${confirmado.folio}`);
    } catch (e) {
      // 409 TRANSICION_INVALIDA trae en `detail` justo lo que falta — se
      // pinta tal cual, no se adelanta un texto propio que pueda
      // contradecir la regla real del servidor.
      setErrorConfirmar(e.detail || e.message);
    } finally {
      setConfirmando(false);
    }
  }

  if (cargandoInicial) {
    return (
      <div className="space-y-4">
        <SkeletonShimmer className="h-10 w-full" />
        <SkeletonShimmer className="h-64 w-full" />
      </div>
    );
  }

  if (errorInicial) {
    return (
      <div
        className="rounded-go border px-4 py-3 font-body text-sm"
        style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
      >
        {errorInicial}
      </div>
    );
  }

  if (borradorPrevio) {
    return (
      <EmptyState
        title="Tienes un borrador sin terminar"
        message={`"${borradorPrevio.motivo || "Sin motivo"}" — puedes continuarlo o empezar de nuevo.`}
        action={
          <div className="mt-2 flex gap-2">
            <button type="button" onClick={() => reanudarBorrador(borradorPrevio)} disabled={reanudando} className="btn-go disabled:opacity-40">
              {reanudando ? "Continuando..." : "Continuar borrador"}
            </button>
            <button type="button" onClick={() => descartarBorrador(borradorPrevio)} disabled={reanudando} className="btn-go-ghost">
              Empezar de nuevo
            </button>
          </div>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* I8 lote 2 (hallazgo): con las 4 etiquetas completas ("Datos",
          "Equipos", "Fotos", "Firmas") el stepper mide ~428px — más que los
          390px del viewport móvil de referencia, y sin overflow-x-auto que
          lo contenga: la PÁGINA ENTERA quedaba con scroll horizontal
          (confirmado con scrollWidth 428 vs clientWidth 390). Debajo de
          `sm:` se esconde la etiqueta y el conector se acorta — el círculo
          numerado solo ya identifica el paso activo. */}
      <div className="flex items-center gap-1 sm:gap-2">
        {PASOS.map((label, i) => (
          <div key={label} className="flex items-center gap-1 sm:gap-2">
            <span
              className="flex h-7 w-7 items-center justify-center rounded-full font-mono text-xs font-bold"
              style={{
                background: paso === i + 1 ? "var(--go-orange)" : "var(--go-surface)",
                color: paso === i + 1 ? "#fff" : "var(--go-text-secondary)",
              }}
            >
              {i + 1}
            </span>
            <span
              className="hidden font-body text-xs sm:inline"
              style={{ color: paso === i + 1 ? "var(--go-text-primary)" : "var(--go-text-secondary)" }}
            >
              {label}
            </span>
            {i < PASOS.length - 1 && <span className="h-px w-3 sm:w-6" style={{ background: "var(--go-border)" }} />}
          </div>
        ))}
      </div>

      {paso === 1 && (
        <form onSubmit={handleSubmitPaso1} className="go-card max-w-xl space-y-4">
          <div>
            <p className="go-eyebrow mb-1.5">Responsable</p>
            <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
              {user.full_name} <span style={{ color: "var(--go-text-secondary)" }}>({user.email})</span>
            </p>
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Área</label>
            <input type="text" value={area} onChange={(e) => setArea(e.target.value)} className="go-input" required />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Empresa</label>
            <select value={empresaSel} onChange={(e) => setEmpresaSel(e.target.value)} className="go-select" required>
              <option value="">Selecciona...</option>
              {empresas.map((emp) => (
                <option key={emp.id} value={emp.razon_social}>
                  {emp.razon_social}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Motivo</label>
            <input type="text" value={motivo} onChange={(e) => setMotivo(e.target.value)} className="go-input" required />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Fecha de regreso esperada</label>
            <input
              type="date"
              value={fechaRegreso}
              onChange={(e) => setFechaRegreso(e.target.value)}
              className="go-input"
              required
            />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Notas (opcional)</label>
            <textarea value={notas} onChange={(e) => setNotas(e.target.value)} rows={2} className="go-input resize-none" />
          </div>

          {errorPaso1 && (
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
            >
              {errorPaso1}
            </div>
          )}

          <div className="flex justify-end">
            <button type="submit" disabled={enviandoPaso1} className="btn-go">
              {enviandoPaso1 ? "Creando..." : "Siguiente"}
            </button>
          </div>
        </form>
      )}

      {paso === 2 && loan && (
        <div className="grid gap-6 lg:grid-cols-2">
          <section>
            <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
              Equipos disponibles
            </h2>
            {cargandoDisponibles ? (
              <SkeletonShimmer className="h-48 w-full" />
            ) : disponibles.length === 0 ? (
              <EmptyState title="Sin equipos disponibles" />
            ) : (
              <div className="space-y-3">
                {disponibles.map((eq) => (
                  <div key={eq.id} className="go-card">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                          {eq.nombre}
                        </p>
                        <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                          {eq.categoria}
                        </p>
                      </div>
                      {agregandoId !== eq.id && (
                        <button type="button" onClick={() => abrirAgregar(eq)} className="btn-go-ghost text-xs px-3 py-1.5">
                          + Agregar
                        </button>
                      )}
                    </div>
                    {agregandoId === eq.id && (
                      <div className="mt-3 border-t pt-3" style={{ borderColor: "var(--go-border)" }}>
                        <AccesoriosPicker
                          accesoriosTipicos={eq.accesorios_tipicos}
                          value={accesoriosTmp[eq.id]}
                          onChange={(v) => setAccesoriosTmp((prev) => ({ ...prev, [eq.id]: v }))}
                        />
                        <div className="mt-3 flex justify-end gap-2">
                          <button type="button" onClick={() => setAgregandoId(null)} className="btn-go-ghost text-xs px-3 py-1.5">
                            Cancelar
                          </button>
                          <button
                            type="button"
                            onClick={() => confirmarAgregar(eq)}
                            disabled={guardandoItem}
                            className="btn-go text-xs px-3 py-1.5"
                          >
                            {guardandoItem ? "Agregando..." : "Confirmar"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
              En este préstamo ({loan.items.length})
            </h2>
            {loan.items.length === 0 ? (
              <EmptyState title="Sin equipos agregados todavía" />
            ) : (
              <ul className="space-y-2">
                {loan.items.map((it) => (
                  <li key={it.id} className="go-card flex items-center justify-between">
                    <span className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
                      {it.equipo_nombre}
                    </span>
                    <button type="button" onClick={() => handleQuitarItem(it)} className="btn-go-ghost text-xs px-2 py-1" style={{ color: "var(--go-error)" }}>
                      Quitar
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4 flex justify-end">
              <button type="button" disabled={loan.items.length === 0} onClick={() => setPaso(3)} className="btn-go disabled:opacity-40">
                Siguiente
              </button>
            </div>
          </section>
        </div>
      )}

      {paso === 3 && loan && (
        <div className="space-y-6">
          {loan.items.map((it) => (
            <div key={it.id} className="go-card">
              <p className="mb-3 font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                {it.equipo_nombre}
              </p>
              <div className="grid grid-cols-2 gap-4">
                <PhotoCapture
                  label="Foto de frente"
                  existingMediaId={it.media.foto_entrega_frente}
                  onUpload={(blob) => handleUploadFoto(it, "foto_entrega_frente", blob)}
                />
                <PhotoCapture
                  label="Foto de atrás"
                  existingMediaId={it.media.foto_entrega_atras}
                  onUpload={(blob) => handleUploadFoto(it, "foto_entrega_atras", blob)}
                />
              </div>
            </div>
          ))}
          <div className="flex justify-between">
            <button type="button" onClick={() => setPaso(2)} className="btn-go-ghost">
              Atrás
            </button>
            <button type="button" disabled={!loan.items.every(itemListo)} onClick={() => setPaso(4)} className="btn-go disabled:opacity-40">
              Siguiente
            </button>
          </div>
        </div>
      )}

      {paso === 4 && loan && (
        <div className="max-w-xl space-y-6">
          <div className="go-card">
            <p className="go-eyebrow mb-2">Firma de quien entrega</p>
            <SignaturePad ref={firmaEntregaRef} />
          </div>
          <div className="go-card">
            <p className="go-eyebrow mb-2">Firma del responsable</p>
            <SignaturePad ref={firmaResponsableRef} />
          </div>

          {errorConfirmar && (
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{ background: "rgba(229,62,62,0.08)", borderColor: "rgba(229,62,62,0.25)", color: "var(--go-error)" }}
            >
              {errorConfirmar}
            </div>
          )}

          <div className="flex justify-between">
            <button type="button" onClick={() => setPaso(3)} className="btn-go-ghost">
              Atrás
            </button>
            <button type="button" disabled={confirmando} onClick={handleConfirmar} className="btn-go">
              {confirmando ? "Confirmando..." : "Confirmar préstamo"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
