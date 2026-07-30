# Frontend — convenciones y gotchas

> Ver también [[CLAUDE]] en la raíz del repo para reglas de negocio y arquitectura general.

## Design system

Fuente de verdad: `IDENTIDAD DE MARCA/context_design.md` (repo `context_desing_go`).
Naranja GO `#FB670B` + neutros `#262626` `#535353` `#C5C5C5` `#ECEBE0` `#FFFFFF` ya aplicados en `tailwind.config.js`.
Tipografia: **decidido 27/07** — Blauer Nue (display/UI) + Conthic (cuerpo) autohospedadas + JetBrains Mono (folios, series, cifras). Space Grotesk/Inter salen en WP7. Cierra el pendiente historico del BACKLOG.
Direccion visual: **liquid glass** (dark-first, naranja como unico acento). Reglas duras y limites reales (SVG `backdrop-filter` solo Chromium; prohibido cristal en tablas y contenedores con scroll; velo solido detras de todo texto sobre cristal, contraste 4.5:1 medido) en `DESIGN_SYSTEM.md` y §8 del plan.

## Gotchas

- **Theming (`data-theme`)**: el selector en `index.css` es `[data-theme="light"]`, **sin** `:root` — a propósito, para que el reporte PDF (R8) pueda forzar tema claro en un contenedor propio (`data-theme="light"` local) sin tocar el tema real del usuario en `<html>`. No revertir a `:root[data-theme="light"]`, rompería esa plantilla off-screen.
- `jspdf` y `html2canvas` son dependencias de frontend (no dev, corren en runtime) cargadas con `import()` dinámico solo al descargar el PDF — no agregar imports estáticos de estas dos, engordarían el bundle principal.
- No agregar alias manuales de `react`/`react-dom` en `vite.config.js` — causo el bug de "Invalid hook call" (resuelto 2026-07-15). `resolve.dedupe` + `optimizeDeps.include` es suficiente con un solo `node_modules`.
- En `frontend/src/modules/presupuestos/components/charts/apexTheme.js`/`createApexOptions`, nunca asignar `stroke`/`fill`/`plotOptions`/`responsive` como `undefined` explicito — ApexCharts 5.x pisa sus defaults internos y truena el dashboard completo sin error boundary.

## Responsividad móvil

Usar `frontend/src/design/useMobile.js` (hook `useMobile(breakpoint=640)`, compartido entre Presupuestos y Equipos desde I8 lote 7) solo cuando Tailwind no alcanza (valores numéricos en JS, ej. `height` de ApexCharts) — para lo demás, clases `sm:`/`md:`. Las acciones por fila de cualquier tabla nueva deben usar `frontend/src/design/RowActions.jsx` (menú `⋯` en móvil, mismo lugar compartido) en vez de botones sueltos, para no repetir el colapso de botones que motivó la auditoría. Las tablas con posible overflow horizontal deben envolver su `overflow-x-auto` con la clase `go-table-scroll-wrapper` (+ `go-table-scroll` en el propio div) definida en `index.css`. Detalle completo: `docs/presupuestos/responsividad-movil.md`.
