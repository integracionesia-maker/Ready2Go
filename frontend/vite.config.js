import { execSync } from "node:child_process";
import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

import pkg from "./package.json";

// Permite apuntar a un backend en otro puerto (usado por la suite E2E de Playwright)
// sin tocar el valor por defecto de desarrollo (127.0.0.1:8000).
const backendPort = process.env.VITE_BACKEND_PORT || "8000";

// Hash del commit desplegado. Lo consume el panel "acerca de" (design/AboutPanel.jsx)
// y sirve para soporte: la versión de package.json solo cambia en release, así que
// entre releases el hash es lo único que distingue un build de otro.
// Con fallback: un build desde un tarball sin `.git` (o sin git instalado) no debe
// romperse — degrada a "sin-git" en vez de tumbar el `vite build`.
function commitHash() {
  try {
    return execSync("git rev-parse --short HEAD", { stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim();
  } catch {
    return "sin-git";
  }
}

// Identidad del build, visible en la UI (menú de perfil y panel "acerca de").
// Va por `process.env.VITE_*` y NO por `define`: el plugin `vite:define` de Vite
// sale temprano cuando el consumidor es el cliente y no es build, así que en el
// dev server no sustituye nada y el identificador llega crudo al navegador
// (ReferenceError al renderizar). Vite copia a `import.meta.env` toda variable
// de process.env con prefijo VITE_, y eso sí funciona en dev y en build.
// Se leen desde `src/design/buildInfo.js`.
// Bumpear `version` en package.json al hacer release.
process.env.VITE_APP_VERSION = pkg.version;
process.env.VITE_COMMIT_HASH = commitHash();
// Fecha en formato local corto (es-MX): se muestra a personas, no se parsea.
process.env.VITE_BUILD_DATE = new Date().toLocaleDateString("es-MX", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

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
  build: {
    rollupOptions: {
      output: {
        // B-I03: react-vendor separado del app code (mejor cacheo, cambia
        // poco); apex agrupa apexcharts + react-apexcharts EN EL MISMO
        // chunk (separarlos rompe el orden de inicialización, ver
        // 01-I1-shell.md commit 4); motion aparte para medir su peso real.
        // Esto reorganiza en qué archivo cae cada dependencia — no decide
        // CUÁNDO se descarga: eso lo sigue marcando el grafo real de
        // imports dinámicos (React.lazy por ruta).
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/node_modules[\\/](react-router|react-dom|react|scheduler)[\\/]/.test(id)) {
            return "react-vendor";
          }
          if (/node_modules[\\/](apexcharts|react-apexcharts)[\\/]/.test(id)) {
            return "apex";
          }
          if (/node_modules[\\/](motion|framer-motion)[\\/]/.test(id)) {
            return "motion";
          }
          return undefined;
        },
      },
    },
  },
});
