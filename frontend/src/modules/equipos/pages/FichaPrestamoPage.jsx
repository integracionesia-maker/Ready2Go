import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { EmptyState, GlassPanel, SkeletonShimmer, Timeline, GlassModal } from "@/design";
import { esCodigo } from "@/api";
import { fetchLoanByFolio, mediaUrl, loanResponsivaUrl } from "../api";

const ESTADO_LABEL = {
  borrador: "Borrador",
  prestado: "Prestado",
  pendiente_confirmacion: "Pend. confirmación",
  incompleto: "Incompleto",
  completado: "Completado",
  cancelado: "Cancelado",
};
const ESTADO_BADGE = {
  borrador: "go-badge-neutral",
  prestado: "go-badge-neutral",
  pendiente_confirmacion: "go-badge-warning",
  incompleto: "go-badge-error",
  completado: "go-badge-success",
  cancelado: "go-badge-neutral",
};

function Dato({ label, children }) {
  return (
    <div>
      <dt className="font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
        {label}
      </dt>
      <dd className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
        {children ?? "—"}
      </dd>
    </div>
  );
}

function Miniatura({ mediaId, label, onExpand }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelado = false;
    setError(false);
    if (mediaId) {
      mediaUrl(mediaId, { tamano: "thumb" }).then((u) => {
        if (!cancelado) setUrl(u);
      });
    }
    return () => {
      cancelado = true;
    };
  }, [mediaId]);

  // I8 lote 3 (hallazgo): sin este `onError`, un id de media que ya no
  // resuelve (archivo borrado del disco, id inventado) dejaba el ícono roto
  // nativo del navegador dentro del botón — no truena nada, pero desentona
  // del resto de la UI. Mismo placeholder "Sin foto" que ya se usa para
  // `mediaId` ausente.
  if (!mediaId || error) {
    return (
      <div
        className="flex h-24 w-24 shrink-0 items-center justify-center rounded-go border font-body text-[10px]"
        style={{ borderColor: "var(--go-border)", background: "var(--go-surface)", color: "var(--go-text-muted)" }}
      >
        {error ? "No disponible" : "Sin foto"}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onExpand(mediaId, label)}
      className="h-24 w-24 shrink-0 overflow-hidden rounded-go border"
      style={{ borderColor: "var(--go-border)", background: "var(--go-surface)" }}
      aria-label={`Ampliar ${label}`}
    >
      {url && <img src={url} alt={label} className="h-full w-full object-cover" onError={() => setError(true)} />}
    </button>
  );
}

export default function FichaPrestamoPage() {
  const { folio } = useParams();
  const [loan, setLoan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permisosNoDisponibles, setPermisosNoDisponibles] = useState(false);
  const [error, setError] = useState(null);
  const [ampliada, setAmpliada] = useState(null); // { mediaId, label }

  async function cargar() {
    setLoading(true);
    setError(null);
    setPermisosNoDisponibles(false);
    try {
      const data = await fetchLoanByFolio(folio);
      setLoan(data);
    } catch (e) {
      if (esCodigo(e, "PERMISOS_NO_DISPONIBLES")) setPermisosNoDisponibles(true);
      else setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [folio]);

  async function verResponsiva() {
    const url = await loanResponsivaUrl(loan.id);
    window.open(url, "_blank", "noopener");
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <SkeletonShimmer className="h-10 w-64" />
        <SkeletonShimmer className="h-48 w-full" />
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

  if (!loan) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-lg font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
            Ficha de préstamo{" "}
            <span className="font-mono" style={{ color: "var(--go-orange)" }}>
              {loan.folio || "Sin folio"}
            </span>
          </h1>
          {/* Tres badges ortogonales — nunca fusionados en uno solo. */}
          <div className="mt-2 flex flex-wrap gap-1.5">
            <span data-testid="badge-estado" className={`go-badge ${ESTADO_BADGE[loan.estado]}`}>
              {ESTADO_LABEL[loan.estado] || loan.estado}
            </span>
            {loan.atrasado && <span className="go-badge go-badge-error">Atrasado {loan.dias_atraso}d</span>}
            <span data-testid="badge-autorizacion" className={`go-badge ${loan.entrega_autorizada ? "go-badge-success" : "go-badge-neutral"}`}>
              {loan.entrega_autorizada ? "Entrega autorizada" : "Entrega no autorizada"}
            </span>
          </div>
        </div>
        {loan.responsiva && (
          <button type="button" onClick={verResponsiva} className="btn-go-ghost">
            Ver responsiva (PDF)
          </button>
        )}
      </div>

      <GlassPanel as="section" className="p-4 sm:p-6">
        <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Datos del préstamo
        </h2>
        <dl className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          <Dato label="Responsable">{loan.responsable?.nombre}</Dato>
          <Dato label="Área">{loan.area}</Dato>
          <Dato label="Empresa">{loan.empresa}</Dato>
          <Dato label="Motivo">{loan.motivo}</Dato>
          <Dato label="Notas de responsiva">{loan.notas_responsiva}</Dato>
          <Dato label="Entregado por">{loan.entregado_por?.nombre}</Dato>
          <Dato label="Fecha de entrega">
            <span className="font-mono">{loan.fecha_entrega || "—"}</span>
          </Dato>
          <Dato label="Regreso esperado">
            <span className="font-mono">{loan.fecha_regreso_esperada || "—"}</span>
          </Dato>
          <Dato label="Regreso real">
            <span className="font-mono">{loan.fecha_regreso_real || "—"}</span>
          </Dato>
          {/* I8 lote 2 (hallazgo, mismo patrón que R-I14): ambos son
              `Optional[PersonaRef]` en `LoanDetail` (objeto {user_id, nombre}),
              no strings — igual que `responsable`/`entregado_por` de arriba,
              que ya usan `.nombre`. Nunca se vio roto porque CE-0007 (el
              fixture usado en I3/I4) siempre los trae null; en cuanto se
              autoriza una entrega o se confirma una devolución de verdad
              contra el servidor real, React tronaba con "Objects are not
              valid as a React child" y la ficha entera se quedaba en blanco. */}
          <Dato label="Autorizada por">{loan.entrega_autorizada_por?.nombre}</Dato>
          <Dato label="Confirmada por">{loan.confirmada_por?.nombre}</Dato>
          <Dato label="Fecha de confirmación">
            <span className="font-mono">{loan.fecha_confirmacion ? loan.fecha_confirmacion.slice(0, 10) : "—"}</span>
          </Dato>
        </dl>
      </GlassPanel>

      <GlassPanel as="section" className="p-4 sm:p-6">
        <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Firmas
        </h2>
        <div className="flex gap-4">
          <div>
            <p className="mb-1.5 font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
              Quien entrega
            </p>
            <Miniatura mediaId={loan.firmas?.firma_entrega} label="Firma de quien entrega" onExpand={(id, label) => setAmpliada({ mediaId: id, label })} />
          </div>
          <div>
            <p className="mb-1.5 font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
              Responsable
            </p>
            <Miniatura mediaId={loan.firmas?.firma_responsable} label="Firma del responsable" onExpand={(id, label) => setAmpliada({ mediaId: id, label })} />
          </div>
        </div>
      </GlassPanel>

      <section className="space-y-4">
        <h2 className="font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Equipos ({loan.items.length})
        </h2>
        {loan.items.map((it) => (
          <GlassPanel key={it.id} className="space-y-3 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                {it.equipo_nombre}
              </p>
              {it.decision && (
                <span className={`go-badge ${it.decision === "ok" ? "go-badge-success" : "go-badge-error"}`}>
                  {it.decision === "ok" ? "OK" : it.decision === "danado" ? "Dañado" : "Faltante"}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
              <p>
                Accesorios:{" "}
                <span style={{ color: "var(--go-text-primary)" }}>
                  {[...(it.accesorios_seleccionados || []), it.accesorios_otros].filter(Boolean).join(", ") || "—"}
                </span>
              </p>
              <p>
                Cargador:{" "}
                <span style={{ color: "var(--go-text-primary)" }}>
                  {it.cargador_con === "responsable" ? "Con el responsable" : it.cargador_con === "empresa" ? "En resguardo" : "—"}
                </span>
              </p>
            </div>

            {it.nota_decision && (
              <p className="font-body text-sm" style={{ color: "var(--go-error)" }}>
                {it.nota_decision}
              </p>
            )}
            {it.no_devuelto && (
              <p className="font-body text-sm" style={{ color: "var(--go-warning)" }}>
                No devuelto — {it.nota_devolucion}
              </p>
            )}

            <div>
              <p className="mb-2 font-body text-xs uppercase tracking-wider" style={{ color: "var(--go-text-muted)" }}>
                Antes / después
              </p>
              <div className="flex flex-wrap gap-3">
                <Miniatura mediaId={it.media.foto_entrega_frente} label="Frente antes" onExpand={(id, label) => setAmpliada({ mediaId: id, label })} />
                <Miniatura mediaId={it.media.foto_entrega_atras} label="Atrás antes" onExpand={(id, label) => setAmpliada({ mediaId: id, label })} />
                <Miniatura mediaId={it.media.foto_dev_frente} label="Frente después" onExpand={(id, label) => setAmpliada({ mediaId: id, label })} />
                <Miniatura mediaId={it.media.foto_dev_atras} label="Atrás después" onExpand={(id, label) => setAmpliada({ mediaId: id, label })} />
              </div>
            </div>
          </GlassPanel>
        ))}
      </GlassPanel>

      <GlassPanel as="section" className="p-4 sm:p-6">
        <h2 className="mb-4 font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          Bitácora
        </h2>
        <Timeline events={loan.eventos} />
      </GlassPanel>

      {ampliada && (
        <GlassModal open onClose={() => setAmpliada(null)} title={ampliada.label}>
          <FotoCompleta mediaId={ampliada.mediaId} label={ampliada.label} />
        </GlassModal>
      )}
    </div>
  );
}

function FotoCompleta({ mediaId, label }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let cancelado = false;
    mediaUrl(mediaId).then((u) => {
      if (!cancelado) setUrl(u);
    });
    return () => {
      cancelado = true;
    };
  }, [mediaId]);

  if (error) {
    return (
      <p className="py-12 text-center font-body text-sm" style={{ color: "var(--go-text-muted)" }}>
        No se pudo cargar la imagen.
      </p>
    );
  }
  if (!url) return <SkeletonShimmer className="h-64 w-full" />;
  return (
    <img
      src={url}
      alt={label}
      className="max-h-[70vh] w-full rounded-go object-contain"
      onError={() => setError(true)}
    />
  );
}
