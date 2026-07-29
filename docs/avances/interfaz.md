# Avances — interfaz

## 2026-07-29 (sesion 3 — modo 09-ejecutar-todo, cinco issues sin push)

### ISSUE I2 — Piel de Presupuestos (cerrada, 1 commit)

Decisión central: el "va cristal" de `02-I2-piel-presupuestos.md` (paneles,
modales, KPI tiles, popover de perfil) choca con el límite duro de 3-4
superficies simultáneas de DESIGN_SYSTEM.md en cuanto se aplica literal a los
8 KPI de Dashboard — así que solo 2 de 8 (`Total Gastado`, `Total
Disponible`) llevan `glass`; el resto queda plano. Con el nav de módulos del
shell (1, siempre presente) + esas 2, quedan 3 superficies simultáneas en
`/dashboard`, dentro del límite.

`KpiCard.jsx` se dejó **sin tocar** a propósito: `DashboardPdfTemplate.jsx`
(intocable en piel, regla dura del pool) todavía lo importa directamente, y
html2canvas no sabe rasterizar `backdrop-filter` — meterle cristal ahí
habría reventado el PDF. `Dashboard.jsx` (la vista en vivo) migró a
`KpiTile` (`@/design`); el PDF sigue con `KpiCard` intacto.

`Modal.jsx` pasó a `.glass`+`.veil` conservando su API exacta
(`{title, onClose, submitting, children}`): sus 5 consumidores
(`AdminView`, `UserManagement`, `ValidationQueue`,
`GeneralExpensesExportModal`, `DeleteConfirmModal`) heredan el cristal sin
que se les tocara una línea — confirmado por el diff (`git diff --stat`
no los lista). Los 3 modales con wrapper propio
(`UploadTicketModal`, `GeneralExpenseModal`, `MediaViewerModal`) y
`ProfilePopover` recibieron el mismo patrón a mano. `LoginPage` es la única
pantalla que lleva cristal en su propia superficie (nada más compite por el
presupuesto ahí).

**Autoverificación obligatoria (02-I2 §"La regla que define el paquete")**:

```
git diff --stat -- frontend/src
git diff -U0 -- frontend/src | grep -nE "^[+-].*(fetch\(|request\(|from \"@/api\"|from '@/api'|useEffect|budget_cycle|is_deleted|status ===|role ===|ADMIN_ROLES)"
```

8 archivos en el diff; el grep salió **vacío** — cero llamadas a API, cero
condición de negocio tocada.

**Verificado, no solo asumido**: el chequeo de contraste de
`pantallas.spec.js` (heredado de I1) solo visitaba `/` — las 2 KpiTile
nuevas de `/dashboard` habrían quedado sin medir. Se agregó un segundo
recorrido (`/` y `/dashboard`) al mismo test; ambas rutas miden >= 4.5:1 real
(no una suposición porque "ya se midió en I1").

**Evidencia**

```
npm run build verde.
dist/assets/index-*.js       47.25 kB  gzip: 14.79 kB
dist/assets/index-*.css      29.80 kB  gzip:  6.88 kB
Payload real de /login (medido con Playwright contra vite preview, los
mismos 4 chunks eager que en I1): index + react-vendor + motion + LoginPage
= 14.79 + 52.97 + 45.03 + 1.10 = 113.89 kB gz de JS + 6.88 kB gz de CSS
≈ 120.8 kB gz total (techo: 250 kB gz, I1 cerró en ~118.3 kB gz).
`motion` subió de 42.51 a 45.03 kB gz: Dashboard (lazy) ahora también usa
`animate()` vía KpiTile, y manualChunks agrupa TODO framer-motion en un
único chunk que ya era eager por GlassNav — el codigo nuevo de animate()
se vuelve eager aunque solo lo use una vista lazy. Con ~129 kB de margen
todavía no hace falta LazyMotion+domAnimation, pero I4 (mas vistas, mas
motion) es donde esto se puede apretar.
```

3 e2e de Presupuestos + pantallas.spec.js, cada uno con DB propia recién
sembrada y uvicorn reiniciado entre archivos:

| Spec | Resultado |
|---|---|
| `auth.spec.js` | 7/7 |
| `presupuesto-flujo-completo.spec.js` | 9/9 (incluye el PDF del dashboard — confirma que `KpiCard`/`DashboardPdfTemplate` siguen intactos — y el popover de perfil) |
| `gastos-generales.spec.js` | 9/9 |
| `pantallas.spec.js` | 23/23 (20 pantallas + bootstrap + 2 contraste: `/` y `/dashboard`) |

Capturas reales (1280x800 y 390x844 donde aplica) en
`C:\dev\prompts-interfaz\respaldos\I2\`: `login`, `home`, `dashboard` (ambos
anchos), `profile-popover` (ambos anchos), y una de `modal-nuevo-ticket`
(1280x800) que alcanzó a salir antes de que un bug de mi propio script de
captura (no del producto — el guion repetía navegaciones a "/" en una
secuencia que un botón del Sidebar no toleraba; los 25 e2e reales sí hacen
ese mismo click sin problema) me hiciera abandonar esa captura específica en
los demás anchos.

**No verificado en pantalla real**: todo lo anterior es Playwright headless
(Chrome real vía CDP, no un ojo humano) — sigue sin haber verificación
manual en un navegador con usuario.

**Riesgo nuevo**: ninguno. El `motion` chunk creciendo por goteo (arriba) no
es un riesgo nuevo, es continuación de lo ya anotado en I1 commit 4.

### ISSUE I3 — Mocks del contrato + `ApiError` (cerrada, 1 commit)

`ApiError extends Error` en `client.js`, con `status`/`codigo`/`detail`
ademas del `message` habitual (que sigue siendo exactamente `body.detail`:
verificado que ningun `catch (e) { setError(e.message) }` existente en
Presupuestos se enteró del cambio — los 25/25 e2e de Presupuestos lo
confirman). `esCodigo(e, codigo)` exportado desde `@/api`. Los dos multipart
existentes (`uploadTicket`, `createGeneralExpense`) migraron a la misma
`throwApiError` compartida en vez de duplicar el parseo del sobre de error
tres veces.

6 fixtures copiados **literal** a `src/modules/equipos/api/mock/fixtures/`
(`empresas.json`, `equipos.json`, `errores.json`, `prestamo_demo.json`,
`permisos_catalogo.json`, `auth_me.json`) — `diff` contra el original de
`docs/contratos/` salio vacio en los 6. `frontend/e2e/contrato-fixtures.spec.js`
nuevo: compara ambos lados con `toEqual` profundo, 6/6, no necesita
navegador (es una comparacion de archivos, corre en ms).

`src/modules/equipos/api/` completo: `equipment.js`, `loans.js`, `media.js`,
`empresas.js`, `permisos.js` (uno por dominio) + `index.js` (barril). Cada
dispatcher decide su transporte con `import()` dinamico segun
`import.meta.env.VITE_EQUIPOS_MOCK === "1"`. `real/*.js` implementa el
cliente HTTP contra las rutas de `API_EQUIPOS_v1.md` (para cuando el
servidor real aterrice); `mock/*.js` implementa la maquina de estados
completa en memoria: `borrador → prestado → pendiente_confirmacion →
completado | incompleto`, el indice unico "un equipo no puede estar en dos
prestamos abiertos" replicado en memoria (`equipoTieneAbiertoUnLoan`),
`confirmar` exige 2 fotos por equipo + 2 firmas o `409 TRANSICION_INVALIDA`,
`entrega_autorizada: false` bloquea `completado`, `decision != "ok"` exige
`nota` o `422`.

Inyeccion de errores por `localStorage["equipos-mock-error"]`
(`getInjectedError`/`setInjectedError`/`checkGlobalInjection`/
`checkInjection`): `SIN_PERMISO` truena en cualquier accion (chequeo global
al inicio de cada funcion del mock, sin excepcion), los otros 4 son
puntuales (`EQUIPO_OCUPADO` en `addLoanItem`, `PERMISOS_NO_DISPONIBLES` en
`fetchPermisosCatalogo`, `MEDIA_MUY_GRANDE` en `uploadMedia`,
`SESION_EXPIRADA` en `addLoanMedia`/`confirmLoan` — paso 3 y 4 del wizard,
tal como pide la asignacion).

**El "Como se acepta este paquete" pide 5 capturas mostrando que la UI se ve
bien en cada codigo feo — pero I4 (donde vivirian las vistas reales de
Equipos) todavia no existe.** Se resolvio con un panel de diagnostico
temporal (`DevMockHarness.jsx`, ruta `/equipos/_mock-harness`, montado solo
si `import.meta.env.DEV`): dispara cada codigo contra el mock real y muestra
el resultado via `Toast` (el componente de I1), con el JSON crudo del error
debajo para verificar `status`/`codigo`/`message` a simple vista. Se anota
explicito: **este panel se borra cuando I4 tenga sus propias 7 vistas
reaccionando a estos mismos codigos** — no es infraestructura permanente.

**Verificado, no solo asumido**, mirando el `dist/` real de un build sin
`VITE_EQUIPOS_MOCK`:

```
grep -rl "EQUIPO_OCUPADO\|estado_fisico\|equipos-mock-error\|DevMockHarness" dist/
# exit 1 — cero coincidencias en TODO dist/, no solo fuera del chunk principal
ls dist/assets/*.js | wc -l   # 25 (el mismo numero que sin el modulo de Equipos)
```

El modulo completo de Equipos (fixtures, mock, harness) desaparece del build
de produccion porque nada mas lo importa todavia — no es solo que el mock
quede en un chunk aparte, es que Rollup elimina la rama muerta completa por
`import.meta.env.DEV`/`VITE_EQUIPOS_MOCK` ser constantes conocidas en build
time.

**Riesgo nuevo — R-I13**: `API_EQUIPOS_v1.md` §3 no da un ejemplo de body
para `POST /loans/{id}/devolucion` (a diferencia de
`/confirmar-devolucion`, que si trae uno). `real/loans.js:returnLoan`
adivino la forma (`{items: [...]}`); anotado en el codigo y en
`docs/riesgos/interfaz.md` para que sea el primer lugar a revisar cuando el
servidor real aterrice. No bloquea I3/I4 porque el mock no depende de esa
adivinanza.

**Evidencia**

```
npm run build verde. Sin cambio de peso real: index-*.js 14.88 kB gz,
CSS 6.89 kB gz (igual que I2 — ApiError pesa lo que pesa una clase de 20
lineas). Payload real de /login: ~120.8 kB gz, igual que I2.
```

Los 3 e2e de Presupuestos (uvicorn reiniciado + DB fresca entre cada uno):
`auth.spec.js` 7/7, `presupuesto-flujo-completo.spec.js` 9/9,
`gastos-generales.spec.js` 9/9. Mas `pantallas.spec.js` 23/23 y
`contrato-fixtures.spec.js` 6/6 en la misma invocacion (29/29 total).

Capturas reales en `C:\dev\prompts-interfaz\respaldos\I3\`: el harness en
su estado inicial, y una por cada uno de los 5 codigos feos
(`409-equipo-ocupado`, `403-sin-permiso` en 1280x800 y 390x844,
`503-permisos-no-disponibles`, `413-media-muy-grande`,
`401-sesion-expirada`), cada una mostrando el toast real con el mensaje y
codigo exactos de `fixtures/errores.json`.

**No verificado en pantalla real**: Playwright headless otra vez, sin ojo
humano. Tampoco se verifico el cliente `real/*.js` contra un servidor de
verdad (no existe todavia) — solo se revisó que las rutas/metodos/body
coincidan con lo que documenta `API_EQUIPOS_v1.md`, con la excepcion
anotada en R-I13.

### ISSUE I5, I6, I4 — en progreso, ver entradas mas abajo en esta misma sesion.

## 2026-07-28 (sesion 2)

### I1 — Shell liquid glass (WP7-A), absorbiendo I7 (cerrada): 5 commits

`210e735` → `0055206` → `a13ebe3` → `c14a368` → `47020d8`.

**Commit 1 — `210e735`: tokens de cristal, fuentes autohospedadas, arranque limpio.**
`src/design/{tokens,fonts,glass}.css` importados antes de `@tailwind base`.
`[data-theme="light"]` movido verbatim, sin `:root` (regla dura del PDF de
Presupuestos, intacta). Fuentes: `@fontsource` con **solo el subset `latin`**
por peso (JetBrains Mono 400/500/600, Nunito 400/600/700, Inter 400/500/600):
el subset agregado (sin especificar) hubiera traido cyrillic/greek/vietnamese
de balde e inflado el CSS de 6.01 a 28.62 kB gz por nada; con subset, 6.54 kB
gz. `theme-boot.js` como script clasico bloqueante (sin `type="module"` ni
`defer"`) en `public/`, verificado por el HTML servido
(`<script src="/theme-boot.js"></script>`, sin atributos que rompan el
bloqueo del parser). `tailwind.config.js` lee `var(--go-font-*)`.

**Commit 2 — `0055206`: los 13 componentes de `src/design/`.**
Requisitos no opcionales verificados uno por uno: `GlassModal` con focus trap
real (ciclo Tab/Shift+Tab sobre los focusables del panel), Esc, click en
backdrop, devuelve foco al disparador, bloquea scroll del body. `GlassNav`
con pildora `layoutId` (animacion magnetica) que en `prefers-reduced-motion`
deja de usar `layoutId` (no hay layout animation, que es movimiento) y solo
hace fade de opacidad de una pildora ya fija. `KpiTile` con `animate()` de
`motion`, <=600ms, valor final siempre como texto en el DOM; `glass` es
**opt-in** (default tarjeta plana): una fila tipica de KPIs son 4-7 tiles y
el limite duro de DESIGN_SYSTEM.md es 3-4 superficies de cristal simultaneas.
`CommandPalette` nunca captura teclas (ni el propio Cmd/Ctrl+K) si el foco
esta en input/textarea/contenteditable; desmontada por completo mientras
esta cerrada. `StatusDonut` en SVG/CSS puro (Apex aqui hubiera arrastrado
942 kB al chunk del shell). `main.jsx`: `MotionConfig reducedMotion="user"`
+ `ToastProvider`, sin tocar el orden `BrowserRouter`/`ThemeProvider`/
`AuthProvider`.

**Commit 3 — `a13ebe3`: shell, renombre `AppShell`, etiquetas de nav, 9 aserciones.**
El `AppShell` local de `App.jsx:48` (contenedor de datos/rutas de
Presupuestos) se movio tal cual a
`src/modules/presupuestos/PresupuestosLayout.jsx` (B-I04). `src/shell/
AppShell.jsx` es el chrome generico. `ProtectedRoute` gano un fallback
aditivo `children ?? <Outlet />` (cero riesgo en sus ~6 usos existentes, que
siguen pasando `children`). `ModuleTabs` (Presupuestos/Equipos) se monta
como overlay flotante centrado sobre la fila vacia del Header existente, no
como segunda barra fija — evita tocar `Header.jsx`/`Sidebar.jsx` (fuera de
alcance de I1) y correr sus offsets. Confirmado en pantalla real
(1280x800 y 390x844, sesion de superadmin): sin colision, sin contenido
tapado. Equipos visible y `aria-disabled` (I4 le da rutas). Las 3 etiquetas
de nav (`Sidebar` "Navegacion de Presupuestos", `GlassNav` "Navegacion
principal", `AdminView.jsx:296` "Secciones de Administracion", esta ultima
antes sin etiqueta) confirmadas coexistiendo sin ambiguedad en
`/administracion` (evaluado en el propio navegador: 3 `<nav>`, 3 aria-label
distintos). Las 9 aserciones de los 3 specs migradas a `getByRole`.

**Commit 4 — `c14a368`: particion del bundle (B-I03).**
`React.lazy` + `Suspense` (fallback `SkeletonShimmer`) en las 9 paginas de
`PresupuestosLayout.jsx` y `LoginPage` en `App.jsx`. `manualChunks`:
`react-vendor`, `apex` (`apexcharts`+`react-apexcharts` en el mismo chunk),
`motion`. Medido con Playwright contra `vite preview` (no solo leido del
output de `npm run build`): visitar `/login` pide exactamente 4 JS —
`index` (14.86 kB gz), `react-vendor` (52.97 kB gz), `motion` (42.51 kB gz),
`LoginPage` (1.09 kB gz) — mas el CSS (6.94 kB gz). Total inicial real:
~118.4 kB gz, contra el techo de 250. `apex` (627.39 kB / 174.54 kB gz),
`html2canvas` y `jspdf` confirmados fuera del grafo eager (no se piden en
`/login`; solo al entrar a `/dashboard` o exportar un PDF, verificado con
`presupuesto-flujo-completo.spec.js` que ejercita ambos caminos). `motion`
sigue eager porque `ToastProvider` envuelve toda la app desde `main.jsx`
— anotado como candidato a `LazyMotion`+`domAnimation` si el margen se
aprieta en I4, no forzado ahora con este margen.

**Commit 5 — `47020d8`: verificador de pantallas formal (B-I05).**
`e2e/helpers/pantallas.mjs` (10 rutas x 2 anchos, mide texto de `#root`,
alto real y `.apexcharts-canvas`), `e2e/helpers/contraste.mjs` (formula WCAG,
acepta hex y `rgb()`/`rgba()`), `e2e/pantallas.spec.js` (bootstrap con un
creador+marca+ticket real —el ticket de superadmin se auto-aprueba— para que
`/dashboard` tenga algo que graficar en vez de repetir la trampa R-I04; un
solo login con `storageState` para las 20 capturas). El verificador
**encontro un bug real** escribiendo el chequeo de contraste: el primer
intento media 1.06:1 en `GlassNav` (muy por debajo de 4.5:1). Causa en
disco: `index.html` traia `<body class="bg-gray-50 text-gray-900
antialiased">` heredado del starter de Tailwind, nunca limpiado — esas
clases (capa `utilities`, gana sobre `@layer base` donde vive
`body { color: var(--go-text-secondary) }` de `index.css`) pisaban en
silencio el tema real en el elemento raiz. Invisible a simple vista porque
cada contenedor de Presupuestos fija su propio `background` inline; pero el
`<a>` de `GlassNav` (que confia en `color: inherit` para llegar hasta
`body`) se pintaba con gray-900 de Tailwind en vez de
`--go-text-secondary`. Sin ninguna referencia en `src/` (confirmado por
grep): se quito sin sustituto, cero regresion. Detalle completo con
evidencia: `docs/riesgos/interfaz.md` R-I12.

**Evidencia del cierre**

`npm run build` verde en los 5 commits. Bundle final:
`dist/assets/index-*.js` 47.47 kB (gzip 14.87 kB), CSS 29.98 kB (gzip
6.89 kB) — el numero que trackeaba R-I01/B-I03 (index-*.js) baja de
261.76 kB gz a 14.87 kB gz; el payload real de arranque (medido, no
inferido) es ~118.4 kB gz, bajo el techo de 250.

Las 20 capturas (10 rutas x 2 anchos) via `e2e/pantallas.spec.js`, con datos
reales: `/dashboard` muestra `$750.00` gastado y una barra real en
"Transacciones por mes" en vez del estado "Sin datos" de R-I04. El
verificador: 22/22 (bootstrap + 20 pantallas + contraste medido, cada
superficie `.glass` del shell >= 4.5:1).

Los 3 e2e de Presupuestos, desde DB propia recien sembrada y uvicorn
reiniciado entre archivos, corridos **dos veces** (tras el commit 3 y otra
vez al final, para confirmar que ni la particion del bundle ni el fix de
`index.html` regresaron nada):

| Spec | Tras commit 3 | Al cierre del paquete |
|---|---|---|
| `auth.spec.js` | 7/7 | 7/7 |
| `presupuesto-flujo-completo.spec.js` | 9/9 | 9/9 |
| `gastos-generales.spec.js` | 9/9 | 9/9 |

25/25 en ambas corridas. Sin tocar: `apexTheme.js`, `components/PdfReport/`,
`backend/`.

### Entorno (sesion 2)

- El repo ya tenia procesos huerfanos de OTRO proyecto del usuario corriendo
  en la maquina (`automatizacion_ventas_sacos`, en `G:\Mi unidad\...`, puertos
  8080/8002) al momento de reiniciar el backend entre especificaciones de
  e2e. Se identificaron por `wmic process ... get CommandLine,ProcessId`
  antes de matar nada — **no se tocaron**, solo se cerro el PID exacto del
  uvicorn propio (verificado por `netstat` antes de cada `taskkill`).
- `presupuesto.db` (la del uso normal, con datos reales) quedo con un
  handle bloqueado (`Device or resource busy` al borrar) tras un reinicio de
  uvicorn con `--reload`: el supervisor de recarga deja un proceso hijo vivo
  que no muere con el `taskkill` del padre. En vez de forzar el borrado, se
  uso `DATABASE_URL=sqlite:///./presupuesto_e2e_i1.db` (variable de entorno
  que `database.py` ya lee) para los 47 e2e de esta sesion: una DB de
  prueba aparte, sin tocar la de uso normal en ningun momento. Gitignorada
  (`*.db` en la raiz).
- La extension de Claude in Chrome fue declinada esta sesion: toda captura y
  verificacion en navegador real se hizo con scripts de Playwright headless
  (el mismo motor que usan los e2e), no con capturas manuales.

### I0 — Costura (cerrada): `d602e00`

`git mv` de `components/`, `pages/`, `hooks/` y `utils/` a
`src/modules/presupuestos/`. Los cuatro juntos, no dos: asi los imports internos
del modulo (`../utils/priority`, `../hooks/useSortable`, `../../hooks/useMobile`)
siguen resolviendo sin tocarse, y solo se reescriben los 37 imports que cruzan la
frontera. `api/`, `context/` y `assets/` se quedan en `src/` porque los va a
compartir el modulo de equipos.

Ademas: `src/api/client.js` con el transporte, `src/api/index.js` como barril,
alias `@` en `jsconfig.json` y en `resolve.alias` de `vite.config.js`.

Git detecto los 41 archivos como rename con 95-100% de similitud.

**Evidencia**

`npm run build` verde, y los bundles salen con **hash de contenido identico** al
de antes del movimiento:

```
dist/assets/index-DaiH1YwQ.js    942.05 kB  gzip: 261.76 kB
dist/assets/index-BHkVJudo.css    24.90 kB  gzip:   6.01 kB
+ los 4 PNG de logos, mismo hash
```

Mismo hash = mismo bundle byte por byte. Es una prueba mas fuerte que comparar
capturas a ojo.

Capturas reales de las 10 rutas (`/login`, `/`, `/dashboard`, `/creadores`,
`/transacciones`, `/validacion`, `/gastos-generales`, `/administracion`,
`/perfil`, `/403`) en desktop 1280x800 y en 390x844, antes y despues del
movimiento: **las 20 imagenes son identicas por SHA256**.

Las capturas se tomaron contra datos reales, no contra el estado vacio: 355
tickets aprobados, 8 marcas, 6 creadores, 2 gastos generales. El dashboard monta
sus 5 canvas de ApexCharts en los dos anchos. El verificador cuenta
`.apexcharts-canvas`, no solo caracteres del DOM: DOM lleno no es pantalla
pintada, y un dashboard con datos en cero pinta el estado vacio sin montar ni un
grafico, lo que esconderia una regresion.

Los 3 e2e desde DB limpia, reiniciando el backend entre archivos:

| Spec | Antes de I0 | Despues de I0 |
|---|---|---|
| `auth.spec.js` | 7/7 | 7/7 |
| `presupuesto-flujo-completo.spec.js` | 9/9 | 9/9 |
| `gastos-generales.spec.js` | 9/9 (tras `1568ff6`) | 9/9 |

Sin tocar: `index.css`, `index.html`, `package.json`, `tailwind.config.js`, los 3
specs, y todo `backend/`.

### Pre-I0 — `gastos-generales.spec.js` venia rojo de fabrica: `1568ff6`

Antes de mover nada corri los 3 specs para tener baseline. `gastos-generales`
fallaba: 2 pasaban, 1 fallaba, 6 no corrian. El archivo usa
`test.describe.serial`, asi que una sola asercion podrida abortaba 7 de 9 tests.

Causa: el spec nunca elegia marca en el modal de nuevo gasto general, y la marca
es obligatoria (`models.GeneralExpense.brand_id` `nullable=False`,
`schemas.GeneralExpenseCreate.brand_id` requerido, `required` en el select del
modal mas un guard propio en JS). La validacion nativa del navegador bloqueaba el
submit; la captura de fallo muestra el tooltip "Please select an item in the
list" sobre el campo MARCA.

Backend y UI coinciden: el spec era el desactualizado. Arreglado en un commit
aislado, antes de I0, para que I0 quedara demostrable.

### Entorno

Bloqueos resueltos, con su causa, para que no se vuelvan a descubrir a golpes:

- **El repo no puede vivir en `G:\Mi unidad` (Google Drive).** Windows la reporta
  como FAT32: no soporta reparse points (la junction falla con "Funcion
  incorrecta") y `npm install` revienta con `EPERM`/`EBADF` a mitad del arbol.
  El mismo `npm install` en `C:\dev\Ready2Go` cierra en 18s con 165 paquetes.
  Se trabaja en `C:\dev\Ready2Go`.
- **`pip` fallaba con `SSLError` contra PyPI** aunque PowerShell si alcanza
  pypi.org: `certifi` no trae el CA corporativo, el almacen de Windows si.
  Se resuelve con `pip install --use-feature=truststore`, sin desactivar la
  verificacion TLS.
- **Los 3 specs no se pueden correr en una sola invocacion.** El rate limit de
  login es 30 por 15 min por IP y esta en memoria (`security._login_attempts_by_ip`),
  asi que se resetea reiniciando uvicorn. Se corre un archivo, se reinicia el
  backend, se corre el siguiente.
- **`auth.spec.js` no es idempotente**: rota la contraseña del superadmin en su
  test 2. Necesita DB recien sembrada con `seed_auth.py`.

### Cierre de sesion

Push a `BeniBranch` limpio: `281f10b..012ef13`, fast-forward, 0 commits detras
del remoto. Tres commits: `1568ff6` (arreglo del spec), `d602e00` (I0),
`012ef13` (estos reportes).

La llave SSH `id_ed25519` sigue sin autorizar en la org, asi que el clon y el
push van por HTTPS con Git Credential Manager. Ya no bloquea, pero el comando de
clonado que da la asignacion (`git@github.com:...`) falla de entrada para quien
lo copie tal cual. Ver R-I08.
