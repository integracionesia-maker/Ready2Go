# Changelog — interfaz

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
