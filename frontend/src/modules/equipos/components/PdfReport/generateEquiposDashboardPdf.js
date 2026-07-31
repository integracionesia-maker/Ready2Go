/**
 * Orquesta la captura de la plantilla off-screen (#equipos-pdf-report-root,
 * ver EquiposDashboardPdfTemplate) sección por sección con html2canvas y las
 * ensambla como páginas en jsPDF. Mismo patrón que
 * `presupuestos/components/PdfReport/generateDashboardPdf.js` — ambas
 * librerías se cargan con import() dinámico, solo al hacer click en
 * "Descargar PDF".
 */
export async function generateEquiposDashboardPdf({ filename }) {
  const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
    import("jspdf"),
    import("html2canvas"),
  ]);

  const root = document.getElementById("equipos-pdf-report-root");
  if (!root) {
    throw new Error("No se encontró la plantilla del reporte.");
  }
  const sections = Array.from(root.querySelectorAll(".pdf-section"));
  if (sections.length === 0) {
    throw new Error("La plantilla del reporte no tiene contenido para exportar.");
  }

  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 24;
  const usableWidth = pageWidth - margin * 2;

  let cursorY = margin;
  let atTopOfPage = true;

  for (const section of sections) {
    const canvas = await html2canvas(section, {
      scale: 1.5,
      backgroundColor: "#ffffff",
      useCORS: true,
    });
    const imgHeight = (canvas.height * usableWidth) / canvas.width;

    if (!atTopOfPage && cursorY + imgHeight > pageHeight - margin) {
      pdf.addPage();
      cursorY = margin;
      atTopOfPage = true;
    }

    // JPEG en vez de PNG: mismo motivo que en generateDashboardPdf.js — el
    // anti-aliasing de texto/gráficas hace que PNG comprima muy mal.
    pdf.addImage(canvas.toDataURL("image/jpeg", 0.92), "JPEG", margin, cursorY, usableWidth, imgHeight);
    cursorY += imgHeight + 14;
    atTopOfPage = false;
  }

  pdf.save(filename || "reporte-equipos.pdf");
}
