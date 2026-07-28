import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Permite apuntar a un backend en otro puerto (usado por la suite E2E de Playwright)
// sin tocar el valor por defecto de desarrollo (127.0.0.1:8000).
const backendPort = process.env.VITE_BACKEND_PORT || "8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Alias de rutas del proyecto. NUNCA agregar aquí `react` ni `react-dom`:
    // ese alias manual causó el bug de "Invalid hook call" (resuelto 2026-07-15).
    // Con un solo node_modules, `dedupe` + `optimizeDeps.include` es suficiente.
    // El mismo mapeo está declarado en `jsconfig.json` para el editor.
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
    dedupe: ["react", "react-dom"],
  },
  optimizeDeps: {
    include: ["react", "react-dom", "react-apexcharts", "apexcharts"],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
});
