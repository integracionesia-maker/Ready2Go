import { state } from "./state";
import { checkGlobalInjection, checkInjection } from "./errorInjection";
import { throwFixtureError, throwNotFound } from "./mockErrors";

const MAX_FOTO_BYTES = 3 * 1024 * 1024;
const MAX_FIRMA_BYTES = 250 * 1024;

function fakeSha256(size) {
  // No es un hash real — alcanza para el mock; nunca se usa para verificar
  // integridad de verdad (eso lo hace el servidor).
  return `mock-${size}-${Date.now().toString(16)}`;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/** `kind` ∈ foto_entrega_frente | foto_entrega_atras | foto_dev_frente |
 * foto_dev_atras | firma_entrega | firma_responsable.
 *
 * `real/media.js` sube y adjunta en una sola llamada multipart
 * (`POST /loans/{id}/media` con `loan_item_id` en el form-data) — el mock
 * tiene que replicar exactamente ese contrato atómico, no solo guardar el
 * archivo. Attach inline aquí (no una función `addLoanMedia` aparte que
 * el wizard tendría que recordar llamar después): así el mock no puede
 * quedar en el estado a medias que dejaría subir la foto sin adjuntarla.
 */
export async function uploadMedia(loanId, { file, kind, loanItemId } = {}) {
  checkGlobalInjection();
  // 401 a mitad del wizard: subir fotos/firmas (pasos 3-4) es exactamente
  // donde el plan pide simular la sesión caída sin perder lo ya subido.
  checkInjection("SESION_EXPIRADA");
  checkInjection("MEDIA_MUY_GRANDE");

  const esFirma = kind === "firma_entrega" || kind === "firma_responsable";
  const limite = esFirma ? MAX_FIRMA_BYTES : MAX_FOTO_BYTES;
  if (file.size > limite) throwFixtureError("MEDIA_MUY_GRANDE");

  const loan = state.loans.find((l) => l.id === loanId);
  if (!loan) throwNotFound(`Préstamo ${loanId} no encontrado.`);

  let item = null;
  if (!esFirma) {
    item = loan.items.find((it) => it.id === loanItemId);
    if (!item) throwNotFound("Item de préstamo no encontrado.");
  }

  // Completar la firma que faltó al confirmar está permitido en cualquier
  // estado no terminal; RE-subir una que ya existe no — es evidencia (mismo
  // candado que el servidor real, ver routers/loans.py::subir_media).
  if (esFirma && loan.estado !== "borrador" && loan.firmas[kind]) {
    throwFixtureError("TRANSICION_INVALIDA");
  }

  const id = ++state.mediaIdCounter;
  const dataUrl = await fileToDataUrl(file);
  state.media.set(id, { kind, loanId, dataUrl, sha256: fakeSha256(file.size) });

  if (esFirma) {
    loan.firmas[kind] = id;
    if (kind === "firma_entrega") loan.firma_entrega_pendiente = false;
    if (kind === "firma_responsable") loan.firma_responsable_pendiente = false;
    if (loan.estado !== "borrador" && loan.firmas.firma_entrega && loan.firmas.firma_responsable) {
      if (loan.responsiva) loan.responsiva = { ...loan.responsiva, version: loan.responsiva.version + 1 };
      loan.eventos.push({
        id: Date.now(),
        tipo: "firma_completada",
        actor: loan.responsable?.nombre || "—",
        detalle: "Firma pendiente completada. Carta responsiva actualizada.",
        created_at: new Date().toISOString(),
      });
    }
  } else {
    item.media[kind] = id;
  }

  return { id, kind, sha256: state.media.get(id).sha256 };
}

/** El mock devuelve el data: URI directo — ya sirve para pintar un thumb en
 * desarrollo sin necesitar un servidor de miniaturas real. Mismo nombre que
 * real/media.js (`mediaUrl`) aunque ahí sea síncrono y aquí necesite
 * resolver el Map en memoria: el consumidor no debe saber cuál transporte
 * tiene detrás. */
export async function mediaUrl(mediaId) {
  checkGlobalInjection();
  const entry = state.media.get(mediaId);
  if (!entry) throwNotFound(`Media ${mediaId} no encontrada.`);
  return entry.dataUrl;
}
