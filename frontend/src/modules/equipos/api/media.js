const backend = import.meta.env.VITE_EQUIPOS_MOCK === "1" ? import("./mock/media") : import("./real/media");

export async function uploadMedia(loanId, data) {
  return (await backend).uploadMedia(loanId, data);
}

/** Real: URL directa (?tamano=thumb la sirve el servidor). Mock: data: URI
 * ya resuelto — por eso es async en ambos lados, aunque el real no necesite
 * esperar nada de verdad. */
export async function mediaUrl(mediaId, opts) {
  return (await backend).mediaUrl(mediaId, opts);
}
