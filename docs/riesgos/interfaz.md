# Riesgos — interfaz

Descubiertos verificando en disco, no en teoria. Los que no son de mi carril se
reportan aqui y no se parchean.

## R-I01 — El presupuesto de rendimiento ya estaba vencido antes de empezar

El bundle inicial mide **261.76 kB gz** en el commit base, contra el techo de
**250 kB gz** de la asignacion. Medido con `npm run build` sobre `281f10b`, antes
de tocar una linea.

ApexCharts viaja dentro del chunk principal (942 kB sin comprimir), sin diferir.
`jspdf` y `html2canvas` si estan bien: salen en chunks aparte por el `import()`
dinamico.

Consecuencia: el `manualChunks` y el code splitting por ruta de I1 no son pulido
opcional, son deuda ya vencida. Y todo lo que agregue I1 (`motion`, fuentes,
cristal) empuja el numero hacia arriba desde un punto que ya no cumple.

## R-I02 — `CLAUDE.md` contradice a `models.py` en gastos generales

`CLAUDE.md:39` afirma que `general_expenses` va "sin `creator_id`/`brand_id`".
`models.py:142-148` dice lo contrario y es explicito:

```
Tiene brand_id (no nullable) porque TODO gasto general debe estar asociado a
una marca para trazabilidad y reportes por marca.
brand_id = Column(Integer, ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
```

Existe `backend/migrate_add_brand_to_general_expenses.py`: la marca se agrego
despues y la documentacion no se actualizo. Esa contradiccion ya costo un e2e
rojo (ver `1568ff6`).

`CLAUDE.md` esta fuera de mi alcance. **Pido que se corrija arriba.**

## R-I03 — `CLAUDE.md` apunta a una ruta que I0 movio

`CLAUDE.md:46` dice `frontend/src/hooks/useMobile.js`. Desde `d602e00` vive en
`frontend/src/modules/presupuestos/hooks/useMobile.js`.

El hook sigue funcionando y se conserva, como manda la regla; solo la ruta
documentada quedo vieja. Tampoco puedo editar ese archivo. Ver B-I07: cuando el
modulo de equipos necesite `useMobile`, hay que promoverlo a un lugar compartido,
y ese es el momento de corregir la referencia de una sola vez.

## R-I04 — `seed_demo_year.py` deja una DB que parece sembrada y pinta ceros

Corre sin error y reporta porcentajes de gasto por creador, pero deja:

- 355 tickets, **todos** en estado `pendiente`
- los 6 ciclos en `spent=0.0` y `amount=0.0`
- 0 gastos generales

Un ticket `pendiente` nunca descuenta (regla R7), asi que el dashboard sale con
todos los KPI en `$0.00` y los 5 graficos en "Sin datos", con la DB "llena". El
seed escribe el campo historico congelado `creators.spent_budget`, que ya no
alimenta ningun calculo vigente.

Es una trampa de verificacion: quien tome capturas despues de ese seed va a
fotografiar el estado vacio y creer que verifico la pantalla. Para las capturas de
I0 hubo que aprobar los 355 tickets **por la API real** (para que
`crud.approve_ticket` actualizara los ciclos), no tocando la DB.

`backend/` esta fuera de mi alcance. **Reportado, no parcheado.**

## R-I05 — Colision de nombre `AppShell` que llega en I1

`frontend/src/App.jsx:48` ya define un componente local llamado `AppShell`. I1
crea `src/shell/AppShell.jsx`. Hay que decidir el renombre al escribir I1, no en
el merge.

## R-I06 — Las fuentes de marca no existen en disco

Barrido de `context_desing_go`: cero `.woff2`, `.woff`, `.otf` y `.ttf`. Blauer
Nue y Conthic no estan. I7 quita el `@import` remoto de Google Fonts, que hoy es
lo unico que trae Inter, JetBrains Mono y Space Grotesk, asi que quitarlo sin
sustituto deja la app sin tipografia propia.

Plan acordado: `@fontsource` autohospedado para JetBrains Mono y los respaldos
documentados, con la pila lista para meter los woff2 de marca cuando lleguen.
Bloquea el cierre visual de I1 y de I7.

## R-I07 — El entorno de desarrollo no tolera Google Drive

`G:\Mi unidad` es Google Drive File Stream y Windows la reporta como FAT32. No
soporta reparse points y `npm install` falla ahi con `EPERM`/`EBADF`. Ademas
sincronizaria `node_modules` completo en segundo plano.

Riesgo real de que alguien vuelva a clonar el repo ahi y pierda medio dia
peleando con el gestor de paquetes en vez de con el codigo. Se trabaja en
`C:\dev\Ready2Go`.

## R-I08 — SSH sin autorizar (mitigado, no resuelto)

La llave SSH `id_ed25519` no esta autorizada en la org
(`SHA256:eMeepbSTJV6UM4k8g0ThUk4wv4toJh195ZPuCLKfLMQ`):
`git@github.com: Permission denied (publickey)`.

Mitigado: el clon y el push van por HTTPS con Git Credential Manager, y el push
de cierre del 28/07 entro limpio (`281f10b..012ef13`, fast-forward). El trabajo
llega igual.

Queda como riesgo porque cualquiera que siga la instruccion de clonar con la URL
`git@github.com:...` de la asignacion se estrella de entrada, sin pista de que la
causa es la llave y no el repo.

## R-I09 — `request()` de `src/api/client.js` descarta `status` y `codigo` (RESUELTO en I3)

Verificado en disco, `frontend/src/api/client.js:62-74`:

```js
export async function request(path, options = {}) {
  const res = await fetchWithAuthRetry(path, {...});
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
```

Solo sobrevive el texto de `detail`. El contrato de Equipos
(`docs/contratos/API_EQUIPOS_v1.md` §0) define un sobre de error con
`codigo` estable (`SIN_PERMISO`, `PERMISOS_NO_DISPONIBLES`, `EQUIPO_OCUPADO`,
`TRANSICION_INVALIDA`, `MEDIA_INVALIDA`, `MEDIA_MUY_GRANDE`,
`NO_ENCONTRADO`) precisamente para que el cliente **no** tenga que adivinar
por el texto del mensaje. Con `request()` tal como esta hoy, pintar los
cinco codigos feos (regla dura del pool: `503` nunca desloguea,
`409 EQUIPO_OCUPADO` vs `409 TRANSICION_INVALIDA` son UI distintas) exigiria
parsear `error.message` con texto libre — fragil y se rompe si el backend
cambia la redaccion de `detail` sin tocar `codigo`.

Se arregla en **I3 commit 1** con una `ApiError` que conserve `status` y
`codigo` ademas del mensaje. Se reporta aqui como riesgo, no como pedido:
es archivo mio (`src/api/`), lo resuelvo yo cuando le toque.

**Resuelto**: `ApiError extends Error` en `client.js`, con `status`/`codigo`/
`detail` ademas de `message` (que sigue siendo exactamente `body.detail`,
igual que antes — las vistas de Presupuestos que hacen
`catch (e) { setError(e.message) }` no se enteraron del cambio, confirmado
por los 25/25 e2e de Presupuestos sin tocar). `esCodigo(e, "EQUIPO_OCUPADO")`
exportado desde `@/api`. `uploadTicket`/`createGeneralExpense` (los dos
multipart existentes) tambien migraron a la misma `throwApiError` compartida,
por consistencia — antes duplicaban el parseo del sobre de error a mano.

## R-I10 — `fixtures/equipos.json` trae 3 campos fuera del contrato congelado

Verificado en disco: `docs/contratos/fixtures/equipos.json` incluye
`estado_fisico`, `comentario_auditoria` y `fecha_auditoria` en cada equipo.
Ninguno de los tres aparece en la forma de fila que documenta
`docs/contratos/API_EQUIPOS_v1.md` §2 (`id`, `codigo`, `nombre`, `categoria`,
`marca`, `modelo`, `numero_serie`, `activo_fijo`, `cuenta_gmail`,
`espacio_disponible`, `estado_operativo`, `condicion`, `accesorios_tipicos`,
`disponible`, `tenedor_actual`, `fecha_regreso_esperada`, `atrasado`,
`dias_atraso`).

`docs/contratos/` es de solo lectura para mi — no me toca decidir cual de
los dos manda. Mientras no haya respuesta de quien congelo el contrato o del
carril de servidor: en I3/I4 estos tres campos se pintan **solo si vienen**
en la respuesta real, nunca se asumen ni se inventan en el mock.

## R-I11 — La razon social emisora de la responsiva sigue "pendiente de confirmar"

Verificado en disco: `docs/contratos/fixtures/empresas.json`, tercer
registro (`SERVICIOS CORPORATIVOS QUANTUM DE OCCIDENTE, S.C.`) trae
`"_nota":"emisora de la carta responsiva — PENDIENTE que marketing confirme
que es la correcta"`.

No bloquea la UI de Equipos: la lista de empresas sale de
`GET /api/empresas/` en tiempo real (§6 del contrato), nunca hardcodeada, asi
que cual sea la razon social final no exige tocar codigo del cliente. Si
bloquea el PDF final de la carta responsiva (WP5, no es mio) si se genera
antes de que marketing confirme cual empresa es la correcta. De marketing/
Jose, no de mi carril — se menciona una vez aqui y se sigue.

## R-I12 — `index.html` tenia clases de Tailwind muertas pisando los tokens de tema en `<body>` (RESUELTO en I1 commit 5)

Encontrado escribiendo el verificador de contraste de `pantallas.spec.js`: el
primer intento media 1.06:1 en el nav de modulos (`GlassNav`), muy por debajo
del 4.5:1 exigido. `getComputedStyle(document.body).color` devolvia
`rgb(17, 24, 39)` (gray-900 de Tailwind) y `backgroundColor` devolvia
`rgb(249, 250, 251)` (gray-50), pese a que `--go-text-secondary` resolvia
correctamente a `#c5c5c5` y `--go-bg` a `#09090b` en `:root`.

Causa: `index.html` traia `<body class="bg-gray-50 text-gray-900
antialiased">`, heredado del starter de Tailwind y nunca limpiado. Esas
clases utilitarias (capa `utilities`, mayor prioridad que `@layer base` donde
vive la regla `body { color: var(--go-text-secondary); ... }` de
`index.css`, y ademas mayor especificidad por ser selectores de clase contra
un selector de tipo) pisaban en silencio el tema real en el elemento raiz.

Invisible en cualquier verificacion visual porque cada contenedor de
Presupuestos fija su propio `background` inline (p.ej. `PresupuestosLayout`
con `style={{ background: "var(--go-bg)" }}`) — la pantalla se ve correcta
a simple vista. Pero cualquier elemento que dependa de `color: inherit` para
llegar hasta `body` (como el `<a>` de `GlassNav`, que no fija color propio y
lo hereda desde su `<span>` hijo hacia arriba en cascada) terminaba pintado
con el gray-900 equivocado.

`grep` confirmo cero referencias a esas dos clases en `src/`: no eran
alcanzadas por ningun estilo ni logica. Se quitaron sin sustituto
(`<body class="antialiased">`); cero regresion visual, los 47 e2e (25 de
Presupuestos + 22 del verificador) siguen verdes tras el cambio.

## R-I13 — El contrato no da un ejemplo de body para `POST /loans/{id}/devolucion`

Verificado en disco: `API_EQUIPOS_v1.md` §3 describe la *regla* de
`/devolucion` ("por cada equipo: 2 fotos de devolucion, o no_devuelto: true
con nota_devolucion obligatoria") pero, a diferencia de
`/confirmar-devolucion` (que sí trae un ejemplo JSON completo del body:
`{"decisiones": [...]}`), no da la forma exacta del body que espera este
endpoint.

`src/modules/equipos/api/real/loans.js` (`returnLoan`) tuvo que **adivinar**
una forma (`{ items: [...] }`) para poder escribir el cliente real contra
algo. El mock (`mock/loans.js`) no depende de esta adivinanza — usa su propia
firma de función interna — así que I3/I4 no se bloquean, pero cuando el
servidor real de Equipos aterrice, `real/loans.js:returnLoan` es el primer
lugar a revisar si el body no calza. Se reporta, no se resuelve solo: falta
que quien congelo el contrato confirme la forma real.
