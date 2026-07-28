# Backlog — interfaz

## Tareas de la asignacion

- [x] **I0 — Costura.** `d602e00`. Build verde, bundle identico, 25/25 e2e, 20/20
      capturas identicas.
- [ ] **I1 — Shell liquid glass (WP7-A), absorbiendo I7.** `src/design/`,
      `src/shell/`, `public/theme-boot.js`, particion de `index.css`,
      `MotionConfig` + `ToastProvider` en `main.jsx`, `manualChunks`.
      I7 va aqui y no al final: `theme-boot.js` y `fonts.css` autohospedadas ya
      viven en la lista de archivos de I1, se hacen juntos o se hacen dos veces.
      Cierra con capturas en desktop y 390px y el contraste **medido**.
- [ ] **I2 — Migracion visual de Presupuestos (WP7-B).** Solo piel sobre los ~40
      archivos ya movidos. Rutas sin cambio. Cero llamadas a API y cero
      condiciones de negocio en el diff.
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

- **B-I01 — Nav y strict mode.** Contrato por etiqueta, no por componente: el
  `nav` que lista secciones de Presupuestos lleva siempre
  `aria-label="Navegacion de Presupuestos"`, lo renderice `Sidebar` hoy o
  `GlassNav` despues. El nav superior nuevo lleva
  `aria-label="Navegacion principal"`. Las 9 aserciones `page.locator("nav")`
  (`auth.spec.js` 99-101 y 158-160, `gastos-generales.spec.js` 169 y 181,
  `presupuesto-flujo-completo.spec.js` 191) pasan a
  `getByRole("navigation", { name: ... })` en el **mismo commit** que monta
  `AppShell`. Asi sobrevive I2 sin volver a tocarse.
- **B-I02 — Fuentes.** `@fontsource` autohospedado. Ver R-I06.

## Pendientes tecnicos

- [ ] **B-I03 — Bajar el bundle inicial de 261.76 kB gz a menos de 250.** Ya
      estaba vencido antes de empezar (R-I01). `manualChunks` + split por ruta +
      diferir ApexCharts. Se mide en cada cierre de paquete, no al final.
- [ ] **B-I04 — Resolver la colision `AppShell`** entre el componente local de
      `App.jsx:48` y `src/shell/AppShell.jsx`. Se decide al escribir I1 (R-I05).
- [ ] **B-I05 — Formalizar el verificador de capturas.** Hoy es un script en el
      scratchpad: levanta sesion, recorre las 10 rutas en 1280x800 y 390x844,
      cuenta caracteres del DOM, alto de `#root` y canvas de ApexCharts, y falla
      si una pantalla sale vacia. Deberia vivir en `frontend/e2e/helpers/` para
      que el criterio de "pantalla pintada" sea reproducible por cualquiera y no
      dependa de mi maquina.
- [ ] **B-I06 — Semilla de demo usable para capturas.** Hoy hay que aprobar los
      355 tickets por la API despues de sembrar (R-I04). Deberia existir un paso
      documentado, o pedir que el seed del backend deje datos que si pinten.
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
      Bloquea el cierre visual de I1 (R-I06).
