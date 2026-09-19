import { useState } from "react";
import { ticketFileUrl, ticketMediaUrl } from "@/api";
import { MediaViewer } from "@/design";

/**
 * Visor de comprobantes de ticket (R11), con navegación cuando el ticket
 * tiene más de una foto. Lo usan Transacciones y Validación.
 *
 * Toda la mecánica (encuadre fijo, zoom, arrastre, pellizco, descarga) vive en
 * `@/design/MediaViewer`, compartido con Gastos Generales y con las fotos de
 * Equipos. Aquí solo queda resolver la URL autenticada de cada foto — nunca
 * una URL pública: las cookies de sesión viajan solas por ser del mismo origen.
 *
 * Fallback a `ticket.file_name`/`ticketFileUrl` (columnas legacy) si
 * `ticket.media` viniera vacío — no debería pasar tras el backfill, pero cubre
 * el hueco entre desplegar este cambio y correr la migración.
 */
export default function MediaViewerModal({ ticket, onClose }) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!ticket) return null;

  const media =
    ticket.media && ticket.media.length > 0
      ? ticket.media
      : [{ id: null, file_name: ticket.file_name, mime_type: ticket.mime_type }];

  const actual = media[Math.min(activeIndex, media.length - 1)];
  const url = actual.id != null ? ticketMediaUrl(actual.id) : ticketFileUrl(ticket.id);

  return (
    <MediaViewer
      url={url}
      fileName={actual.file_name}
      mimeType={actual.mime_type || ""}
      title={`Comprobante — ${actual.file_name}`}
      onClose={onClose}
      index={media.length > 1 ? activeIndex + 1 : undefined}
      total={media.length > 1 ? media.length : undefined}
      onPrev={activeIndex > 0 ? () => setActiveIndex((i) => i - 1) : undefined}
      onNext={activeIndex < media.length - 1 ? () => setActiveIndex((i) => i + 1) : undefined}
    />
  );
}
