# Changelog — interfaz

## 2026-07-29 (I4c — Wizard de nuevo préstamo — modo 09-ejecutar-todo)

### Agregado

- `frontend/src/modules/equipos/components/SignaturePad.jsx` — firma en
  canvas (Pointer Events, `devicePixelRatio`, deshacer, detección de
  vacío real, `ref.getBlob()`/`ref.isEmpty()`).
- `frontend/src/modules/equipos/components/PhotoCapture.jsx` — foto con
  compresión cliente (900px/0.72), preview, reintento por foto.
- `frontend/src/modules/equipos/components/AccesoriosPicker.jsx` —
  accesorios típicos + libres + `cargador_con` condicional.

### Cambiado

- `frontend/src/modules/equipos/pages/NuevoPrestamoPage.jsx` — de
  placeholder (I4a) al wizard real de 4 pasos.
- `frontend/src/modules/equipos/api/mock/media.js` — `uploadMedia()`
  ahora adjunta el media al ítem/firma en la misma llamada (antes solo lo
  guardaba); preserva el `checkInjection("SESION_EXPIRADA")` que vivía en
  la función huérfana que se quitó.
- `frontend/src/modules/equipos/api/mock/state.js` — `clone()` ahora se
  exporta (antes era un helper interno solo para el seed inicial).
- `frontend/src/modules/equipos/api/mock/loans.js` — cada función
  exportada clona el préstamo/ítem justo antes de devolverlo (nunca
  dentro del helper interno `findLoan`, que sigue devolviendo la
  referencia viva a propósito para que el resto de esas mismas funciones
  la muten).

### Quitado

- `frontend/src/modules/equipos/api/mock/loans.js` — `addLoanMedia()`:
  código muerto de I3 (ningún dispatcher lo exponía), superado por el fix
  de `uploadMedia()`.

## 2026-07-29 (I4b — Inventario de Equipos — modo 09-ejecutar-todo)

### Agregado

- `frontend/src/modules/equipos/components/EquipmentCard.jsx` — tarjeta de
  rejilla con tilt 3D condicionado a `matchMedia("(hover: hover) and
  (pointer: fine)")` (no se monta en táctil).
- `frontend/src/modules/equipos/components/EquipmentFormModal.jsx` —
  alta/edición de metadata (`equipos_inventario:crear`/`:editar`).
- `frontend/src/modules/equipos/components/EquipmentAuditModal.jsx` —
  auditoría de condición (`equipos_inventario:auditar_condicion`),
  separado del formulario de edición porque el contrato los trata como
  permisos distintos.
- `frontend/src/modules/equipos/components/EquipmentFichaModal.jsx` —
  ficha con `GET /equipment/{id}` fresco y acción "Dar de baja"
  (`POST /baja`, pinta 409 `EQUIPO_OCUPADO` con el `detail` del servidor).

### Cambiado

- `frontend/src/modules/equipos/pages/InventarioPage.jsx` — de placeholder
  (I4a) a listado real: filtros en la URL, alternancia rejilla/tabla,
  paginación por `limit`/`offset`.

## 2026-07-29 (I4a — Rutas, esqueleto y vista Inicio de Equipos — modo 09-ejecutar-todo)

### Agregado

- `frontend/src/modules/equipos/EquiposLayout.jsx` — chrome del módulo
  (`EquiposSubNav` + `Outlet`).
- `frontend/src/modules/equipos/EquiposSubNav.jsx` — sub-nav horizontal
  filtrada por `usePermisos().puede(...)`, con `overflow-x-auto`
  (`go-table-scroll-wrapper`/`go-table-scroll`) para no recortar pestañas
  en móvil.
- `frontend/src/modules/equipos/pages/InicioPage.jsx` — vista real:
  `fetchEquipmentDashboard()`, `KpiTile` x4, `StatusDonut` con leyenda,
  lista "Requiere atención"; estados de loading/503/error/vacío explícitos.
- `frontend/src/modules/equipos/pages/{InventarioPage,NuevoPrestamoPage,
  ActivosPage,AprobacionesPage,HistorialPage,FichaPrestamoPage}.jsx` —
  placeholders `EmptyState` hasta su propio sub-commit (I4b..I4g).
- `App.jsx` — 7 rutas lazy bajo `/equipos` (layout route + 6 hijas),
  hermanas de `/*` (PresupuestosLayout).

### Cambiado

- `frontend/src/shell/navItems.js` — se quita `disabled: true` del tab
  "Equipos" (ya tiene rutas detrás).
- `frontend/src/api/index.js` — **bug de I3**: `BASE` y `throwApiError` se
  importaban de `./client` para uso interno pero nunca se reexportaban;
  `real/loans.js` y `real/media.js` (I3) ya los importaban de `@/api` y
  nadie lo notó hasta que I4a conectó `real/*.js` al grafo de build de
  producción (antes solo lo tocaba el harness dev). Un `export` con los
  dos nombres agregados.

## 2026-07-29 (I6 — e2e de Equipos + B-I06, 1 commit — modo 09-ejecutar-todo)

### Agregado

- `frontend/e2e/helpers/imagen.mjs` — `pngReal()` (PNG RGB truecolor real
  vía `node:zlib`, CRC32 propio, sin dependencias nuevas), `jpegReal()`
  (JPEG mínimo válido, constante base64 documentada), `fotoGrande()`
  (>3 MB con ruido — un color sólido comprimiría a unos KB sin importar el
  lienzo), `firmaPng()` (<250 KB).
- `frontend/e2e/helpers/sesiones.mjs` — `contextoDe()`: un login por
  persona, `storageState` cacheado en `e2e/.auth/<usuario>.json`.
- `frontend/e2e/helpers/sembrar-demo.mjs` — `sembrarDemo()`: N
  creadores/marcas/tickets vía API real, sufijo por corrida, extraído del
  bootstrap que antes vivía solo dentro de `pantallas.spec.js` (B-I06).
- `frontend/e2e/equipos-errores.spec.js` — los 5 códigos feos contra el
  mock de I3 (vía `DevMockHarness`), corre HOY (no fixme), 6/6.
- `frontend/e2e/equipos-flujo-completo.spec.js` — flujo completo de un
  préstamo (10 pasos), `test.fixme` con motivo y condición de despertar
  escritos en el archivo; selectores aspiracionales (I4 no existe aún).

### Cambiado

- `frontend/e2e/pantallas.spec.js` — su bootstrap ahora consume
  `sembrarDemo()` en vez de crear el creador/marca/ticket inline. Sigue en
  23/23 (era 22/22 al cierre de I1; subió a 23/23 en I2 con el segundo
  chequeo de contraste en `/dashboard`).
- `frontend/src/modules/equipos/api/real/loans.js` — comentario nuevo
  documentando la asunción de nombres de campo (R-I14).

## 2026-07-29 (I5 — permisos en la UI, 1 commit — modo 09-ejecutar-todo)

### Agregado

- `frontend/src/modules/equipos/permisos/` — `catalogo.js` (import directo
  de la copia congelada de `permisos_catalogo.json`), `fallbackPorRol.js`
  (temporal, marcado para retiro cuando WP1 aterrice — B-I14),
  `usePermisos.js` (`puede`/`permisosDe`, deny-by-default, modo diagnostico
  con `console.warn` deduplicado por clave), `RequierePermiso.jsx` (modo
  `ui` y modo `ruta`), `PermisosDemo.jsx` (demo temporal dev-only, ruta
  `/equipos/_permisos-demo`).

### Cambiado

- `frontend/src/modules/equipos/api/mock/errorInjection.js` —
  `checkGlobalInjection` ahora cubre `SIN_PERMISO` **y**
  `PERMISOS_NO_DISPONIBLES` (antes solo el primero): ambos son fallos de la
  capa de autorización que el contrato describe como generales, no
  acotados a un endpoint puntual.
- `frontend/src/App.jsx` — ruta dev-only `/equipos/_permisos-demo` agregada
  junto a la de I3.

### Sin cambio (verificado)

Los 3 e2e de Presupuestos: 25/25, sin tocar ningún archivo de
`src/modules/presupuestos/` ni `src/context/`. `dist/` de un build sin
`VITE_EQUIPOS_MOCK` sigue en 25 archivos JS, cero rastro de
`PermisosDemo`/`fallbackPorRol`/claves del catálogo.

## 2026-07-29 (I3 — mocks del contrato + ApiError, 1 commit — modo 09-ejecutar-todo)

### Agregado

- `frontend/src/api/client.js` — `class ApiError extends Error` (`status`,
  `codigo`, `detail`), `esCodigo(e, codigo)`, `throwApiError(res)` compartido.
- `frontend/src/modules/equipos/api/` — módulo completo: `index.js` (barril),
  `equipment.js`/`loans.js`/`media.js`/`empresas.js`/`permisos.js`
  (dispatchers mock-vs-real por `import()` dinámico según
  `VITE_EQUIPOS_MOCK`), `real/*.js` (clientes HTTP contra el contrato),
  `mock/*.js` (estado en memoria, máquina de estados de préstamos,
  inyección de errores por `localStorage`), `mock/fixtures/*.json` (copia
  literal de `docs/contratos/`).
- `frontend/src/modules/equipos/DevMockHarness.jsx` — panel de diagnóstico
  temporal (dev-only), ruta `/equipos/_mock-harness` en `App.jsx` detrás de
  `import.meta.env.DEV`.
- `frontend/e2e/contrato-fixtures.spec.js` — igualdad profunda entre
  `docs/contratos/` y la copia local, 6/6.

### Cambiado

- `frontend/src/api/index.js` — exporta `ApiError`/`esCodigo`/`BASE`;
  `uploadTicket`/`createGeneralExpense` (multipart) migran a
  `throwApiError` compartido en vez de duplicar el parseo del sobre de
  error.
- `frontend/src/App.jsx` — ruta dev-only agregada como hermana de `/*`
  (mayor especificidad, React Router v6 la prioriza sobre el wildcard de
  `PresupuestosLayout`).

### Sin cambio (verificado)

`message` de los errores sigue siendo exactamente `body.detail`: ningún
`catch (e) { setError(e.message) }` existente en Presupuestos se enteró del
cambio (25/25 e2e). `dist/` de un build sin `VITE_EQUIPOS_MOCK` no contiene
ninguna referencia a `EQUIPO_OCUPADO`, `estado_fisico`,
`equipos-mock-error` ni `DevMockHarness` — el módulo completo queda fuera,
no solo el mock.

## 2026-07-29 (I2 — piel de Presupuestos, 1 commit — modo 09-ejecutar-todo)

### Cambiado

- `frontend/src/modules/presupuestos/components/Modal.jsx` — superficie
  sólida manual reemplazada por `.glass` + `.veil` (glass.css de I1). API y
  nombres accesibles sin cambio: `AdminView`, `UserManagement`,
  `ValidationQueue`, `GeneralExpensesExportModal` y `DeleteConfirmModal`
  heredan el cristal sin tocarse.
- `frontend/src/modules/presupuestos/components/Dashboard.jsx` — sus 8
  `KpiCard` pasan a `KpiTile` (`@/design`); 2 (`Total Gastado`, `Total
  Disponible`) con `glass`, el resto plano. Cálculos (`spentPct`,
  `remainingPct`, etc.) sin tocar, solo cambia qué componente pinta el
  resultado.
- `frontend/src/modules/presupuestos/components/ProfilePopover.jsx`,
  `UploadTicketModal.jsx`, `GeneralExpenseModal.jsx`, `MediaViewerModal.jsx`
  — mismo patrón `.glass`+`.veil` en su overlay.
- `frontend/src/modules/presupuestos/pages/LoginPage.jsx` — el formulario
  pasa de `go-card` a `.glass`+`.veil` (única superficie de cristal de esa
  pantalla, sin conflicto de presupuesto).
- `frontend/src/design/KpiTile.jsx` — dos props nuevas, no rompen el uso
  existente (nadie más lo consumía todavía): `hint` (subtítulo, lo que
  `KpiCard` llamaba `subtitle`) y `accentColor` (borde izquierdo, lo que
  `KpiCard` llamaba `accent`). `value` ahora tolera un string no numérico
  (p.ej. `"—"` mientras el dato no ha cargado): se pinta tal cual, sin
  animar ni pasar por `format`.
- `frontend/e2e/pantallas.spec.js` — el chequeo de contraste ahora corre en
  `/` **y** `/dashboard` (antes solo `/`): las 2 KpiTile nuevas de Dashboard
  son cristal que el verificador de I1 no visitaba.

### Sin cambio (verificado, no solo asumido)

- `frontend/src/modules/presupuestos/components/KpiCard.jsx` — intacto:
  sigue siendo lo que usa `DashboardPdfTemplate.jsx` (intocable en piel).
- `apexTheme.js`, `components/PdfReport/*`, `Header.jsx`, `Sidebar.jsx`,
  `ThemeToggle.jsx`, `BrandLogo.jsx`, tablas (`TransactionTable`,
  `ValidationQueue`, `CreatorList`, `SortableHeader`, `RowActions`),
  `DateRangeFilter`, los 5 charts, `HomePage.jsx`, `ProfilePage.jsx`,
  `ForbiddenPage.jsx`, `GeneralExpensesPage.jsx`, `AdminView.jsx`,
  `UserManagement.jsx` — ya usaban los tokens de `--go-*` desde antes de I1
  y no entran en la lista de "va cristal"; verificados, no tocados.

## 2026-07-28 (I1 — shell liquid glass, 5 commits)

### Agregado

- `frontend/src/design/` — sistema de diseño: `tokens.css`, `fonts.css`,
  `glass.css`, y 13 componentes (`GlassPanel`, `GlassNav`, `GlassModal`,
  `KpiTile`, `StatusDonut`, `Timeline`, `Toast`/`ToastProvider`,
  `SkeletonShimmer`, `EmptyState`, `RoleBadge`, `CommandPalette`/su provider,
  `GlassFilterDefs`, `motion.js`) + `index.js` (barril).
- `frontend/src/shell/` — `AppShell.jsx` (chrome genérico: `GlassNav` de
  módulos + `<Outlet />`), `ModuleTabs.jsx`, `navItems.js`.
- `frontend/src/modules/presupuestos/PresupuestosLayout.jsx` — el
  componente local `AppShell` de `App.jsx:48` movido tal cual, renombrado
  (B-I04).
- `frontend/public/theme-boot.js` — script de tema, antes inline en
  `index.html` (I7).
- `frontend/e2e/helpers/pantallas.mjs` y `contraste.mjs`,
  `frontend/e2e/pantallas.spec.js` — verificador de pantallas formal (B-I05):
  10 rutas x 2 anchos, conteo de `.apexcharts-canvas`, contraste WCAG medido.
- `frontend/.gitignore` (no existía) — `e2e/.auth/` y `e2e/.screenshots/`.
- `@fontsource/jetbrains-mono`, `@fontsource/nunito`, `@fontsource/inter`
  (solo subset `latin`) y `motion` como dependencias.
- `manualChunks` en `vite.config.js`: `react-vendor`, `apex`
  (`apexcharts`+`react-apexcharts` juntos), `motion`.
- `React.lazy` + `Suspense` por ruta en `PresupuestosLayout.jsx` (9 páginas)
  y `App.jsx` (`LoginPage`).

### Cambiado

- `frontend/index.css` — capas movidas a `src/design/` (`@import` arriba de
  `@tailwind base`); se quitó el `@import` remoto de Google Fonts.
- `frontend/index.html` — `<title>` a "Ready2Go — Grupo Ortiz"; script de
  tema pasa a `<script src="/theme-boot.js">` (clásico, bloqueante); se quitó
  `class="bg-gray-50 text-gray-900"` de `<body>` (dead code de Tailwind que
  pisaba los tokens de tema — ver R-I12 en `docs/riesgos/interfaz.md`).
  `<body class="antialiased">`.
- `frontend/tailwind.config.js` — `fontFamily.display/body/mono` lee
  `var(--go-font-*)` en vez de tener "Space Grotesk"/"Inter" hardcodeados.
- `frontend/src/App.jsx` — solo enrutado: `/login` (lazy) + `ProtectedRoute`
  (layout route) + `AppShell` (layout route) + `PresupuestosLayout` en `/*`.
- `frontend/src/main.jsx` — `MotionConfig reducedMotion="user"` (outermost) +
  `ToastProvider` (envolviendo `App`), sin tocar el orden existente de
  `BrowserRouter`/`ThemeProvider`/`AuthProvider`.
- `frontend/src/modules/presupuestos/components/ProtectedRoute.jsx` —
  fallback aditivo `children ?? <Outlet />` (B-I04), cero cambio en sus ~6
  usos existentes con `children`.
- `frontend/src/modules/presupuestos/components/Sidebar.jsx` —
  `aria-label="Navegacion de Presupuestos"` en su `<nav>` (B-I01).
- `frontend/src/modules/presupuestos/components/AdminView.jsx` —
  `aria-label="Secciones de Administracion"` en su `<nav>` (antes sin
  etiqueta, B-I01).
- `frontend/e2e/auth.spec.js`, `gastos-generales.spec.js`,
  `presupuesto-flujo-completo.spec.js` — las 9 aserciones
  `page.locator("nav")` pasan a
  `page.getByRole("navigation", { name: "Navegacion de Presupuestos" })`
  (B-I01).
- `frontend/vite.config.js` — agrega `build.rollupOptions.output.manualChunks`.

### Quitado

- `@import url("https://fonts.googleapis.com/...")` de `index.css` (I7).
- Script inline de tema de `index.html` (movido a `public/theme-boot.js`).
- `class="bg-gray-50 text-gray-900"` de `<body>` en `index.html` (dead code,
  sin ninguna referencia en `src/` — confirmado por grep).

### Sin cambio (verificado)

Los 3 e2e de Presupuestos (auth/presupuesto-flujo-completo/gastos-generales)
siguen 25/25 tras los 5 commits. `apexTheme.js` y las plantillas de
`components/PdfReport/` no se tocaron (fuera de alcance de I1).

## 2026-07-28 (I0)

### Agregado

- `frontend/src/modules/presupuestos/` — raiz del modulo, con `components/`,
  `pages/`, `hooks/` y `utils/` adentro.
- `frontend/src/api/client.js` — transporte HTTP compartido: `request`,
  `fetchWithAuthRetry`, `refreshSession`, `isNetworkError`,
  `setAuthFailureHandler`.
- `frontend/jsconfig.json` — alias `@/*` -> `./src/*` para el editor.
- Alias `@` en `resolve.alias` de `frontend/vite.config.js`, con la razon por la
  que ahi NUNCA van `react` ni `react-dom` escrita en el propio archivo.
- `docs/avances/interfaz.md`, `docs/backlog_interfaz.md`,
  `docs/changelog/interfaz.md`, `docs/riesgos/interfaz.md`.

### Cambiado

- 37 imports en 25 archivos del modulo pasan al alias `@`: solo los que cruzan la
  frontera (`api/`, `context/`, `assets/`). Los internos (`../utils/`,
  `../hooks/`) no se tocaron porque siguen resolviendo.
- `frontend/src/App.jsx` — los 15 imports de vistas apuntan a
  `./modules/presupuestos/`.
- `frontend/src/api/index.js` — pasa a ser barril: conserva las 38 funciones por
  dominio e importa el transporte de `./client`. Re-exporta `isNetworkError`,
  `setAuthFailureHandler`, `request` y `fetchWithAuthRetry`.
- `frontend/src/assets/logos/README.md` — la ruta de `BrandLogo.jsx` que el
  movimiento invalido.
- `frontend/e2e/gastos-generales.spec.js` — selecciona la marca obligatoria en el
  modal de nuevo gasto general, en los dos tests que lo abren.

### Quitado

- `refreshSession` deja de ser alcanzable desde `@/api`. Sigue exportado de
  `./client` porque el transporte lo usa; no se re-exporta en el barril a
  proposito, es interno del reintento por 401.
- Dejan de existir como raices `frontend/src/components/`, `pages/`, `hooks/` y
  `utils/`. Ningun archivo se borro: los 41 son renames.

### Sin cambio

Bundle identico byte por byte y las 20 capturas (10 rutas x 2 anchos) identicas
por SHA256. No se toco `index.css`, `index.html`, `package.json`,
`tailwind.config.js`, `apexTheme.js` ni `backend/`.
