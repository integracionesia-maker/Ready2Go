# Backlog — interfaz

## Tareas de la asignacion

- [x] **I0 — Costura.** `d602e00`. Build verde, bundle identico, 25/25 e2e, 20/20
      capturas identicas.
- [x] **I1 — Shell liquid glass (WP7-A), absorbiendo I7.** 5 commits:
      `210e735` (tokens/fuentes/arranque limpio), `0055206` (13 componentes de
      `src/design/`), `a13ebe3` (shell, renombre `AppShell`→`PresupuestosLayout`,
      etiquetas de nav, 9 aserciones, 25/25 e2e), `c14a368` (particion de bundle,
      B-I03 resuelto), `47020d8` (verificador de pantallas formal, B-I05
      resuelto, encontro y arreglo R-I12). `src/design/`, `src/shell/`,
      `public/theme-boot.js`, particion de `index.css`, `MotionConfig` +
      `ToastProvider` en `main.jsx`, `manualChunks`. I7 fue absorbido en el
      commit 1. Cerrado con capturas reales en 1280x800 y 390x844 (20, via
      `e2e/pantallas.spec.js`) y el contraste **medido** (>= 4.5:1, 22/22 en el
      verificador).
- [x] **I2 — Migracion visual de Presupuestos (WP7-B).** Commit de este issue
      (ver `git log` — modo 09-ejecutar-todo, 1 commit por issue). Solo piel:
      `Modal.jsx` se apoya en `.glass`+`.veil` (API intacta, cubre 5
      consumidores gratis); `Dashboard.jsx` cambia sus 8 `KpiCard` por
      `KpiTile` (2 con `glass`, el resto plano — presupuesto de 3-4
      superficies de cristal ya casi lleno con el nav del shell);
      `ProfilePopover`, `UploadTicketModal`, `GeneralExpenseModal`,
      `MediaViewerModal` y `LoginPage` con la misma receta. `KpiCard.jsx`
      **sin tocar** (lo sigue usando `DashboardPdfTemplate.jsx`, intocable en
      piel — html2canvas no rasteriza `backdrop-filter`). Diff verificado
      vacio contra el grep de `fetch/request/@api/useEffect/budget_cycle/
      is_deleted/status===/role===/ADMIN_ROLES`. `e2e/pantallas.spec.js`
      ganó un segundo chequeo de contraste en `/dashboard` (las 2 KpiTile
      nuevas no estaban cubiertas por el de `/`). 25/25 + 23/23.
- [ ] **I3 — Mocks propios.** `src/modules/equipos/api/mock/` con
      `VITE_EQUIPOS_MOCK=1`, copia literal de `docs/contratos/fixtures/*.json`.
      Los cinco codigos feos: 409, 403, 503, 413 y 401 a mitad del wizard.
- [ ] **I4 — Modulo Equipos (WP8).** 7 vistas. `SignaturePad`, `PhotoCapture`,
      `AccesoriosPicker`, `EquipmentCard` en `modules/equipos/components/`; solo
      `Timeline` es generico y vive en `src/design/`.
- [ ] **I5 — Permisos en la UI.** `usePermisos` y `RequierePermiso` propios del
      modulo, leyendo `user.permisos`. Con modo diagnostico en desarrollo que
      loguee toda clave de permiso desconocida.
- [ ] **I6 — e2e del flujo completo de equipos.** Escrito contra el contrato,
      en `test.fixme` hasta que aterrice el servidor. Helpers de imagen con
      PNG/JPEG reales, no el truco de `%PDF-1.4`.

## Decisiones ya tomadas, para no re-litigarlas

- [x] **B-I01 — Nav y strict mode.** `a13ebe3`. Contrato por etiqueta, no por
  componente: el `nav` que lista secciones de Presupuestos lleva siempre
  `aria-label="Navegacion de Presupuestos"` (hoy en `Sidebar`). El nav superior
  nuevo (`GlassNav` de modulos) lleva `aria-label="Navegacion principal"`, y el
  de `AdminView.jsx:296` (antes sin etiqueta) `aria-label="Secciones de
  Administracion"`. Las 9 aserciones `page.locator("nav")` (`auth.spec.js`
  99-101 y 158-160, `gastos-generales.spec.js` 169 y 181,
  `presupuesto-flujo-completo.spec.js` 191) pasaron a
  `getByRole("navigation", { name: ... })` en el mismo commit que monto
  `AppShell`. Los 3 `<nav>` coexisten en `/administracion` sin ambiguedad,
  confirmado en disco.
- [x] **B-I02 — Fuentes.** `210e735`. `@fontsource` autohospedado (JetBrains
  Mono, Nunito, Inter — solo subset `latin`, cubre el español acentuado sin
  arrastrar cyrillic/greek/vietnamese de balde). Ver R-I06: sigue "con
  respaldo", no con tipografia de marca — eso llega cuando `context_desing_go`
  entregue los woff2, y es cambiar solo `src/design/fonts.css`.

## Pendientes tecnicos

- [x] **B-I03 — Bajar el bundle inicial de 261.76 kB gz a menos de 250.**
      `c14a368`. Resuelto con margen real: `React.lazy` por ruta +
      `manualChunks` (react-vendor/apex/motion) dejan `dist/assets/index-*.js`
      en 14.87 kB gz. El payload real que carga /login (medido con Playwright
      contra `vite preview`, no solo leido del output de build) es
      index+react-vendor+motion+LoginPage ≈ 111.4 kB gz de JS + 6.89 kB gz de
      CSS ≈ 118.3 kB gz — bajo el techo de 250 con margen. `apex` (174.54 kB
      gz), `html2canvas` y `jspdf` quedan fuera del grafo eager, solo se piden
      al entrar a `/dashboard` o exportar un PDF. `motion` sigue eager
      (42.51 kB gz, `ToastProvider` envuelve toda la app) — candidato a
      `LazyMotion`+`domAnimation` si el margen se aprieta en I4, no hace falta
      forzarlo ahora.
- [x] **B-I04 — Resolver la colision `AppShell`** entre el componente local de
      `App.jsx:48` y `src/shell/AppShell.jsx`. `a13ebe3`. El local se renombro a
      `PresupuestosLayout` (tal cual, sin cambiar su logica) en
      `src/modules/presupuestos/`; `src/shell/AppShell.jsx` es el chrome
      generico (`GlassNav` de modulos + `<Outlet />`). `ProtectedRoute` gano un
      fallback aditivo `children ?? <Outlet />` para servir de layout route sin
      romper sus ~6 usos existentes.
- [x] **B-I05 — Formalizar el verificador de capturas.** `47020d8`. Sale del
      scratchpad: `frontend/e2e/helpers/pantallas.mjs` (10 rutas x 2 anchos,
      mide texto de `#root`, alto real y `.apexcharts-canvas`) +
      `frontend/e2e/helpers/contraste.mjs` (formula WCAG) +
      `frontend/e2e/pantallas.spec.js` (bootstrap con datos reales para evitar
      R-I04, un solo login con `storageState`, contraste medido del velo de
      cada superficie `.glass` del shell). 22/22. Encontro y arreglo un riesgo
      real en el camino: R-I12.
- [ ] **B-I06 — Semilla de demo usable para capturas.** Hoy hay que aprobar los
      355 tickets por la API despues de sembrar (R-I04). Deberia existir un paso
      documentado, o pedir que el seed del backend deje datos que si pinten.
      Sigue sin existir el helper generico `e2e/helpers/sembrar-demo.mjs`
      pedido en la asignacion — lo que hay hoy es un bootstrap ad-hoc *dentro*
      de `e2e/pantallas.spec.js` (crea 1 creador + 1 marca + 1 ticket via API
      real, el ticket de superadmin se auto-aprueba) que sirve de precedente
      pero no es reusable por otros specs todavia.
- [ ] **B-I07 — Promover `useMobile` a un lugar compartido** cuando el modulo de
      equipos lo necesite. Quedo dentro de `modules/presupuestos/hooks/` por I0;
      es infra generica, no del modulo. Al moverlo, corregir tambien la ruta que
      `CLAUDE.md:46` documenta (R-I03).

## Pedidos a otros carriles

- [ ] **B-I08 — Corregir `CLAUDE.md:39`**: dice que `general_expenses` va sin
      `brand_id` y `models.py` dice `nullable=False`. Ver R-I02. Esa
      contradiccion ya costo un e2e rojo.
- [ ] **B-I09 — Autorizar la llave SSH.** Ya no bloquea: el push por HTTPS
      funciona y quedo verificado el 28/07. Queda pendiente porque el comando de
      clonado de la asignacion usa `git@github.com:...` y falla de entrada.
      Ver R-I08.
- [ ] **B-I10 — Los woff2 de Blauer Nue y Conthic** desde `context_desing_go`.
      No bloqueo I1 (R-I06): cerro con la pila de respaldo autohospedada
      (`210e735`) y el nombre de marca primero en `src/design/fonts.css`.
      Cuando lleguen los woff2, es cambiar ese unico archivo.
- [ ] **B-I11 — Preguntar cual manda**: `fixtures/equipos.json` trae
      `estado_fisico`, `comentario_auditoria` y `fecha_auditoria`, ausentes en
      `API_EQUIPOS_v1.md` §2. Ver R-I10. Mientras no haya respuesta, en I3/I4
      esos tres campos se pintan solo si vienen, nunca se asumen.
- [ ] **B-I12 — Seguir la confirmacion de marketing** sobre la razon social
      emisora de la responsiva (`fixtures/empresas.json` trae
      "Quantum de Occidente" marcada `PENDIENTE`). Ver R-I11. No bloquea mi
      carril; bloquea el PDF final (WP5, no es mio). Mencionar una vez por
      reporte mientras siga abierto.
