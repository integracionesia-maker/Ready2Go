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
- [x] **I3 — Mocks propios.** Commit de este issue (modo 09-ejecutar-todo, 1
      commit por issue). `ApiError`/`esCodigo` en `client.js` (R-I09
      resuelto), copia literal de los 6 archivos de `docs/contratos/` a
      `src/modules/equipos/api/mock/fixtures/` (`contrato-fixtures.spec.js`
      nuevo, 6/6, compara byte a byte). `src/modules/equipos/api/` con
      `equipment.js`/`loans.js`/`media.js`/`empresas.js`/`permisos.js` +
      `index.js`, cada uno decidiendo mock-vs-real por `import()` dinamico
      segun `VITE_EQUIPOS_MOCK` — confirmado en `dist/`: **cero** rastro del
      mock, sus fixtures o `DevMockHarness` en un build sin la variable
      (`grep` vacio en todo `dist/`, no solo "fuera del chunk principal").
      Maquina de estados de prestamos completa en el mock (borrador →
      prestado → pendiente_confirmacion → completado/incompleto, con el
      indice unico "un equipo no en dos prestamos abiertos" replicado en
      memoria). Los cinco codigos feos + panel de diagnostico temporal
      (`DevMockHarness.jsx`, dev-only, ruta `/equipos/_mock-harness`) con
      capturas reales mostrando cada codigo — sustituido cuando I4 tenga
      vistas propias. Riesgo nuevo: R-I13 (body de `/devolucion` sin ejemplo
      en el contrato, se adivino la forma en `real/loans.js`).
- [x] **I4 — Modulo Equipos (WP8).** 7 vistas, 7 sub-commits (I4a..I4g),
      los 7 cerrados. `SignaturePad`, `PhotoCapture`, `AccesoriosPicker`,
      `EquipmentCard` en `modules/equipos/components/`; solo `Timeline`
      es generico y vive en `src/design/` (ya estaba listo desde I1).
  - [x] **I4a — Rutas, esqueleto y vista Inicio.** `App.jsx`: 7 rutas lazy
        bajo `/equipos` (`EquiposLayout` + `EquiposSubNav` filtrada por
        `usePermisos`). `InicioPage.jsx` real (KPIs + `StatusDonut` +
        "Requiere atención"); las otras 6 son placeholder `EmptyState`
        hasta su propio sub-commit. Dos bugs reales encontrados y
        arreglados en el mismo commit: `src/api/index.js` (I3) nunca
        reexportaba `BASE`/`throwApiError` que `real/loans.js` y
        `real/media.js` ya importaban de `@/api` — build rojo de fabrica,
        invisible hasta que I4a conecto `real/*.js` al grafo de produccion;
        y `GlassNav` (pensado para 2 pastillas) recortaba "Inicio" fuera
        del viewport en 390px con 6 pestañas — arreglado con el mismo
        patron `go-table-scroll-wrapper`/`go-table-scroll` de las tablas.
        Bundle: index-*.js 14.88 → 16.31 kB gz, payload de /login
        ~120.87 → 122.36 kB gz (techo 250). Los 4 e2e de Presupuestos:
        48/48 (auth 7/7, flujo 9/9, gastos-generales 9/9, pantallas 23/23).
  - [x] **I4b — Inventario.** Filtros en la URL (`useSearchParams`,
        debounce de 300ms solo en el texto libre); opciones de categoría
        aprendidas del propio inventario (`limit=200`), sin enum inventado.
        `EquipmentCard` con tilt 3D que ni monta listeners en táctil
        (`matchMedia("(hover: hover) and (pointer: fine)")` una sola vez).
        Alternativa de tabla sin cristal + `RowActions`. Dos modales
        separados por permiso real del contrato: `editar` (metadata) vs
        `auditar_condicion` (condición/estado físico/comentario) — la
        fecha de auditoría la pone el servidor, nunca el cliente. Ficha con
        `GET /equipment/{id}` fresco; "Dar de baja" pinta el 409
        `EQUIPO_OCUPADO` con el `detail` del servidor. Bug de doc
        encontrado: `CLAUDE.md` apunta a una ruta vieja de `RowActions.jsx`
        (continuación de R-I03, mismo commit `d602e00`). Bundle: 122.36 →
        122.72 kB gz. Los 4 e2e de Presupuestos: 48/48.
  - [x] **I4c — Wizard de nuevo prestamo (4 pasos).** `SignaturePad`
        (canvas + Pointer Events, deteccion de vacio real por bounding
        box, API imperativa, nunca base64 en estado), `PhotoCapture`
        (compresion 900px/0.72, reintento sin re-pedir archivo),
        `AccesoriosPicker`. Responsable de solo lectura desde la sesion
        (el contrato exige `user_id` real, no hay buscador de usuarios).
        Accesorios se combinan con la seleccion del equipo en un solo
        `POST /items` (reportado: no hay endpoint para editarlos despues,
        ver avances). Tres bugs reales de la misma causa raiz (el mock
        devuelve referencias vivas, no copias) encontrados y arreglados:
        `uploadMedia` nunca adjuntaba el media al item/firma
        (`addLoanMedia` vivia huerfana, sin dispatcher); un item se
        duplicaba al agregarlo (fix: refrescar con `fetchLoanById` en vez
        de anexar a mano); y por eso mismo un `setLoan` con la misma
        referencia no re-renderizaba (fix de raiz: `clone()` exportado de
        `state.js`, aplicado en la frontera publica de cada funcion de
        `mock/loans.js` — beneficia a I4d-g tambien). Bundle: 122.72 →
        122.80 kB gz. Los 4 e2e de Presupuestos: 48/48;
        `contrato-fixtures`/`equipos-errores` re-verificados sin
        regresion (18/18).
  - [x] **I4d — Prestamos activos.** Union de 3 estados (el contrato solo
        filtra por uno) resuelta con filtrado en cliente sobre una pagina
        de 200, no un parametro multivalor inventado. Tabla con los 3
        badges ortogonales por separado (estado/atrasado/entrega
        autorizada). `RegistrarDevolucionModal` (reutiliza `PhotoCapture`
        de I4c): 2 fotos o "no devuelto"+nota obligatoria por equipo,
        nunca a medias. "Ver responsiva" resuelve la URL async antes de
        abrir pestaña (mismo cuidado que `mediaUrl` en I4c). Bundle:
        122.80 → 122.85 kB gz. Los 4 e2e de Presupuestos: 48/48.
  - [x] **I4e — Aprobaciones.** Tres colas separadas, cada una detras de
        su propio permiso (autorizar_entrega/confirmar_devolucion/
        cerrar_incidencia). "Confirmar devolucion" explica ANTES de
        intentarlo que un prestamo con entrega_autorizada:false no puede
        llegar a completado (bloqueo verificado en pantalla real, no solo
        leido). "Cerrar incidencia" regresa los equipos de revision a
        activo. Verificado de punta a punta contra CE-0007 en el estado
        limite exacto que pedia el prompt (pendiente_confirmacion +
        entrega no autorizada a la vez). Bundle: 122.85 → 122.86 kB gz.
        Los 4 e2e de Presupuestos: 48/48.
  - [x] **I4f — Historial.** Filtros por los 6 estados, persona/folio/
        motivo y rango de fechas — primera vista que usa GET /loans/ con
        TODOS sus parametros documentados sin rodeos de cliente. Dos bugs
        reales de I3 arreglados: mock nunca implemento desde/hasta
        (decision documentada: filtra por fecha_entrega, comparacion de
        strings YYYY-MM-DD en vez de new Date()); fetchLoansExport vivia
        huerfana en real/loans.js (nunca en el dispatcher ni en el mock) y
        ademas usaba request() -que hace res.json()- para lo que debe ser
        un blob CSV. Arreglado: fetch -> blob -> descarga real, ApiError
        si el servidor falla, dispatcher completo, mock con el mismo
        contrato observable. Bundle: 122.86 kB gz (sin cambio, chunk
        lazy). Los 4 e2e de Presupuestos: 48/48.
  - [x] **I4g — Ficha de prestamo.** GET /loans/by-folio/{folio} (la
        razon de ser de esa ruta). Los 3 badges ortogonales juntos, fotos
        antes/despues lado a lado (miniaturas ampliables), bitacora con
        el Timeline generico que I1 ya habia dejado listo para esto.
        Criterio de aceptacion verificado en pantalla real: los 6 campos
        null del fixture demo se pintan como "—", nunca como texto "null"
        ni revientan el render. Bug real encontrado en pantalla (no
        leyendo codigo): state.media del mock arranca vacio pero el
        fixture demo referencia 4 ids de firmas/fotos como si ya
        existieran -> pageerror "no encontrada". Arreglado sembrando 4
        placeholders SVG en state.js. Bundle final: 122.89 kB gz (techo
        250). Los 4 e2e de Presupuestos: 48/48.
  - **Cierre de I4 completo**: 7/7 sub-paquetes, 48/48 e2e en cada uno,
    cero regresiones, 9 bugs reales encontrados y arreglados en el mismo
    commit que los encontro (ninguno quedo abierto). Bundle final 122.89
    kB gz contra el techo de 250.
- [x] **I5 — Permisos en la UI.** Commit de este issue (modo 09-ejecutar-todo,
      1 commit por issue). `src/modules/equipos/permisos/`: `catalogo.js`
      (import directo de la copia congelada de I3), `fallbackPorRol.js`
      (**temporal**, marcado para retiro — ver B-I14), `usePermisos.js`
      (`puede`/`permisosDe`, deny-by-default, fallback solo si `permisos`
      viene ausente/vacio, **jamas** regala paquetes aditivos por rol),
      `RequierePermiso.jsx` (modo `ui` y modo `ruta`). Modo diagnostico:
      `console.warn` una sola vez por clave `(modulo, accion)` fuera del
      catalogo — encontro y arreglo un bug real en el camino (ver
      `docs/riesgos/interfaz.md`, sin numero propio porque se arreglo el
      mismo dia sin quedar expuesto). `checkGlobalInjection` del mock de I3
      se amplio para cubrir tambien `PERMISOS_NO_DISPONIBLES` ademas de
      `SIN_PERMISO` (ambos son fallos de la capa de autorizacion, no de un
      endpoint puntual). Capturas de los 3 roles pedidos + el 503 (no
      desloguea, no se pinta como 403) + la consola con la clave inventada.
      Los 3 e2e de Presupuestos sin tocar: 25/25.
- [x] **I6 — e2e del flujo completo de equipos.** Commit de este issue
      (modo 09-ejecutar-todo, 1 commit por issue). `e2e/helpers/imagen.mjs`
      (PNG real via `node:zlib` con CRC32 propio — verificado con
      round-trip real de `zlib.inflateSync`, no solo "parece PNG"; JPEG
      minimo valido; `fotoGrande()` con ruido para forzar > 3 MB de verdad,
      un color solido hubiera comprimido a unos KB sin importar el lienzo).
      `e2e/helpers/sesiones.mjs` (un login por persona, `storageState`
      cacheado). `e2e/equipos-flujo-completo.spec.js` — **en `test.fixme`**
      con el motivo y la condicion de despertar escritos en el propio
      archivo; selectores aspiracionales (I4 no existe todavia).
      `e2e/equipos-errores.spec.js` — los 5 codigos feos corriendo HOY
      contra el mock de I3 via `DevMockHarness` (no fixme), 6/6. Riesgo
      nuevo: R-I14 (los bodies de escritura del contrato no traen ejemplo
      JSON, patron detras de R-I13). B-I06 tambien cerrado en este commit
      (ver abajo).

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
- [x] **B-I06 — Semilla de demo usable para capturas.** Commit de I6.
      `e2e/helpers/sembrar-demo.mjs`: generico y parametrizable (cuantos
      creadores/marcas/tickets, monto, ciclo, prioridad), sufijo por
      corrida (no choca con datos de una corrida anterior), solo por la API
      real (clics reales, cero escritura a `presupuesto.db`).
      `pantallas.spec.js` ya lo consume en vez de su bootstrap ad-hoc
      anterior — sigue en 23/23 (era 22/22 en el cierre de I1; subio a
      23/23 en I2 al agregar el chequeo de contraste en `/dashboard`, y se
      mantiene ahi tras el refactor, sin regresion).
      pero no es reusable por otros specs todavia.
- [ ] **B-I07 — Promover `useMobile` a un lugar compartido** cuando el modulo de
      equipos lo necesite. Quedo dentro de `modules/presupuestos/hooks/` por I0;
      es infra generica, no del modulo. Al moverlo, corregir tambien la ruta que
      `CLAUDE.md:46` documenta (R-I03).
- [ ] **B-I14 — Retirar `fallbackPorRol.js`** cuando WP1 (RBAC aditivo del
      servidor) este en pie y `/auth/me` mande siempre `permisos` con
      contenido real. Vive en `src/modules/equipos/permisos/`, marcado
      "TEMPORAL" en su cabecera. Al retirarlo, `usePermisos` deja de
      necesitar la rama de fallback y el import de `catalogo.js` en ese
      archivo especifico ya no hace falta.

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
- [ ] **B-I13 — Confirmar la forma del body de `POST /loans/{id}/devolucion`**.
      Ver R-I13: el contrato da la regla pero no un ejemplo JSON (a diferencia
      de `/confirmar-devolucion`, que si trae uno). `real/loans.js:returnLoan`
      adivino `{items: [...]}` para poder escribir el cliente; revisar ahi
      primero cuando el servidor real de Equipos aterrice.
- [ ] **B-I15 — Confirmar los nombres de campo de los bodies de escritura**
      de `POST /loans/`, `POST /loans/{id}/items` y
      `POST /loans/{id}/autorizar-entrega`. Ver R-I14: el contrato solo
      ejemplifica el *response* de `GET /loans/{id}`, nunca estos bodies —
      es el mismo patron que R-I13, pero encontrado escribiendo
      `equipos-flujo-completo.spec.js` (I6) contra el contrato completo, no
      un caso aislado. `real/loans.js` (I3) tiene la asuncion anotada
      explicita en el codigo (snake_case, calcado del ejemplo de lectura).
