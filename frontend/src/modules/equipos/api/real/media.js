import { BASE, fetchWithAuthRetry, throwApiError } from "@/api";

/** `kind` ∈ foto_entrega_frente | foto_entrega_atras | foto_dev_frente |
 * foto_dev_atras | firma_entrega | firma_responsable.
 *
 * Multipart: NUNCA fijar `Content-Type` a mano — el navegador tiene que
 * poner el `boundary` él mismo. Por eso esto usa `fetchWithAuthRetry`
 * directo (que no fuerza ningún header), no `request()` (que sí fuerza
 * `application/json`, ver client.js).
 *
 * Firmas (docs/equipos/firma-guardada.md): con `usarFirmaGuardada` NO se manda
 * `file` — el servidor copia la firma del perfil del usuario logueado.
 * `guardarComoPredeterminada` (con `file`) guarda lo dibujado en el perfil.
 */
export async function uploadMedia(loanId, { file, kind, loanItemId, usarFirmaGuardada, guardarComoPredeterminada }) {
  const formData = new FormData();
  if (usarFirmaGuardada) {
    formData.append("usar_firma_guardada", "true");
  } else {
    formData.append("file", file);
    if (guardarComoPredeterminada) formData.append("guardar_como_predeterminada", "true");
  }
  formData.append("kind", kind);
  if (loanItemId != null) formData.append("loan_item_id", loanItemId);

  const res = await fetchWithAuthRetry(`/loans/${loanId}/media`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) await throwApiError(res);
  return res.json();
}

/** `?tamano=thumb` pide la miniatura de 96px generada en servidor — nunca
 * bajar la foto completa (hasta 3 MB) para pintar un thumb de listado. */
export function mediaUrl(mediaId, { tamano } = {}) {
  const qs = tamano ? `?tamano=${tamano}` : "";
  return `${BASE}/media/${mediaId}${qs}`;
}
