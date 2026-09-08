// Paths SVG (viewBox 24x24, trazo) compartidos por RowActions y botones
// standalone — mismo formato que los íconos de navegación en Sidebar.jsx /
// EquiposSidebar.jsx. Centralizados acá para no repetir el mismo `d` en
// cada tabla que usa la misma acción (ver, editar, eliminar, ...).
export const ICONS = {
  ver: "M15 12a3 3 0 11-6 0 3 3 0 016 0zm-3 7a9 9 0 100-18 9 9 0 000 18z",
  editar: "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z",
  eliminar: "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
  auditar: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4",
  devolucion: "M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3",
  responsiva: "M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z",
  aprobar: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  rechazar: "M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  resetear: "M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z",
  toggle: "M5.636 5.636a9 9 0 1012.728 0M12 3v9",
  historico: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  exportar: "M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2",
  nuevo: "M12 4v16m8-8H4",
  info: "M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z",
  // Cabeceras de sección del Dashboard de Presupuestos (Dashboard.jsx):
  // agrupan las gráficas por lo que muestran (creadores, actividad, gastos
  // generales/operativos) en vez de amontonarlas todas juntas.
  personas: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z",
  actividad: "M13 10V3L4 14h7v7l9-11h-7z",
  recibo: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-9c-1.11 0-2.08.402-2.599 1M12 16c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
};
