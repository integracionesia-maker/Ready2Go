# DESIGN_SYSTEM — Control de Presupuestos (Creadores de Contenido)

## Fuente visual

- Repo base: `https://github.com/joseaguilar-wq/context_desing_go.git`
- Archivo consultado: `IDENTIDAD DE MARCA/context_design.md` (no referenciado formalmente en el codigo hoy — los tokens coinciden por replicacion manual, no por vinculo real)
- Fecha de revision: 2026-07-15 (alineacion framework, primera vez que se documenta)

## Aplicacion

| Elemento | Regla aplicada | Evidencia |
|---|---|---|
| Colores | Naranja GO `#FB670B` + neutros `#262626` `#535353` `#C5C5C5` `#ECEBE0` `#FFFFFF` | `frontend/tailwind.config.js` |
| Colores de graficos | `#FB670B` `#14B8A6` `#38BDF8` `#A78BFA` `#00A36E` `#F59E0B` | `frontend/src/components/charts/apexTheme.js` |
| Tipografia | Space Grotesk (display) + Inter (body) + JetBrains Mono (mono) — **no coincide** con la tipografia oficial GO (Blauer Nue / Conthic) | `frontend/tailwind.config.js` |
| Bordes | `border-radius` 8px / 12px / 16px (`go`, `go-lg`, `go-xl`) | `frontend/tailwind.config.js` |
| Tema de graficos | Tema oscuro fijo (`goApexTheme`, `mode: "dark"`), grid y ejes con `--go-gray-2`/`--go-dark-600` | `charts/apexTheme.js` |
| Dashboard | Filtro de fechas + presets, 7 KPI cards, 4 graficos, spinner de carga, mensajes de error inline | `Dashboard.jsx` |

## Modos

Solo modo oscuro implementado (`background: var(--go-dark-900)` fijo en `App.jsx`). No hay toggle claro/oscuro como en otros proyectos del portafolio (ej. market_intelligence).

## Estados

- **Vacio:** cada grafico muestra un mensaje centrado ("Sin transacciones/datos en este periodo") cuando no hay datos
- **Error:** banda roja translucida (`rgba(229,62,62,0.08)`) con texto del mensaje de error
- **Carga:** spinner circular animado (`animate-spin`) + texto "Cargando..."
- **Exito:** KPI cards + graficos ApexCharts renderizados

---

# Direccion visual 2026-07-27 — Liquid Glass (aprobada, se implementa en WP7)

> Aplica a **toda** la app (shell nuevo + migracion de las vistas de Presupuestos + modulo Control de Equipos).
> Detalle de arquitectura de componentes: §8 de `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md`.

## Concepto

**"Vitrina de equipo"** — superficies de cristal oscuro sobre un fondo con profundidad, donde lo unico saturado de color son las fotos reales del equipo. El cristal aporta jerarquia, no decoracion. Naranja GO `#FB670B` como **unico** acento. Dark-first (regla del framework); claro via `[data-theme="light"]`.

## Tipografia (decision cerrada)

| Uso | Fuente | Notas |
|---|---|---|
| Display / UI / headings | **Blauer Nue** | Oficial de marca. Autohospedada woff2 desde `context_desing_go` |
| Cuerpo | **Conthic** | Oficial de marca |
| Cifras, folios, numeros de serie | **JetBrains Mono** | Se mantiene |

Space Grotesk e Inter salen. Fallbacks: `'Blauer Nue', 'Nunito', 'Poppins', sans-serif` y `'Conthic', 'Inter', system-ui, sans-serif`.

## Receta de cristal (fuente unica — no improvisar variantes)

```css
.glass {
  background: linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.04));
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);   /* Safari exige el prefijo */
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.25),      /* highlight superior */
    inset 0 0 0 1px rgba(255,255,255,.08),    /* rim hairline */
    0 24px 48px -12px rgba(0,0,0,.55);        /* sombra externa */
  border-radius: 20px;
}
```

Refraccion real (borde que dobla la luz): filtro SVG `feImage` + `feDisplacementMap` + `feSpecularLighting` aplicado como `backdrop-filter: url(#glass)`.

## Reglas duras (violarlas = rechazo en review)

1. **SVG como `backdrop-filter` solo funciona en Chromium.** Safari y Firefox lo ignoran. La refraccion SVG va **solo** en el shell (nav + hero), detras de `@supports`. Todo lo demas usa la receta CSS de arriba, que si es cross-browser.
2. **Prohibido cristal en filas de tabla, listas largas y contenedores con scroll.** Cada instancia reserva GPU y compositing. Maximo **3-4 superficies de cristal simultaneas** en pantalla.
3. **Todo texto sobre cristal lleva velo solido detras.** Contraste minimo 4.5:1 **medido**, no estimado. El cristal es el enemigo natural de la legibilidad.
4. **Naranja `#FB670B` es el unico acento.** Nada de segundos acentos decorativos.
5. **Animacion respeta `prefers-reduced-motion: reduce`** — sin movimiento, solo opacidad.
6. **Cero emojis** en UI, textos, reportes y PDF (regla del pool).
7. Se conservan `useMobile`, `RowActions` y `go-table-scroll-wrapper` (reglas vigentes de responsividad movil) y el selector `[data-theme="light"]` **sin `:root`** (lo necesita la plantilla off-screen del PDF de Presupuestos).

## Animacion

Libreria: `motion` (sucesor de framer-motion). Se usa para: entrada escalonada de KPIs y cards, transicion de layout compartido card → modal de ficha, indicador de nav tipo pildora magnetica, `AnimatePresence` en modales y toasts, contadores animados. Hover/focus/press en CSS puro — no montar JS donde no hace falta.

## Componentes del sistema (`frontend/src/design/`)

`GlassPanel` · `GlassNav` · `GlassModal` · `KpiTile` · `StatusDonut` · `EquipmentCard` (tilt 3D solo en puntero fino) · `SignaturePad` (Pointer Events, alta densidad, deshacer, deteccion real de vacio) · `PhotoCapture` (`capture="environment"`, compresion en cliente, frente+atras obligatorias) · `Timeline` · `CommandPalette` (Cmd+K) · `Toast` · `SkeletonShimmer` · `EmptyState` · `RoleBadge`.

## Presupuesto de rendimiento

Bundle inicial < 250 KB gz. Code splitting por ruta (`equipos`, `presupuestos`, PDF). `jspdf`/`html2canvas` siguen con `import()` dinamico. ApexCharts diferido. Miniaturas generadas en servidor (no mandar 3 MB al navegador para un thumb de 96px).

## Riesgos visuales abiertos

- Rendimiento del cristal en el Mac mini de produccion y en celular — se mide en el dispositivo real antes de cerrar WP7/WP8 (RISKS #12).
- Sin vinculo real (import) a `context_design.md`: los tokens se replican a mano y pueden desalinearse si la fuente cambia.
- Fuentes de marca dependen de que `context_desing_go` entregue los woff2 (BACKLOG T7).

## Decisiones de direccion registradas

| Fecha | Decision | Quien |
|---|---|---|
| 2026-07-27 | Liquid glass en toda la app, shell nuevo, se migran las vistas de Presupuestos | Jose |
| 2026-07-27 | Tipografia oficial de marca (Blauer Nue + Conthic + JetBrains Mono) | Jose |
| 2026-07-27 | Acoplar el modulo de Equipos a la identidad de marca (pedido explicito en la reunion con marketing) | Marketing / Jose |
