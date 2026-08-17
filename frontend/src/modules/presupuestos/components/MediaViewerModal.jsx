import { ticketFileUrl } from "@/api";
import { MediaViewer } from "@/design";

/**
 * Visor de comprobantes de ticket (R11). Lo usan Transacciones y Validación.
 *
 * Toda la mecánica (encuadre fijo, zoom, arrastre, pellizco, descarga) vive en
 * `@/design/MediaViewer`, compartido con Gastos Generales y con las fotos de
 * Equipos. Aquí solo queda resolver la URL autenticada del ticket — nunca una
 * URL pública: las cookies de sesión viajan solas por ser del mismo origen.
 */
export default function MediaViewerModal({ ticket, onClose }) {
  if (!ticket) return null;

  return (
    <MediaViewer
      url={ticketFileUrl(ticket.id)}
      fileName={ticket.file_name}
      mimeType={ticket.mime_type || ""}
      title={`Comprobante — ${ticket.file_name}`}
      onClose={onClose}
    />
  );
}
