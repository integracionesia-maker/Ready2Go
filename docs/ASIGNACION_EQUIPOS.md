# Asignacion de trabajo — Control de Equipos (interfaz)

> Fase 5 del proyecto. Tu carril: **interfaz**. Paquetes WP7 y WP8 del plan, mas el endurecimiento que vive en el cliente.
> Plan tecnico completo: `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` (seccion 8) y `DESIGN_SYSTEM.md`.
> Contrato de API: `docs/contratos/` — **solo lectura**.
> Este documento manda sobre el plan si algo se contradice. Si algo no esta aqui, preguntalo antes de escribirlo.

> **ANTES DE ESCRIBIR CODIGO:** el contrato de API (`docs/contratos/`) se publica en master el dia 0 y todavia no esta. Lee este documento completo, prepara tu entorno y planea tu orden de trabajo, pero **no arranques la tarea 0 hasta que se avise que el contrato ya esta en master**. Se avisa el mismo dia.

---

## Regla numero uno

Tu carril vive **dentro de `frontend/`**. La frontera con el resto del trabajo no es un archivo: es el contrato HTTP. Si respetas el contrato y no sales de `frontend/`, no vas a chocar con nadie en un merge. Nunca.

---

## Tus rutas (dueño unico, nadie mas las toca)

```
frontend/src/            el arbol completo — design/, shell/, modules/presupuestos/,
                         modules/equipos/, api/, context/, hooks/, utils/, assets/,
                         index.css, main.jsx, App.jsx
frontend/index.html, frontend/public/
frontend/vite.config.js, tailwind.config.js, postcss.config.js, jsconfig.json
frontend/package.json, package-lock.json
frontend/playwright.config.js y frontend/e2e/ completo
                         (incluidos auth.spec.js, presupuesto-flujo-completo.spec.js y
                          gastos-generales.spec.js: los rompes tu, los arreglas tu)
DESIGN_SYSTEM.md         (raiz)
docs/backlog_interfaz.md, docs/avances/interfaz.md, docs/changelog/interfaz.md, docs/riesgos/interfaz.md
```

## Fuera de tu alcance — no los edites

```
backend/                 el directorio completo. Ni codigo, ni pruebas, ni migraciones,
                         ni seeds, ni requirements.
raiz: BACKLOG.md, CHANGELOG.md, status.md, context.md, MVP_BREAKDOWN.md, RISKS.md,
      CLAUDE.md, avances_diarios.md, .env.example, .gitignore
docs/contratos/          solo lectura. De ahi copias los fixtures a tus mocks; no los editas.
docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md y doc/ completo
```

Hay trabajo en paralelo sobre varios de esos archivos. Si necesitas cambiar algo de esta lista, **pidelo, no lo edites**.

**Si el servidor no cumple el contrato: se reporta. NO se parchea con un adaptador en el cliente.** Un adaptador escondido es deuda invisible que revienta despues en el e2e real.

---

## Reglas duras dentro de tus propios archivos

Cada una de estas nace de un bug real que ya costo tiempo en este repo:

- **Prohibido** agregar alias manuales de `react`/`react-dom` en `vite.config.js`. `resolve.dedupe` + `optimizeDeps.include` es suficiente con un solo `node_modules`. El alias causo el "Invalid hook call".
- `[data-theme="light"]` se queda **sin `:root`**. Agregarselo rompe la plantilla off-screen del PDF de Presupuestos.
- En `apexTheme.js` nunca asignes `stroke`, `fill`, `plotOptions` ni `responsive` como `undefined` explicito: ApexCharts pisa sus defaults y truena el dashboard entero sin error boundary.
- `jspdf` y `html2canvas` siguen con `import()` dinamico. No los importes estaticamente.
- Una sola instalacion de npm agrupada al inicio. Si `package-lock.json` sale en conflicto, **jamas se edita a mano**: se toma una version completa y se regenera con `npm install`.
- Se conservan `useMobile`, `RowActions` y `go-table-scroll` (responsividad movil ya auditada).

---

## Tareas, en orden

### I0 — Costura (primer commit, mecanico, aislado, sin cambio visual)
`git mv` de `src/components/`, `src/pages/`, `src/hooks/`, `src/utils/` a `src/modules/presupuestos/` + arreglo mecanico de imports + extraccion de `src/api/client.js` (`request`, `fetchWithAuthRetry`, `refreshSession`, `isNetworkError`, `setAuthFailureHandler`) dejando `src/api/index.js` como barril + `jsconfig.json` con alias `@`.
**Cierra con:** `npm run build` verde y **los 3 e2e existentes verdes en el mismo commit**, cero cambio visual.
Si esto no sale limpio y aislado, todo lo que venga despues es irrevisable.

### I1 — Shell liquid glass (WP7-A)
`src/design/`: `tokens.css`, `fonts.css` (woff2 autohospedadas, `font-display: swap` y pila de respaldo), `glass.css`, `GlassFilterDefs.jsx`, `motion.js`, y los componentes `GlassPanel`, `GlassNav`, `GlassModal`, `KpiTile`, `StatusDonut`, `Timeline`, `Toast` + `ToastProvider`, `SkeletonShimmer`, `EmptyState`, `RoleBadge`, `CommandPalette` (registro por provider), `index.js`.
`src/shell/`: `AppShell`, `ModuleTabs`, `navItems`. `public/theme-boot.js`. Particion de `index.css` por capas. `MotionConfig` + `ToastProvider` en `main.jsx`. `manualChunks` en `vite.config.js`.

Limites del cristal, no negociables (estan en `DESIGN_SYSTEM.md`):
- El filtro SVG como `backdrop-filter` **solo funciona en Chromium**. Va unicamente en el shell, detras de `@supports`. El resto usa la receta CSS pura.
- **Prohibido cristal en filas de tabla, listas largas y contenedores con scroll.** Maximo 3-4 superficies de cristal en pantalla.
- Todo texto sobre cristal lleva velo solido detras. Contraste 4.5:1 **medido**, no a ojo.
- Todo el movimiento dentro de `prefers-reduced-motion: reduce`.

**Cierra con:** capturas en desktop y 390px, y el contraste medido.

### I2 — Migracion visual de Presupuestos (WP7-B)
Los ~34 componentes y paginas ya movidos a `src/modules/presupuestos/`. **Solo piel.** El diff de este paquete no debe contener ni una llamada a la API ni una condicion de negocio. Se conservan las rutas actuales tal cual: `/`, `/dashboard`, `/creadores`, `/transacciones`, `/validacion`, `/gastos-generales`, `/administracion`, `/perfil`, `/403`.

**Trampa ya verificada en disco:** los 3 specs usan `page.locator('nav')` y hoy solo hay un `nav` montado por pantalla. Al agregar la nav superior de cristal revientan por strict mode. Resuelvelo con `aria-label` distintos y `getByRole`, o no marques el contenedor nuevo como `nav`. Decidelo **ahora**, no en el merge.

**Cierra con:** los 3 e2e verdes y captura de cada pantalla migrada.

### I3 — Mocks propios (arranca el dia 1, no esperes al servidor)
`src/modules/equipos/api/mock/` activado por `VITE_EQUIPOS_MOCK=1`, alimentado con **copia literal** de `docs/contratos/fixtures/*.json`.
Los fixtures incluyen los codigos feos, no solo el camino feliz: **409** equipo ocupado, **403** sin permiso, **503** permisos no disponibles, **413** foto muy grande, **401** a mitad del wizard. Tu UI tiene que verse bien en los cinco.

### I4 — Modulo Equipos (WP8)
`src/modules/equipos/` completo — 7 vistas: inicio, inventario, nuevo prestamo (wizard de 4 pasos), activos, aprobaciones, historial, y ficha por folio.
Componentes propios del modulo: `SignaturePad` (Pointer Events, alta densidad, deshacer, deteccion real de vacio), `PhotoCapture` (`capture="environment"`, compresion en cliente a 900px/0.72, frente y atras **obligatorias**), `AccesoriosPicker`, `EquipmentCard` (tilt 3D solo en puntero fino), modales de devolucion, autorizacion, confirmacion e incidencia, bitacora, fotos antes/despues, dashboard, y clientes de API por dominio.

**Correccion al plan §8.4:** `SignaturePad`, `PhotoCapture` y `EquipmentCard` bajan a `src/modules/equipos/components/`. Solo `Timeline` es generico y se queda en `src/design/`.

**Ojo con los badges:** estado, atraso y autorizacion son **tres cosas distintas**. `entrega_autorizada` es ortogonal al estado del prestamo: un prestamo puede estar devuelto y seguir sin autorizar. No los mezcles en un solo badge.

**El cliente NUNCA recalcula el atraso.** El servidor entrega `atrasado` (bool) y `dias_atraso` (int) ya calculados en hora de Mexico. Calcularlo en el navegador con `toISOString()` marca atrasado un dia antes despues de las 18:00.

### I5 — Permisos en la UI
`usePermisos` y `RequierePermiso` propios del modulo, leyendo `user.permisos` de `/auth/me`, con fallback por rol mientras el motor real aterriza.
**La UI solo pinta. Ningun control de acceso vive aqui** — cada endpoint valida por su cuenta.
Agrega un modo diagnostico en desarrollo que registre en consola toda clave de permiso desconocida: si el catalogo cambia, los botones desaparecen en silencio y nadie se entera hasta el piloto.

### I6 — e2e del flujo completo
`frontend/e2e/equipos-flujo-completo.spec.js` con helpers propios en `frontend/e2e/helpers/`. Escribelo el **dia 1** contra el contrato y dejalo en `test.fixme` hasta que se conecte el servidor real.
Los helpers de imagen deben emitir **PNG/JPEG reales**: el truco de `Buffer.from('%PDF-1.4...')` de los specs actuales no pasa la validacion por magic bytes.
Cuidado con el rate limit de login (30 por 15 min por IP): el flujo usa al menos 3 sesiones, reusa `storageState`.

### I7 — Endurecimiento que vive en el cliente
Quitar el script inline de tema de `index.html` (pasa a `public/theme-boot.js`) y el `@import` remoto de Google Fonts de `index.css`. Son lo unico que rompe una CSP estricta. Se hace aqui y ahora, no al final.

---

## Presupuesto de rendimiento

Bundle inicial **< 250 KB gz**. Code splitting por ruta. ApexCharts diferido. Las miniaturas las genera el servidor: pide `?tamano=thumb`, no bajes la foto de 3 MB para pintar 96px.

## Como reportas

Cuatro archivos tuyos, en `docs/`. **No abras los documentos de estado de la raiz** — se consolidan en otro lado y si los tocas hay conflicto de merge garantizado:

```
docs/avances/interfaz.md      que hiciste, evidencia, bloqueo (una entrada por dia de trabajo)
docs/backlog_interfaz.md      tus pendientes
docs/changelog/interfaz.md    que agregaste, cambiaste, quitaste
docs/riesgos/interfaz.md      riesgos que descubras
```

## Git

- Trabaja **solo en tu rama**. Nunca en master.
- `git add` con **rutas explicitas**. Nunca `git add -A` ni `git add .`.
- Push a tu rama al terminar el dia: el trabajo solo existe cuando esta en origin.
- Si un push sale rechazado o la rama diverge: **para y reporta**. Nada de `pull` pelado, `reset` ni force.

## Terminado significa

Codigo funciona + **verificado en pantalla** (desktop y 390px, captura real) + los 3 e2e de Presupuestos siguen verdes + evidencia en `docs/avances/interfaz.md`. DOM lleno no es pantalla pintada: si la captura sale en blanco, no esta terminado.
