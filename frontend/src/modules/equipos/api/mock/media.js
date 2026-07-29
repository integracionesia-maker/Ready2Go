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
 * foto_dev_atras | firma_entrega | firma_responsable. */
export async function uploadMedia(loanId, { file, kind }) {
  checkGlobalInjection();
  checkInjection("MEDIA_MUY_GRANDE");

  const esFirma = kind === "firma_entrega" || kind === "firma_responsable";
  const limite = esFirma ? MAX_FIRMA_BYTES : MAX_FOTO_BYTES;
  if (file.size > limite) throwFixtureError("MEDIA_MUY_GRANDE");

  const id = ++state.mediaIdCounter;
  const dataUrl = await fileToDataUrl(file);
  state.media.set(id, { kind, loanId, dataUrl, sha256: fakeSha256(file.size) });

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
