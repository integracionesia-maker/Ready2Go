# Avances — interfaz

## 2026-07-29/30 (sesion 4 — I8, integracion real, 7 lotes)

El carril de servidor aterrizó completo en `BeniBranch` (S0..S7, merge limpio
sin conflictos: tocó solo `backend/` y `docs/*/servidor.md`, este carril solo
`frontend/` y `docs/*/interfaz.md`). I4 quedó verificado contra el mock, no
contra la API real — I8 cierra esa brecha.

### Lote 1 — Paridad de los bodies de escritura (cerrado)

**El 422 se reprodujo primero, contra el servidor real**, antes de tocar una
línea: wizard completo (crear → agregar equipo → subir 2 fotos → firmar →
confirmar) funcionó de punta a punta sin un solo 422 — folio real `CE-0008`
emitido por la base. El único 422 apareció al intentar `POST
/loans/{id}/devolucion` desde `Activos`, exactamente como describía el
paquete: `RegistrarDevolucionModal.jsx` mandaba `{itemId, noDevuelto,
notaDevolucion}` (camelCase) y `DevolucionItem` (schema real) exige
`{loan_item_id, no_devuelto, nota_devolucion}`, con `loan_item_id`
obligatorio y sin default.

**Bug adicional encontrado ANTES de poder siquiera reproducir el 422** (no
nombrado en el paquete): `RegistrarDevolucionModal` y `ConfirmarDevolucionModal`
tronaban con un error de React (`Cannot read properties of undefined
(reading 'map')`) al abrirse desde `ActivosPage`/`AprobacionesPage` contra el
servidor real. Causa: `GET /api/loans/` devuelve `LoanRow` — la fila liviana
del listado (`schemas_loans.py`), **sin** `items[]`, sin `firmas`, sin
`responsiva` — pero ambas páginas pasaban esa fila directo a modales que
esperan la ficha completa (`LoanDetail`, con `items[].media` por renglon). El
mock nunca distinguió fila de ficha (`fetchLoans()` siempre devolvía el
objeto completo), así que este desfase real-vs-mock sobrevivió invisible a
los 48/48 de I4d/I4e. Arreglado: ambas páginas ahora piden `fetchLoanById(loan.id)`
antes de abrir el modal, en vez de pasar la fila tal cual. De paso, la
columna "Equipos" de `ActivosPage` (que leía `loan.items` — siempre vacía
contra el servidor real, `LoanRow` no lo tiene) se corrigió a `loan.equipos`
(el campo real de la fila), y "Ver responsiva" pasó de comprobar
`loan.responsiva` (tampoco existe en la fila) a comprobar `loan.folio`
(se asigna en el mismo momento que la responsiva).

**Fix de 1.1**: siguiendo el patrón que ya usaba `ConfirmarDevolucionModal.jsx`
para `/confirmar-devolucion` (mandar las llaves reales directo, sin capa de
conversión), `RegistrarDevolucionModal.jsx` ahora arma
`{loan_item_id, no_devuelto, nota_devolucion}` — `real/loans.js` sigue
siendo un paso directo (raw passthrough), consistente con
`confirmReturnDecision`.

**Fix de 1.2 (bug latente, R-I14)**: `NuevoPrestamoPage.jsx` mandaba
`responsable: {user_id, nombre, email}` anidado; `LoanCreate` exige las tres
claves **planas** (`responsable_user_id/nombre/email`). Pydantic ignoraba la
clave desconocida en silencio y el servidor caía a `current_user` — hoy
coincide siempre (el wizard es autoservicio), así que nunca se vio roto.
Arreglado a las tres claves planas, con el comentario de por qué en el
código.

**Hallazgos adicionales del mismo patrón** (no nombrados en el paquete, pero
mismo bug de forma — cuerpo obligatorio sin mandar ninguno):
`cancelLoan` (`CancelarRequest`) y `dischargeEquipment`
(`BajaRequest`, en Inventario) mandaban `POST` sin body a rutas que
declaran un parámetro Pydantic obligatorio (aunque su único campo sea
opcional, FastAPI exige *algún* JSON). Ambas corregidas a mandar
`{motivo: null}` si no hay motivo.

**Limpieza relacionada**: `EquipmentFormModal.jsx` inventaba
`estado_operativo`/`condicion` al crear un equipo — confirmado leyendo
`routers/equipment.py` que `EquipmentCreate.model_dump()` ni siquiera
conserva esas dos claves (Pydantic las descarta antes de validar, nunca
llegan a `crud_equipment.crear`, que ya las default a "activo"/"bueno" él
mismo). Se dejó de inventarlas en el cliente; el mock ahora pone los mismos
default por su cuenta en vez de esperar que el cliente los mande.

**1.3 — el mock deja de mentir**: `mock/loans.js` ahora exige
`loan_item_id` en cada item de `/devolucion` (422 con el mismo sobre del
contrato si falta), igual que el servidor real. No se borró nada:
`equipos-errores.spec.js` lo sigue necesitando para el 503, imposible de
provocar a voluntad en el servidor real.

**1.4 — prueba de paridad** (`frontend/e2e/paridad-bodies-equipos.spec.js`,
10 casos): llama cada función de `real/loans.js`/`real/equipment.js`/
`real/media.js` con `window.fetch` interceptado en el propio navegador
(nunca toca la red), y compara las llaves del body capturado contra una
copia de lectura de `schemas_loans.py`/`schemas_equipment.py`. Cubre los 9
endpoints que pedía el paquete, incluyendo la afirmación explícita de que
`/autorizar-entrega` y `/confirmar` **no** llevan body. **Alcance honesto**:
protege la fidelidad de la capa de transporte (`real/*.js`) dado un input
ya bien formado — para `createLoan`/`returnLoan`/`confirmReturnDecision`
(passthrough crudo, sin conversión), un regreso a camelCase en el
COMPONENTE que llama no lo detectaría esta prueba; lo detectaría
`equipos-flujo-completo.spec.js` (I8 lote 4) contra el servidor real, con
un 422 de verdad. Para `addLoanItem` (que sí convierte camelCase→snake_case
dentro de `real/loans.js`) la prueba sí protege ese código directamente.

**Evidencia**

```
npm run build verde. Bundle sin cambio real: 122.89 kB gz de /login (todos
los archivos tocados son chunks lazy o el dispatcher/mock, fuera del grafo
eager). dist/ grep sigue sin rastro de mock/harness/permisos-demo.
```

Migraciones y seeds del servidor corridos en el orden que sus propios
encabezados exigían (no el orden sugerido por el paquete): `seed_auth.py` →
`migrate_rbac_aditivo.py` → `migrate_equipos.py` → `seed_equipos.py` →
`seed_prestamo_demo.py` → `seed_rbac.py` (invertido respecto al paquete:
`seed_prestamo_demo.py` siembra a `melisa` con `user_id=4` exacto — el que
pide el fixture — y `seed_rbac.py --crear-si-falta` ejecutado antes se la
había robado con `id=2`; el propio script avisó y no pisó nada, se
reconstruyó la base con el orden correcto).

`paridad-bodies-equipos.spec.js`: 10/10. `equipos-errores.spec.js`: 6/6.
`contrato-fixtures.spec.js`: 6/6 (sin regresión tras el endurecimiento del
mock). Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48).

**No verificado en pantalla real**: el 422 original solo se capturó por
red (`page.on("response")`), no se guardó una captura de pantalla del
error tal cual lo vería una persona (el toast de error sí se probó en I4d
contra el mock, con el mismo componente).

**Riesgo nuevo**: ninguno — todos los bugs de este lote se encontraron y
arreglaron dentro del mismo commit.

### Lote 2 — Levantar el módulo contra el servidor real (cerrado)

Con `VITE_EQUIPOS_MOCK` apagado, las 7 vistas recorridas en 1280x800 y
390x844 contra datos reales (préstamos `CE-0007`..`CE-0012`, creados a
propósito para cubrir cada caso — devolución confirmada, entrega
autorizada, atraso real, borrador sin terminar). Tres hallazgos serios,
los tres arreglados en este commit; ninguno estaba nombrado en el paquete.

**Hallazgo 2.1 (severo) — la ficha se ponía en blanco al autorizar una
entrega o confirmar una devolución de verdad.** `entrega_autorizada_por` y
`confirmada_por` son `Optional[PersonaRef]` en `LoanDetail`
(`schemas_loans.py`) — un objeto `{user_id, nombre}`, no un string.
`FichaPrestamoPage.jsx` los pintaba como hijos JSX directos
(`{loan.entrega_autorizada_por}`). Mientras el campo es `null` (el
fixture `CE-0007` que usó I3/I4 siempre lo trae así) no pasa nada; en
cuanto el servidor real lo puebla, React tira "Objects are not valid as a
React child" y la página entera queda en negro, sin *error boundary* que
lo atrape. Reproducido a propósito: `POST /loans/7/autorizar-entrega` por
la API real y luego visitar su ficha — pantalla en negro, confirmado con
`page.on("pageerror")`. Arreglado a `.nombre` en ambos campos (mismo
patrón que `entregado_por`, que ya lo hacía bien un renglón arriba).

**Hallazgo 2.2 (el mock mentía, y por eso el 2.1 sobrevivió a I3/I4)**:
`mock/loans.js` ponía `entrega_autorizada_por = "Melisa Avendano"` y
`confirmada_por` igual — strings planos, no el objeto que exige el
contrato real. Corregido a `{ user_id: 4, nombre: "Melisa Avendano" }`
(mismo id que ya usa `entregado_por` en `prestamo_demo.json`).

**Hallazgo 2.3 (regresión propia, encontrada a tiempo) — `createLoan` del
mock rompió tras el fix 1.2 de este mismo paquete.** El lote 1 corrigió
`NuevoPrestamoPage.jsx` para mandar `responsable_user_id/nombre/email`
planos (lo que de verdad exige `LoanCreate`); el mock's `createLoan`
seguía leyendo `data.responsable` anidado — sin ese fix el mock nunca lo
notó, pero desde el lote 1 cualquier préstamo nuevo en modo mock quedaba
con `responsable: null` en silencio. Arreglado a leer las tres llaves
planas (con una rama de compatibilidad si algún día vuelve a llegar
anidado).

**Hallazgo 2.4 (severo) — "Continuar borrador" no hacía nada contra el
servidor real.** `fetchLoans({estado:"borrador", mios:true})` devuelve
`LoanRow` (sin `items[]`) — el mismo desfase fila-vs-ficha del hallazgo
del lote 1, esta vez en `reanudarBorrador()`, que hacía
`borrador.items.length` sobre una fila sin `items`. El *throw* pasa en un
manejador de evento (`onClick`), no en render, así que React no lo
muestra en ningún lado: el botón se veía normal, no hacía nada visible, y
`setBorradorPrevio(null)` (la línea que cierra la pantalla de "borrador
sin terminar") nunca se ejecutaba porque estaba *después* de la línea que
tronaba. Cualquier persona que cierre la pestaña a medio wizard y vuelva
se queda atascada para siempre en esa pantalla. Reproducido creando un
borrador real por API y dando clic en el botón: `pageerror` capturado
("Cannot read properties of undefined (reading 'length')"), pantalla sin
cambios. Arreglado pidiendo `fetchLoanById(borrador.id)` antes de
reanudar (mismo patrón que `ActivosPage`/`AprobacionesPage`, con estado
`reanudando` para el botón mientras carga).

**Hallazgo 2.5 (responsividad) — el stepper de 4 pasos desbordaba la
página completa a 390px.** Medido en el DOM, no solo por ojo:
`scrollWidth` 428px contra `clientWidth` 390px — la página entera
quedaba con scroll horizontal (viola la regla de 320px usable). Arreglado
escondiendo la etiqueta de texto de cada paso debajo de `sm:` (el círculo
numerado solo ya identifica el paso activo); confirmado `scrollWidth`
390 == `clientWidth` 390 tras el fix, sin cambio visible en desktop.

**Confirmado con datos reales (cierra sospechosos del paquete)**:
`estado_fisico`/`comentario_auditoria`/`fecha_auditoria` sí vienen del
servidor en `GET /equipment/` → **cierra B-I11 a favor del fixture**.
`disponible`/`tenedor_actual`/`fecha_regreso_esperada` correctos en la
fila de Inventario. Los 3 badges de la ficha (`estado`, `entrega
autorizada`, `atrasado`) son ortogonales de verdad — se armó un préstamo
con `fecha_regreso_esperada` pasada por API para forzar `atrasado:true` (
ningún dato sembrado lo traía) y el badge "ATRASADO 28D" se pintó en rojo,
independiente de los otros dos. Los 6 campos `null` de `CE-0007`
(`notas_responsiva`, `fecha_regreso_real`, `entrega_autorizada_por`,
`fecha_autorizacion_entrega`, `confirmada_por`, `fecha_confirmacion`)
confirmados pintando "—".

**No verificado**: paginación real con una segunda página — con 8 equipos
y hasta 6 préstamos reales en la base de prueba, ambos listados caben en
una sola página; la forma `{items, total}` con `limit`/`offset` está
confirmada por API, pero nunca se disparó un salto de página de verdad.

**Evidencia**: `npm run build` verde (mismo tamaño de bundle, sin cambio
real). Regresión completa: `equipos-errores.spec.js` 6/6,
`contrato-fixtures.spec.js` 6/6, `paridad-bodies-equipos.spec.js` 10/10,
y las 4 suites de Presupuestos 48/48 (`auth` 7/7, `presupuesto-flujo-
completo` 9/9, `gastos-generales` 9/9, `pantallas` 23/23) — sin
regresión tras los 5 hallazgos de este lote.

**Riesgo nuevo**: ninguno — los 5 hallazgos se arreglaron en este mismo
commit y quedaron cubiertos por la regresión existente; ninguno tiene
prueba automatizada propia todavía (quedan para I8 lote 4, que sí ejerce
la UI real de punta a punta).

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

### ISSUE I5 — Permisos en la UI (cerrada, 1 commit)

`usePermisos()` lee `user.permisos` de `useAuth()` (AuthContext, sin fetch
propio) y deriva `permisos` efectivos: si vienen con contenido, se usan tal
cual; si vienen ausentes o vacios (`{}`, el default del contrato para no
romper nada existente), se deriva del rol base via `fallbackPorRol.js`
**temporal** — nunca de los paquetes aditivos (`APROBADOR_EQUIPO`,
`CUSTODIO_EQUIPO`, `AUDITOR`), que sin `permisos` explicito simplemente no
se pintan. `puede(modulo, accion)` es deny-by-default incluso contra el
propio catalogo: una clave que ya no existe ahi no puede otorgar acceso a
nada aunque el paquete del usuario la listara antes.

`RequierePermiso` en dos modos (`ui`: renderiza `children` o `fallback`;
`ruta`: redirige a `/403`), sin duplicar `ProtectedRoute` de Presupuestos
(ese resuelve sesion/rol; este resuelve `(modulo, accion)` sobre una sesion
que ya existe).

**Bug real encontrado y arreglado en el camino** (por eso las primeras
capturas de verificacion salieron mal y hubo que repetirlas): el modo
diagnostico llamaba `advertirClaveDesconocida()` **antes** de comprobar si
la clave existia en el catalogo, asi que avisaba "clave desconocida" en
**cada** llamada a `puede()`, existiera o no la clave — probado en vivo:
`equipos_prestamos:solicitar` y `equipos_aprobacion:autorizar_entrega`
(ambas claves reales del contrato) salian marcadas como desconocidas.
Arreglado moviendo el aviso DENTRO del `if (!accionExiste(...))`. Verificado
de nuevo: solo la clave inventada a proposito (`teletransportar`) dispara el
aviso.

**Segundo hallazgo real**: la demo de "503 no es 403" llamaba
`loansApi.fetchLoans()` con `PERMISOS_NO_DISPONIBLES` inyectado, pero
`fetchLoans` (I3) solo respetaba la inyeccion global de `SIN_PERMISO` — el
503 nunca se disparaba, la llamada respondia `{ok:true}`. Causa: al
construir el mock en I3 solo cablee `PERMISOS_NO_DISPONIBLES` en
`permisos.js` (catalogo/auth_me), asumiendo que era especifico de
"resolver permisos" como concepto aislado. Releyendo el contrato: es un
fallo general de la capa de autorizacion (igual que `SIN_PERMISO`), no
acotado a un endpoint. Arreglado ampliando `checkGlobalInjection` para
cubrir ambos codigos — verificado que esto no rompio los 5 codigos del
harness de I3 (se re-corrio completo, sin regresion).

**Evidencia**

Capturas reales en `C:\dev\prompts-interfaz\respaldos\I5\` (via
`PermisosDemo.jsx`, usando `userOverride` de `usePermisos` para simular los
3 roles sin necesitar 3 sesiones reales con esos permisos exactos):

- `colaborador_mkt`: Solicitar=Visible, Ver global=Oculto, Autorizar=Oculto.
- `colaborador_mkt` + `APROBADOR_EQUIPO`: las 3 Visible.
- `admin`: Solicitar=Visible, Ver global=Visible, Autorizar=Oculto (admin
  base **nunca** tiene `equipos_aprobacion`, ni por fallback).
- 503: `{status:503, codigo:"PERMISOS_NO_DISPONIBLES", message:"No se
  pudieron resolver los permisos. Reintenta en un momento."}` mostrado via
  Toast, **sin** redireccion a `/login` ni a `/403`.
- Consola: `[permisos] clave desconocida: equipos_prestamos:teletransportar`
  — una sola vez, nada mas.

```
npm run build verde. Sin cambio de peso: index-*.js 14.88 kB gz, CSS 6.89
kB gz — igual que I2/I3. dist/ sigue en 25 archivos JS, grep confirma cero
rastro de PermisosDemo/fallbackPorRol/claves del catalogo.
```

Los 3 e2e de Presupuestos (uvicorn reiniciado + DB fresca entre cada uno):
`auth.spec.js` 7/7, `presupuesto-flujo-completo.spec.js` 9/9,
`gastos-generales.spec.js` 9/9 — sin tocar `src/modules/presupuestos/` ni
`src/context/`. Mas `pantallas.spec.js` 23/23 y `contrato-fixtures.spec.js`
6/6 (29/29 en la misma invocacion).

**No verificado en pantalla real**: Playwright headless otra vez. Tampoco
se probo `usePermisos` contra un `/auth/me` real que ya mande `permisos`
con contenido (WP1 no ha aterrizado) — solo contra el fallback por rol y
contra usuarios sinteticos via `userOverride`.

**Riesgo nuevo**: ninguno nuevo con numero propio — los dos bugs de arriba
se encontraron y arreglaron el mismo dia, dentro del mismo commit, sin
quedar expuestos en ninguna captura de cierre.

### ISSUE I6 — e2e de Equipos + B-I06 (cerrada, 1 commit)

`e2e/helpers/imagen.mjs`: PNG real construido a mano vía `node:zlib`
(firma + IHDR + IDAT comprimido con `deflateSync` + IEND, con CRC32 propio
— tabla estándar IEEE 802.3/Anexo D de la spec PNG). **Verificado con
round-trip real**, no solo "parece un PNG": `zlib.inflateSync` del IDAT y
lectura del primer píxel confirma que decodifica exactamente al color
pedido. `fotoGrande()` usa **ruido** por píxel, no un color sólido — un
color sólido comprime a unos cuantos KB sin importar el tamaño del lienzo
(deflate ama la repetición) y jamás dispararía el límite real de 3 MB;
medido: 3,782,118 bytes, por encima del límite. `firmaPng()` medido en 414
bytes, bajo 250 KB. `jpegReal()` con magic bytes reales.

`e2e/helpers/sesiones.mjs`: un login por persona, `storageState` cacheado
por usuario — mismo patrón que `pantallas.spec.js` pero como helper
reusable por cualquier spec futuro.

**`equipos-flujo-completo.spec.js`** (10 pasos, `test.fixme` con motivo y
condición de despertar escritos en la primera línea del describe):
escribirlo contra `API_EQUIPOS_v1.md` de punta a punta encontró el
**entregable más valioso del paquete** — un patrón de huecos del contrato,
no un caso aislado: el contrato ejemplifica con JSON completo la
*respuesta* de `GET /loans/{id}` y el *body* de `/confirmar-devolucion`,
pero nunca los bodies de `POST /loans/`, `POST /loans/{id}/items` ni
`POST /loans/{id}/autorizar-entrega`. R-I13 (de I3, sobre `/devolucion`)
era el primer síntoma; esto confirma que es sistemático. Documentado como
**R-I14** en `docs/riesgos/interfaz.md` con la pregunta concreta para el
carril de servidor, y anotado directo en `real/loans.js` (I3) para que
quien lo lea sepa que esos nombres de campo son una asunción, no un hecho
confirmado.

**`equipos-errores.spec.js`** (los 5 códigos feos, corre HOY): usa
`DevMockHarness.jsx` (I3) como "UI" de prueba — es lo único que hoy
reacciona visiblemente a estos códigos, ya que I4 (las 7 vistas reales)
no existe todavía. Lee el bloque "Último resultado" del harness (JSON
crudo con `status`/`codigo`/`message`) en vez de parsear el texto del
Toast, más frágil. Para el caso 503 confirma **explícitamente** que la
página no redirige a `/login` — la regla dura de que un 503 nunca
desloguea, verificada por assertion, no solo inferida.

**B-I06 (semilla de demo reusable)**: `e2e/helpers/sembrar-demo.mjs`
generaliza el bootstrap que vivía hardcodeado dentro de
`pantallas.spec.js` — ahora acepta cuántos creadores/marcas/tickets, con
sufijo por corrida (no choca con datos de una corrida anterior), solo por
la API real. `pantallas.spec.js` fue refactorizado para consumirlo:
**sigue en 23/23** (no bajó del número anterior a este refactor).

**Evidencia**

```
npm run build verde, byte-idéntico al de I5 (index-*.js y CSS con el
MISMO hash de contenido: I6 no tocó ni un archivo de frontend/src/, solo
frontend/e2e/).
```

Batería completa, cada uno con DB propia recién sembrada y uvicorn
reiniciado entre archivos (rate limit 30/15min):

| Spec | Resultado |
|---|---|
| `auth.spec.js` | 7/7 |
| `presupuesto-flujo-completo.spec.js` | 9/9 |
| `gastos-generales.spec.js` | 9/9 |
| `pantallas.spec.js` | 23/23 |
| `contrato-fixtures.spec.js` | 6/6 |
| `equipos-errores.spec.js` (con `VITE_EQUIPOS_MOCK=1`) | 6/6 |
| `equipos-flujo-completo.spec.js` | 8 fixme (skip confirmado, no ejecuta) |

**No verificado en pantalla real**: Playwright headless. El flujo completo
de `equipos-flujo-completo.spec.js` no se verificó contra NADA real (ni
UI ni servidor) — es aspiracional por diseño, a la espera de I4 y del
servidor.

**Riesgo nuevo**: R-I14 (bodies de escritura sin ejemplo en el contrato,
patrón detrás de R-I13 — ver arriba y `docs/riesgos/interfaz.md`).

### ISSUE I4 — Módulo Equipos, 7 sub-commits (I4a..I4g)

#### Commit I4a — Rutas, esqueleto y vista Inicio (cerrado)

`frontend/src/shell/navItems.js`: se quita `disabled: true` del tab
"Equipos" (I1/I2 lo dejaron deshabilitado a propósito hasta que hubiera
algo detrás). `App.jsx`: 7 rutas nuevas bajo `/equipos` (`EquiposLayout`
como layout route, hijas con `React.lazy`: `/equipos` (Inicio),
`/inventario`, `/nuevo`, `/activos`, `/aprobaciones`, `/historial`,
`/prestamo/:folio`) — declaradas como hermanas de `/*` (PresupuestosLayout);
React Router v6 rankea por especificidad de segmento, no por orden de
declaración, así que un path estático (`/equipos`) siempre gana sobre el
wildcard sin importar dónde se escriba (mismo patrón ya probado por las
rutas dev de I3/I5). `EquiposLayout.jsx` (chrome: `EquiposSubNav` +
`Outlet`, `pt-16` para no chocar con el GlassNav de módulos del shell) y
`EquiposSubNav.jsx` (filtra las 6 pestañas por `usePermisos().puede(...)`,
oculta las que el rol no tiene — la UI solo pinta, cada endpoint valida su
propio permiso).

**Vista real: `InicioPage.jsx`** — `fetchEquipmentDashboard()` +
`KpiTile` x4 (Prestados/Disponibles planos, Atrasados/Pend. confirmación
con `glass`) + `StatusDonut` con leyenda por `estado` + lista "Requiere
atención" enlazando a `/equipos/prestamo/{folio}`. Estados explícitos:
loading (`SkeletonShimmer` x4), `PERMISOS_NO_DISPONIBLES` (503, UI de
reintento — nunca "sin acceso", nunca desloguea), error genérico, vacío.
Las otras 6 páginas son placeholder (`EmptyState` con "Este módulo se
construye en I4x") — I4a es el esqueleto de rutas, no las 7 vistas.

**Bug real encontrado — `npm run build` rojo de fábrica.**
`src/modules/equipos/api/real/loans.js` y `real/media.js` (I3) importan
`BASE` y `throwApiError` desde `@/api`, pero `src/api/index.js` (I3) los
importaba de `./client` para uso interno y nunca los re-exportaba en su
`export { ... }` — nadie lo notó en I3/I5/I6 porque nada consumía esos dos
nombres desde `@/api` hasta que I4a conectó `real/*.js` al árbol de build
real (antes solo lo tocaba el harness dev, fuera del grafo de producción).
Un solo `export` con dos nombres agregados, cero cambio de comportamiento.

**Bug real encontrado — subnav ilegible en 390px.** `GlassNav` (I1) está
pensado para 2 pastillas (tabs de módulo); `EquiposSubNav` le mete 6. Sin
manejo de overflow, `justify-center` recortaba la mitad de las pestañas
fuera del viewport en móvil — "Inicio" (la pestaña activa, la que carga por
default) quedaba completamente invisible y sin forma de llegar a ella
(no hay scroll, solo clipping). Mismo patrón que las tablas con overflow
horizontal: envuelto en `go-table-scroll-wrapper` (fade a la derecha) +
`overflow-x-auto go-table-scroll` en el contenedor real. Verificado en
pantalla real a 390x844: "Inicio" visible y activo, el resto alcanzable
con scroll horizontal.

**Evidencia**

```
npm run build verde. index-*.js sube de 14.88 a 16.31 kB gz (rutas +
EquiposSubNav + catálogo de permisos entran al chunk eager de App.jsx,
igual que PresupuestosLayout ya lo hacía) — CSS 6.89 -> 6.95 kB gz. Payload
real de /login: 16.31 + 52.97 (react-vendor) + 45.03 (motion) + 1.10
(LoginPage) + 6.95 (CSS) = 122.36 kB gz, contra el techo de 250 (anterior:
~120.87 kB gz). dist/ grep confirma cero rastro de PermisosDemo/
DevMockHarness/fallbackPorRol/mock — el chunk de mocks sigue sin entrar a
producción.
```

Los 4 e2e de Presupuestos (uvicorn reiniciado + DB fresca antes de cada
uno, por tocar `App.jsx` y `src/api/index.js`, archivos compartidos):
`auth.spec.js` 7/7, `presupuesto-flujo-completo.spec.js` 9/9,
`gastos-generales.spec.js` 9/9, `pantallas.spec.js` 23/23 (48/48 total).

Capturas reales (`VITE_EQUIPOS_MOCK=1`, sesión de superadmin, datos del
fixture de mock) en 1280x800 y 390x844 de `/equipos` (Inicio con KPIs y
donut reales) y de una página placeholder (`/equipos/prestamo/PR-0001` →
"Ficha de préstamo"), más las 7 rutas navegadas sin crash. Guardadas en
scratchpad de la sesión.

**No verificado en pantalla real**: las 6 páginas placeholder son
`EmptyState` sin lógica — no hay nada que verificar hasta I4b-g. Tampoco se
probó `InicioPage` contra el backend real de Equipos (no existe todavía;
solo contra el mock del contrato).

**Riesgo nuevo**: ninguno con número propio — los dos bugs de arriba se
encontraron y arreglaron el mismo commit.

#### Commit I4b — Inventario (cerrado)

`GET /api/equipment/` con `q`, `categoria`, `condicion`, `disponible`,
`limit`/`offset` (20 por página) — **filtros en la URL** vía
`useSearchParams` (`useUrlFilters()`), no en estado local: un F5 o un link
compartido conserva la búsqueda. El input de texto (`q`) es el único filtro
que dispara una petición por tecleo, así que corre con debounce de 300ms
sobre un estado local (`qInput`); los selects sincronizan de inmediato
porque son una acción deliberada, no tecleo continuo. Las opciones del
select de categoría se aprenden de una llamada propia con `limit=200` (no
hay enum de categorías en el contrato, es texto libre — inventarlo habría
sido "improvisar un adaptador").

**`EquipmentCard.jsx`** (rejilla) con **tilt 3D condicionado**: el chequeo
`matchMedia("(hover: hover) and (pointer: fine)")` corre una sola vez al
montar el módulo (el tipo de dispositivo no cambia a media sesión) y en
táctil el componente **ni siquiera monta** los listeners de `mousemove`
— no es solo esconder el efecto con CSS, es no pagar su costo. Alternativa
de **tabla** (`go-table-scroll-wrapper`/`go-table-scroll`, cero cristal en
filas) con `RowActions` (Ver ficha/Editar/Auditar) por renglón.

**Separación real del contrato, no una decisión de UI**: `editar`
(metadata: nombre, categoría, marca, modelo, número de serie, activo fijo,
cuenta de Gmail, espacio disponible, accesorios) y `auditar_condicion`
(condición, estado físico, comentario) son dos permisos distintos en
`permisos_catalogo.json` → dos modales distintos
(`EquipmentFormModal.jsx`, `EquipmentAuditModal.jsx`), cada uno detrás de
su propio `RequierePermiso`. La fecha de auditoría **no se manda desde el
cliente** — mismo patrón que `atrasado`/`dias_atraso`: la pone el servidor
(el mock ya lo hace, `fecha_auditoria: data.fecha_auditoria ?? ...`).
`estado_fisico`/`comentario_auditoria`/`fecha_auditoria` se pintan **solo
si vienen** en la ficha (R-I10: no están en el contrato congelado, solo en
el fixture).

`EquipmentFichaModal.jsx`: `GET /api/equipment/{id}` fresco al abrir (no
reusa la fila del listado, para que una auditoría recién guardada se
refleje sin recargar toda la página). Acción **"Dar de baja"** con
`POST /baja` — el **409 `EQUIPO_OCUPADO`** se pinta con `e.detail` del
servidor tal cual, en un toast, nunca con un texto propio que pueda
desalinearse de la regla real del servidor.

**Bug de doc encontrado (mismo patrón que R-I03)**: `CLAUDE.md` dice que
`RowActions` vive en `frontend/src/components/RowActions.jsx`; el archivo
real quedó en `frontend/src/modules/presupuestos/components/
RowActions.jsx` desde la costura de I0 (`d602e00`, el mismo commit que
también dejó vieja la ruta de `useMobile.js`). Anotado como continuación
de R-I03 en `docs/riesgos/interfaz.md` — no me toca editar `CLAUDE.md`.

Autoverificación de la regla dura del paquete: `grep -rn "new Date(" src/modules/equipos/`
solo encuentra los tres usos ya existentes dentro de `api/mock/*.js`
(simulan al SERVIDOR estampando fechas, igual que haría el backend real) —
cero apariciones nuevas en código de UI de I4b.

**Evidencia**

```
npm run build verde. index-*.js 16.31 -> 16.63 kB gz, CSS 6.95 -> 6.99 kB
gz (clases de Tailwind nuevas, sin sorpresas). Payload de /login: 122.72
kB gz (anterior: 122.36 kB gz), contra el techo de 250.
InventarioPage-*.js (chunk lazy, no entra al payload de /login): 22.26 kB
/ 6.01 kB gz. dist/ grep sigue sin rastro de mock/harness/permisos-demo.
```

Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48). Verificado en pantalla real
(`VITE_EQUIPOS_MOCK=1`, 1280x800 y 390x844): rejilla con datos del
fixture, cambio a vista de tabla, filtro por categoría + búsqueda con
debounce (confirmado en la URL), ficha con los 3 badges + auditoría
previa, modal de auditoría pre-poblado con los valores actuales, alta de
un equipo nuevo que aparece de inmediato en el conteo (8 → 9) sin recargar
la página.

**No verificado en pantalla real**: `POST /baja` con 409 `EQUIPO_OCUPADO`
(el fixture no trae, hoy, un equipo activo con préstamo abierto a la vez
que se pueda dar de baja desde Inventario sin antes construir I4c/I4d;
queda para cuando exista un préstamo real que ocupe un equipo). Filtro
`condicion` en pantalla real (probado categoría y búsqueda, no condición,
mismo mecanismo).

**Riesgo nuevo**: ninguno con número propio — la actualización de
`RowActions.jsx` se agregó como continuación de R-I03 (mismo commit que lo
originó, `d602e00`), no como un riesgo nuevo.

#### Commit I4c — Nuevo préstamo: wizard de 4 pasos (cerrado)

El sub-paquete más delicado del paquete, tal como lo marcaba
`06-I4-modulo-equipos.md`. 4 pasos — **Datos → Equipos → Fotos → Firmas**
— sobre `/equipos/nuevo`, contra el mock de I3 (`VITE_EQUIPOS_MOCK=1`).

**Componentes nuevos** (`src/modules/equipos/components/`):
`SignaturePad.jsx` (canvas + Pointer Events, escalado por
`devicePixelRatio`, deshacer por trazo completo, detección de vacío real
por diagonal del bounding box de los trazos — un tap no pasa como firma;
API imperativa `ref.getBlob()`/`ref.isEmpty()`, nunca base64 en el estado,
exporta PNG y rechaza si pasa de 250 KB); `PhotoCapture.jsx`
(`capture="environment"`, compresión en cliente a 900px/calidad 0.72 vía
canvas, preview con `URL.createObjectURL`, reintento por foto sin
re-pedir el archivo, rechaza si sigue pasando de 3 MB tras comprimir);
`AccesoriosPicker.jsx` (checkboxes de `accesorios_tipicos` + libre +
`cargador_con` obligatorio solo si el equipo declara "cargador").

**Responsable no es un campo libre**: el contrato exige `user_id` real
(`fixtures/prestamo_demo.json` lo confirma: `{user_id, nombre, email}`) y
no hay ningún endpoint de búsqueda de usuarios en el contrato de Equipos
— se auto-llena con la sesión actual (`useAuth().user`), de solo lectura
en el paso 1. Improvisar un buscador de usuarios habría sido inventar un
endpoint que no existe.

**Decisión de diseño reportada, no adivinada**: el contrato solo tiene
`POST /loans/{id}/items` para dar de alta un equipo — no existe un
endpoint para *editar* accesorios después. El prompt describe "paso 2:
equipos" y "paso 3: accesorios" como si fueran llamadas separadas, pero
eso exigiría un endpoint de actualización que el contrato no tiene. Se
resolvió combinando la selección del equipo y sus accesorios en una sola
interacción del paso 2 (se abre un panel de accesorios inline al elegir
un equipo; "Confirmar" dispara un único `POST /items` con todo junto) —
el paso 3 queda exclusivamente para fotos, que sí dependen de que el ítem
ya exista (`loan_item_id`). Mismo comportamiento observable que pedía el
prompt (409 `EQUIPO_OCUPADO` se maneja ahí, no se pierde la selección
previa), sin inventar un PUT que no está en `API_EQUIPOS_v1.md`.

**Recuperación de borrador**: `GET /loans/?estado=borrador&mios=1` al
entrar a `/equipos/nuevo`; si hay uno, se ofrece continuar (salta al paso
correcto según qué le falta) o descartar (`cancelLoan` + empezar limpio).
El mock ignora `mios` (I3 ya lo dejó anotado como decisión de I4) — en
desarrollo solo hay un borrador a la vez, así que no hay ambigüedad
práctica; documentado como limitación conocida, no oculta.

**401 a mitad del wizard**: se prueba con el conmutador de I3
(`SESION_EXPIRADA`). Un helper (`conManejoDeSesion`) envuelve cada llamada
que muta: si `e.status === 401`, llama `useAuth().logout()` (mismo camino
que un 401 real de `fetchWithAuthRetry`) y deja que `ProtectedRoute`
mande a `/login` — el borrador y las fotos ya subidas siguen en el
servidor (mock o real), se recuperan al volver a entrar.

**Tres bugs reales encontrados y arreglados, los tres por la misma causa
raíz**: el mock (I3) devuelve **referencias vivas** a su estado interno en
vez de copias — ningún backend real hace esto (cada respuesta HTTP es una
deserialización fresca), pero nadie lo había notado porque I4a/I4b nunca
mutaban un objeto y luego lo re-leían en el mismo flujo.

1. `mock/media.js`: `uploadMedia()` guardaba el archivo pero **nunca
   adjuntaba el `mediaId` al ítem/firma del préstamo** — esa mitad del
   contrato vivía huérfana en una función `addLoanMedia` de `mock/loans.js`
   que ningún dispatcher exponía (verificado con grep: cero referencias en
   todo el repo). Contra el mock, ningún préstamo podía llegar nunca a
   `confirmar` — `confirmLoan` exige fotos y firmas que jamás quedaban
   registradas. Arreglado adjuntando inline dentro de `uploadMedia`
   (mismo contrato atómico que `real/media.js`: un solo POST multipart
   sube Y adjunta), y se borró `addLoanMedia` por muerto. De paso se
   preservó ahí el `checkInjection("SESION_EXPIRADA")` que antes vivía en
   la función huérfana.
2. Mi propio código: tras un `addLoanItem` exitoso, yo hacía
   `setLoan(prev => ({...prev, items: [...prev.items, item]}))` — pero el
   mock YA había empujado ese mismo `item` al array que `prev.items`
   referenciaba (la misma referencia viva), así que mi `[...prev.items,
   item]` lo duplicaba. Verificado en pantalla real: un solo "+ Agregar"
   dejaba DOS renglones idénticos en "En este préstamo" (React además
   avisaba con "two children with the same key"). Arreglado: en vez de
   reconstruir el array a mano, el wizard ahora refresca con
   `fetchLoanById(loan.id)` después de cada mutación (agregar/quitar
   ítem, subir foto) — más robusto también contra un backend real, donde
   la fuente de verdad siempre es el servidor.
3. Con el fix anterior aplicado, apareció un tercer síntoma de la MISMA
   causa: el botón "Siguiente" del paso 3 nunca se habilitaba aunque las
   dos fotos ya se hubieran subido (confirmado con `PhotoCapture`
   mostrando "Reemplazar foto" en ambas, o sea que sí subieron). Causa:
   `fetchLoanById` devolvía la MISMA referencia de objeto en cada llamada
   (mutada en el sitio), así que el segundo `setLoan(fresh)` recibía un
   valor **idéntico por referencia** al estado actual — React usa
   `Object.is` para decidir si re-renderiza y, al ser la misma identidad,
   se lo saltaba en silencio. La UI de `PhotoCapture` (estado local,
   genuinamente nuevo en cada `setState`) sí se actualizaba; la del
   wizard padre, no. **Arreglo de raíz, no un parche por función**: se
   exportó `clone()` de `state.js` y se aplicó en la frontera pública de
   **cada** función exportada de `mock/loans.js` que devuelve un préstamo
   o ítem (`fetchLoans`, `fetchLoanById`, `fetchLoanByFolio`, `createLoan`,
   `addLoanItem`, `confirmLoan`, `cancelLoan`, `returnLoan`,
   `authorizeDelivery`, `confirmReturnDecision`, `closeIncident`) —
   nunca dentro del helper interno `findLoan` (ese sigue devolviendo la
   referencia viva a propósito: el resto de esas mismas funciones la usan
   para mutar `state.loans` antes de clonar al final). Esto deja al mock
   comportándose como un backend real para **todo** el módulo de
   préstamos, no solo para el wizard — I4d-g heredan la corrección sin
   tener que recordar "usar fetchLoanById en vez de anexar a mano".

**Evidencia**

```
npm run build verde. index-*.js 16.63 -> 16.64 kB gz, CSS 6.99 -> 7.06 kB
gz. Payload de /login: 122.80 kB gz (anterior: 122.72 kB gz), contra el
techo de 250. NuevoPrestamoPage-*.js (chunk lazy): 17.68 kB / 5.50 kB gz.
dist/ grep sigue sin rastro de mock/harness/permisos-demo — los cambios
de mock/loans.js y mock/media.js son código muerto en producción, como
todo el resto del mock.
```

Flujo completo verificado en pantalla real (`VITE_EQUIPOS_MOCK=1`,
1280x800, superadmin): paso 1 con responsable de solo lectura desde la
sesión; paso 2 agrega un equipo con sus accesorios en una sola
interacción (409 `EQUIPO_OCUPADO` deja el resto de la selección intacta,
solo se probó por code review — el fixture no trae hoy un segundo usuario
compitiendo por el mismo equipo); paso 3 con 2 fotos subidas y el botón
"Siguiente" habilitándose correctamente tras el fix del bug #3; paso 4
con las 2 firmas capturadas (detección de vacío real, no solo "¿hubo
click?"); `confirmar` genera folio real (`CE-0008`) y navega a
`/equipos/prestamo/{folio}`.

Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48). Además, re-verificados tras los tres
fixes al mock: `contrato-fixtures.spec.js` 6/6 y `equipos-errores.spec.js`
6/6 (los cinco códigos feos, incluida la propia inyección
`SESION_EXPIRADA` cuya lógica se movió de `addLoanMedia` a `uploadMedia`)
— sin regresión.

**No verificado en pantalla real**: 409 `EQUIPO_OCUPADO` en el paso 2 (el
fixture no trae hoy dos usuarios compitiendo por el mismo equipo en
simultáneo — revisado por lectura de código, no por clic); el 401 a
mitad del wizard con el conmutador del mock (la lógica se comparte con
`equipos-errores.spec.js`, que sí lo prueba contra `confirmLoan`, pero no
se repitió manualmente dentro del wizard real); recuperación de un
borrador huérfano tras cerrar la pestaña (probado por lectura de código:
`fetchLoans({estado:"borrador"})` + salto de paso, no con una sesión de
navegador cerrada y reabierta de verdad).

**Riesgo nuevo**: ninguno con número propio — los tres bugs se
encontraron y arreglaron dentro de este mismo commit. El límite de
`mios` sin resolver en el mock (heredado de I3) queda anotado arriba como
limitación conocida, no como riesgo nuevo (ya estaba documentado en
`mock/loans.js` desde I3).

#### Commit I4d — Préstamos activos (cerrado)

`GET /api/loans/` — el contrato solo acepta **un** `estado` a la vez, pero
"Activos" es la unión de tres (`prestado`, `pendiente_confirmacion`,
`incompleto`): se trae una página razonable (`limit=200`) y se filtra en
el cliente, en vez de inventar un parámetro multivalor que el contrato no
tiene. El dropdown de estado sí reduce a uno solo cuando la persona lo usa
(mismo filtrado, sin round-trip extra). Tabla (`go-table-scroll-wrapper`,
cero cristal): folio (enlaza a la ficha), responsable, equipos, fecha de
regreso esperada, y los **tres badges ortogonales** por separado —
`estado`, `atrasado`+`dias_atraso` (del servidor, nunca derivado) y
`entrega_autorizada` (el demo `CE-0007` los muestra los tres a la vez:
"Prestado" + "Entrega no autorizada", sin fusionarlos en uno). Acciones
con `RowActions`: Ver ficha, Ver responsiva, Registrar devolución.

**"Ver responsiva" es un endpoint autenticado, no un mount estático**
(hallazgo 3 del plan fue un IDOR real en este mismo repo) — mismo patrón
ya usado en Presupuestos (`ticketFileUrl`, `generalExpenseFileUrl`):
`loanResponsivaUrl(loanId)` es async (el dispatcher mock/real lo envuelve
igual que `mediaUrl`), se resuelve antes de abrir la pestaña
(`window.open`), nunca se renderiza en un `href` sin await primero — el
mismo descuido que se corrigió en I4c (`PhotoCapture`) para no repetirlo
aquí.

**`RegistrarDevolucionModal.jsx`** (nuevo, reutiliza `PhotoCapture` de
I4c): por cada equipo, 2 fotos de devolución **o** "No devuelto" con nota
obligatoria — el botón de enviar queda deshabilitado hasta que **todos**
los equipos del préstamo estén resueltos de una forma u otra (nunca se
puede enviar a medias). Las fotos usan el mismo contrato atómico de
`uploadMedia` (sube y adjunta en una sola llamada) que ya se corrigió en
el mock durante I4c — este commit no tuvo que tocar el mock de nuevo,
señal de que el arreglo de raíz de I4c efectivamente sostiene al resto
del módulo.

**Evidencia**

```
npm run build verde. index-*.js 16.64 -> 16.68 kB gz, CSS 7.06 -> 7.07 kB
gz. Payload de /login: 122.85 kB gz (anterior: 122.80 kB gz), contra el
techo de 250. PhotoCapture pasó a ser un chunk compartido entre
NuevoPrestamoPage y RegistrarDevolucionModal (Rollup lo extrajo solo, sin
pedírselo) — NuevoPrestamoPage-*.js bajó de 17.68 a 15.17 kB gz.
ActivosPage-*.js (chunk lazy): 8.40 kB / 3.15 kB gz. dist/ grep sigue sin
rastro de mock/harness/permisos-demo.
```

Verificado en pantalla real (`VITE_EQUIPOS_MOCK=1`, 1280x800 y 390x844,
superadmin) contra el préstamo demo `CE-0007` (ya `prestado` en el
fixture): tabla con los 3 badges correctos; modal de devolución con las 2
fotos subidas y el botón habilitándose correctamente; tras registrar la
devolución, el renglón pasa a "Pend. confirmación" y pierde la acción
"Registrar devolución" (ya no aplica), con toast de éxito. En 390x844 la
tabla desborda horizontalmente por diseño (mismo patrón ya aceptado de
Presupuestos: `go-table-scroll-wrapper` con scroll, no colapso de
columnas).

Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48).

**No verificado en pantalla real**: el filtro de "Estado" (dropdown) solo
se probó por code review, no con un clic — el fixture demo solo trae un
préstamo activo, no hay un segundo estado con el que comparar visualmente
el filtro en acción.

**Riesgo nuevo**: ninguno.

#### Commit I4e — Aprobaciones (cerrado)

Tres colas **separadas**, cada una detrás de su propio permiso
(`equipos_aprobacion:autorizar_entrega`/`:confirmar_devolucion`/
`:cerrar_incidencia`) — mezclarlas en una sola tabla habría escondido que
el contrato (§4) las trata como tres acciones y tres permisos distintos:

- **Autorizaciones de entrega**: `!entrega_autorizada` sobre cualquier
  estado no terminal (ni `borrador` ni `cancelado`) — no solo `prestado`,
  porque el mock no impide que un préstamo llegue a `pendiente_confirmacion`
  sin autorización previa (confirmado leyendo `confirmLoan`: no valida
  `entrega_autorizada`), así que un préstamo puede necesitar autorización
  retroactiva estando ya en cualquiera de los dos estados.
- **Devoluciones por confirmar**: `estado === "pendiente_confirmacion"`.
  **Regla dura verificada en pantalla real, no solo leída**: un préstamo
  con `entrega_autorizada:false` nunca puede llegar a `completado` (409
  `TRANSICION_INVALIDA`) — `ConfirmarDevolucionModal.jsx` lo explica
  **antes** de intentarlo (mensaje de bloqueo en vez del formulario de
  decisiones), no después de un error del servidor.
- **Incidencias abiertas**: `estado === "incompleto"`. Cerrar con nota
  obligatoria regresa los equipos de "revisión" a "activo" — sin esto,
  `incompleto` es terminal y el equipo queda varado en revisión para
  siempre (hallazgo 12 del plan).

**Componentes nuevos**: `ConfirmarDevolucionModal.jsx` (una decisión
`ok|dañado|faltante` por equipo, nota obligatoria si no es `ok`, y el
bloqueo de `entrega_autorizada` de arriba); `CerrarIncidenciaModal.jsx`
(nota obligatoria).

**Evidencia**

```
npm run build verde. index-*.js 16.68 -> 16.69 kB gz, CSS sin cambio
(7.07 kB gz). Payload de /login: 122.86 kB gz (anterior: 122.85 kB gz),
contra el techo de 250. AprobacionesPage-*.js (chunk lazy): 9.10 kB /
2.63 kB gz. dist/ grep sigue sin rastro de mock/harness/permisos-demo.
```

**Verificado en pantalla real de punta a punta** contra el préstamo demo
`CE-0007` (`VITE_EQUIPOS_MOCK=1`, 1280x800 y 390x844): se registró su
devolución (I4d) SIN autorizar antes la entrega, dejándolo exactamente en
el estado límite que el prompt pedía cubrir — `pendiente_confirmacion` +
`entrega_autorizada:false`. Confirmado: aparece en ambas colas
("Autorizaciones" y "Devoluciones") a la vez; intentar "Confirmar
devolución" en ese momento muestra el mensaje de bloqueo, no el
formulario; tras "Autorizar entrega" la cola de autorizaciones baja a 0;
tras "Confirmar devolución" (todo `ok`) la cola de devoluciones baja a 0 —
el préstamo pasó a `completado`. Historial de toasts capturado en pantalla
mostrando la secuencia completa: "Devolución registrada" →
"Entrega autorizada — CE-0007" → "Devolución confirmada".

Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48).

**No verificado en pantalla real**: la cola de "Incidencias abiertas"
(el fixture no trae hoy un préstamo `incompleto` — para generarlo hay que
confirmar una devolución con alguna decisión distinta de `ok`, lo cual
consumiría el único préstamo demo disponible antes de poder probar
también el camino feliz; revisado por lectura de código: mismo patrón de
modal con nota obligatoria que `RegistrarDevolucionModal`, ya verificado
en I4d).

**Riesgo nuevo**: ninguno.

#### Commit I4f — Historial (cerrado)

Filtros por estado (los 6 del contrato, no solo los "activos" de I4d),
persona/folio/motivo (`q`) y rango de fechas (`desde`/`hasta`), paginado —
la primera vista del módulo que usa `GET /api/loans/` con **todos** sus
parámetros documentados, sin necesitar el rodeo de filtrar en cliente que
usaron I4d/I4e (ahí la unión de varios estados no tenía forma de pedirse
en una sola llamada; aquí cada filtro es independiente y sí calza en el
querystring tal cual).

**Dos bugs reales de I3 encontrados al conectar esto, arreglados en el
mismo commit** (mismo patrón que I4c: código escrito pero nunca
terminado de cablear):

1. **`desde`/`hasta` no existían en el mock.** `real/loans.js` ya los
   mandaba en el querystring desde I3, pero `mock/loans.js` los
   ignoraba silenciosamente (no estaban ni en la firma de la función). El
   contrato tampoco dice contra qué campo de fecha filtran — se decidió
   `fecha_entrega` (cuándo arrancó el préstamo de verdad, no cuándo se
   creó el borrador) y se documentó la decisión en el propio código; un
   préstamo sin `fecha_entrega` (`borrador`/`cancelado` antes de
   confirmar) no matchea ningún rango. Comparación de strings
   `"YYYY-MM-DD"` en vez de `new Date()` — el orden lexicográfico de ese
   formato ya es cronológico, sin el riesgo de zona horaria que prohíbe
   la regla dura del módulo.
2. **`fetchLoansExport` no estaba conectada a nada.** Vivía únicamente en
   `real/loans.js`, nunca en el dispatcher público (`api/loans.js`, el
   único punto por el que el resto del módulo debe importar) ni en el
   mock — exactamente el mismo patrón de "escrito pero huérfano" que
   `addLoanMedia` en I4c. Peor: la implementación real usaba `request()`,
   que **siempre hace `res.json()`** — un CSV no es JSON; de haber
   quedado así, un 403/503 real habría intentado parsear el error como si
   fuera el archivo. Arreglado: `real/loans.js` ahora hace
   `fetch → blob → descarga` de verdad (mismo texto que pedía el prompt
   de I4f), lanza `ApiError` real si el servidor no responde 2xx; se
   agregó al dispatcher; y se escribió una implementación en el mock que
   arma el mismo `Blob` `text/csv` (mismas columnas, mismo filtrado que
   `fetchLoans`) para que ambos lados del dispatcher compartan
   exactamente el mismo contrato observable.

**Evidencia**

```
npm run build verde. index-*.js sin cambio (16.68 kB gz, HistorialPage es
un chunk lazy). CSS 7.07 -> 7.08 kB gz. Payload de /login: 122.86 kB gz,
igual que I4e, contra el techo de 250. HistorialPage-*.js (chunk lazy):
5.77 kB / 2.15 kB gz. dist/ grep sigue sin rastro de mock/harness/
permisos-demo.
```

Verificado en pantalla real (`VITE_EQUIPOS_MOCK=1`, 1280x800 y 390x844,
superadmin): filtro por estado "prestado" muestra el demo `CE-0007`;
filtro por "cancelado" muestra el estado vacío correcto ("Sin
resultados"); "Exportar CSV" descarga un archivo real (`prestamos.csv`,
2 líneas: encabezado + 1 fila) con las 8 columnas esperadas y sin
depender de ningún visor de PDF ni backend real para generarse.

Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48).

**No verificado en pantalla real**: el toast de error de "Exportar CSV"
ante un 403/503 real (el fixture actual no tiene forma de negarle
`equipos_prestamos:exportar` a superadmin sin tocar el catálogo de
permisos; el camino de error se revisó por lectura de código —
`throwApiError` ya está probado por el resto del módulo desde I3).

**Riesgo nuevo**: ninguno — los dos bugs se encontraron y arreglaron en
este mismo commit.

#### Commit I4g — Ficha de préstamo (cerrado) — último sub-paquete de I4

`GET /api/loans/by-folio/{folio}` (la razón de ser de esa ruta en el
contrato — I4a-f solo habían usado `GET /loans/{id}`). Folio y fechas en
`--go-font-mono`. Los **tres badges ortogonales** de nuevo, esta vez los
tres juntos en el mismo lugar donde más importa verlos sin fusionar:
`estado`, `atrasado`+`dias_atraso`, `entrega_autorizada`. Fotos
**antes/después lado a lado** por equipo (frente/atrás de entrega junto a
frente/atrás de devolución, en ese orden) vía miniaturas de 96px
ampliables (clic → `GlassModal` con la imagen completa). Bitácora con el
`Timeline` genérico que I1 ya había dejado listo específicamente para
esto (mismo shape `{id, tipo, actor, detalle, created_at}` que trae
`loan.eventos`, sin que I4g tuviera que tocarlo).

**El criterio de aceptación real, no solo leído**: se cargó
`fixtures/prestamo_demo.json` tal cual y se verificó en pantalla —no por
inspección del JSON— que los 6 campos `null` del payload (`notas_responsiva`,
`fecha_regreso_real`, `entrega_autorizada_por`, `confirmada_por`,
`fecha_confirmacion`, y las 2 fotos de devolución aún no tomadas) se
pintan como "—", nunca como el string literal `"null"` ni `"undefined"`,
y sin tronar el render. Verificado por script: cero apariciones de esos
dos literales en el texto renderizado, 6 guiones exactos donde el fixture
trae `null`.

**Bug real encontrado al verificar en pantalla, no al leer código**: la
página tronaba con `pageerror` — "Media 39/40/41/42 no encontrada" — al
intentar pintar las miniaturas de firmas y fotos del préstamo demo.
Causa: `fixtures/prestamo_demo.json` referencia esos 4 ids como si ya
existieran (son el payload congelado, criterio de aceptación de esta
misma ficha), pero `state.media` (el `Map` en memoria del mock) arranca
**vacío** — solo se puebla cuando alguien sube una foto de verdad vía
`uploadMedia`. Nadie lo había notado antes porque I4a-f nunca renderizó
una miniatura de un media id preexistente del fixture, solo de fotos
recién subidas en la misma sesión (que sí generan su propia entrada).
Arreglado sembrando 4 placeholders (SVG generado en el momento, sin
canvas ni dependencias — `data:image/svg+xml`) en `state.js` para
exactamente esos 4 ids, con una nota explicando por qué existen y por qué
no son fotos reales.

**Evidencia**

```
npm run build verde. index-*.js 16.66 kB gz (sin cambio real — el salto a
16.68 en el build anterior fue ruido del pre-bundle de Vite, no un
cambio real de código). CSS 7.08 -> 7.11 kB gz. Payload de /login: 122.89
kB gz (anterior: 122.86 kB gz), contra el techo de 250 — el margen sigue
enorme incluso sumando los 7 sub-paquetes completos de I4.
FichaPrestamoPage-*.js (chunk lazy): 9.18 kB / 2.76 kB gz. dist/ grep
sigue sin rastro de mock/harness/permisos-demo.
```

Verificado en pantalla real de punta a punta (`VITE_EQUIPOS_MOCK=1`,
1280x800 y 390x844, superadmin) contra `CE-0007` con su JSON pristino
(nunca mutado por ninguna prueba anterior en esta misma sesión de
servidor): folio, badges, los 6 campos vacíos como "—", accesorios,
cargador, 4 miniaturas (2 con placeholder naranja de "foto", 2 "Sin foto"
para las de devolución que no existen todavía), clic en una miniatura
abre el modal con la imagen completa y el título correcto, bitácora
muestra el evento real del fixture ("Prestamo confirmado. Carta
responsiva firmada por ambas partes.").

Los 4 e2e de Presupuestos: `auth.spec.js` 7/7,
`presupuesto-flujo-completo.spec.js` 9/9, `gastos-generales.spec.js` 9/9,
`pantallas.spec.js` 23/23 (48/48).

**No verificado en pantalla real**: "Ver responsiva (PDF)" solo abre la
URL en una pestaña nueva (el mock no genera un PDF real detrás de esa
ruta, mismo límite ya documentado desde I3 en `loanResponsivaUrl`); un
préstamo `atrasado:true` para ver el tercer badge simultáneo con los
otros dos (el fixture demo trae `atrasado:false`).

**Riesgo nuevo**: ninguno — el bug de media ids se encontró y arregló en
este mismo commit.

---

### Cierre del paquete I4 completo (I4a → I4g, 7 commits)

Los 7 sub-paquetes cerraron con build verde, capturas reales en 1280x800
y 390x844, y los 4 e2e de Presupuestos en 48/48 cada uno — sin una sola
regresión a lo largo de todo el paquete. Bundle final de `/login`: **122.89
kB gz**, contra el techo de 250 (el paquete que el propio prompt marcaba
como "el que puede reventar el techo" terminó usando poco más de la mitad
del margen, sin necesitar ningún recorte).

Bugs reales encontrados y arreglados durante la construcción (todos
dentro del mismo commit que los encontró, ninguno quedó abierto):
`src/api/index.js` no reexportaba `BASE`/`throwApiError` (I4a);
`GlassNav` recortaba la pestaña activa en 390px con 6 items (I4a);
`uploadMedia` del mock nunca adjuntaba el media al ítem/firma —
`addLoanMedia` vivía huérfana sin dispatcher (I4c); un ítem se duplicaba
al agregarlo por reconstruir el array a mano sobre una referencia viva
del mock (I4c); por la misma causa, un `setLoan` con la misma identidad
de objeto no re-renderizaba — arreglo de raíz con `clone()` en la
frontera pública de todo `mock/loans.js`, no un parche puntual (I4c);
`fetchLoansExport` vivía huérfana y además usaba `res.json()` para lo que
debía ser un blob CSV (I4f); el mock nunca implementó `desde`/`hasta`
(I4f); y el `state.media` vacío tronaba al pintar las miniaturas del
préstamo demo (I4g). Nueve bugs reales en total, los nueve encontrados
por verificación en pantalla (no por lectura de código) salvo dos, y los
nueve arreglados antes de cerrar su commit — ninguno quedó como riesgo
abierto en `docs/riesgos/interfaz.md`.

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
