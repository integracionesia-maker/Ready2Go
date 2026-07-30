# Prompt: Pantalla de carga inteligente + orden universal en tablas

> Prompt para una IA especializada en código. Copiar desde "## ROL" hasta el final como instrucción inicial. Tarea acotada y contenida — sin cambios de modelo de datos ni API.

---

## ROL

Eres un ingeniero de software senior full-stack (React + FastAPI) con buen criterio de UX. Tu misión es implementar dos mejoras en el frontend de una app existente, sin romper nada y respetando el design system y las convenciones del proyecto. Trabajas en una sola fase de implementación con pruebas. Reporta al terminar.

---

## CONTEXTO DEL PROYECTO

**App**: Control de Presupuestos para Creadores de Contenido — Grupo Ortiz. React 18.3 + react-router-dom 6 + Tailwind 3 + Vite 6.

**Lo relevante para esta tarea**:

- El estado de carga global vive en `App.jsx`: `const [loading, setLoading] = useState(true)`. `loadData()` pone `loading=true` antes de los 3-4 fetches paralelos (`fetchCreators`, `fetchCreatorsKpi`, `fetchBrands`, pendingCount) y lo limpia al terminar. Con `{silent:true}` (mutaciones rápidas) no activa el spinner.
- Hoy en `loading=true` se muestra un `<LoadingSpinner />` inline debajo del header — un círculo giratorio con "Cargando datos..." centrado en la vista (`frontend/src/App.jsx`, componente `LoadingSpinner` local). Eso reemplaza **todo** el `<Routes>` — ni siquiera se ve el sidebar durante la carga.
- `api/index.js` ya tiene manejo de 401 con refresh automático y `fetchWithAuthRetry`. Si el backend no responde (red caída), el fetch falla con `TypeError: Failed to fetch` (no hay `body.detail`).
- La tabla de transacciones (`TransactionTable.jsx`) ya implementa el **orden de 3 estados** con las columnas Fecha/Creador/Marca/Monto: ciclo `null → asc → desc → null`, ícono `SortIcon`, `useMemo` sobre el array completo antes de paginar, `cycleSort` resetea a página 1. Íconos SVG inline. Esa implementación es la **fuente de verdad** que debes extraer y reutilizar.
- Las otras tablas (creadores en `AdminView`, marcas en `AdminView`, usuarios en `UserManagement`) **no tienen orden** — son arrays pasados como props renderizados con `.map()` directo.
- El `Header` y el `Sidebar` siempre existen en la app autenticada (layout `AppShell`). Fuera de ahí solo está `LoginPage` (sin header/sidebar).
- Design system GO: variables CSS `--go-*`, clases `.go-card`, `.go-table`, `.go-badge`, `.btn-go`, `.go-eyebrow`, `--go-orange #FB670B`, fuentes Space Grotesk/Inter/JetBrains Mono. Tema claro/oscuro vía `data-theme` en `<html>` + `ThemeContext`.

**Convenciones**: rama `dami-branch`, commits atómicos en español, código y UI en español. NO tocar `vite.config.js` (regla de no alias manuales). Verificar en frío el backend (no confiar en `--reload` en Windows) si hay cambios de backend — pero esta tarea es solo frontend.

---

## REQUERIMIENTOS

### R1. Pantalla de carga real (sustituye al LoadingSpinner actual)

El spinner simple de hoy (`LoadingSpinner` en App.jsx) se reemplaza por una pantalla de carga completa con personalidad:

1. **Logo animado**: el isotipo oficial (`BrandLogo variant="isotipo"`) con una animación sutil (pulso de opacidad o scale). NO duración fija — se muestra mientras `loading=true`, sea 0.3s o 8s.

2. **Indicador de progreso indeterminado**: barra sutil tipo NProgress (barra delgada superior con gradiente naranja, animación de vaivén infinita que nunca llega al 100%).

3. **Mensajes rotativos (frases ingeniosas)**: un pool de ~8-10 frases en español con tono profesional pero simpático — ej. "Sumando presupuestos...", "Contando tickets uno por uno...", "Afinando los gráficos..." (invéntalas, manteniendo coherencia con la app). La frase activa **cambia cada 4 segundos** con un fade crossfade sutil.

4. **Pantalla de "sin conexión"**: si el fetch inicial falla **con un error de red** (`TypeError: Failed to fetch` o `ERR_INTERNET_DISCONNECTED` o similar, sin `body.detail`), en lugar del spinner se muestra un estado distinto con:
   - Isotipo en gris/atenuado
   - Texto claro: "Sin conexión al servidor" + subtítulo "Verifica tu conexión de red o que el servidor esté funcionando."
   - Botón "Reintentar" (vuelve a llamar `loadData()`)
   - Este estado reemplaza completamente el spinner (no hay intermitencia de spinner→error→spinner; el usuario sabe que es un problema de conectividad, no un error de datos).

5. **Dónde vive**: esta pantalla de carga **reemplaza al `<LoadingSpinner />` actual en las rutas protegidas de `AppShell`**. No debe interferir con la carga inicial de la app (antes de que `AuthProvider` determine la sesión — ese caso ya lo maneja `AuthContext.loading` mostrando nada). Tampoco debe interferir con `/login`.

**Implementación**: componente `LoadingScreen.jsx` en `components/`. App.jsx lo renderiza en lugar del `<LoadingSpinner />` actual. Debe recibir `onRetry` (callback para el botón Reintentar) y saber si el error es de red para mostrar el estado sin conexión.

### R2. Orden universal de 3 estados en TODAS las tablas

Extraer el patrón de orden de `TransactionTable.jsx` (columnas `SORTABLE_COLUMNS`, `SortIcon`, `cycleSort` de 3 estados, `useMemo` de ordenamiento) y aplicarlo a las **tres tablas restantes**:

| Tabla | Componente | Columnas ordenables |
|---|---|---|
| Creadores | `AdminView.jsx` (sección "Creadores") | Nombre, Presupuesto, Gastado, Restante |
| Marcas | `AdminView.jsx` (sección "Marcas") | Nombre |
| Usuarios | `UserManagement.jsx` | Nombre, Rol, Estado, Último acceso |

**Cómo hacerlo**: extraer la lógica común a un **hook** `useSortable` o un **componente utilitario** `SortableTableHeader` (tú decides cuál es más limpio, justifica en 1 línea). El `<SortIcon>` actual ya tiene los 3 estados — puede moverse a un archivo compartido `components/SortableHeader.jsx` o dejarse inline.

**Reglas que ya cumple TransactionTable y deben preservarse**:
- El orden se aplica sobre el **array completo** (no solo la página actual).
- Ordenar texto usa `localeCompare` en español con `sensitivity: "base"` (insensible a acentos: "Ángel" al lado de "Ana").
- Al cambiar de columna o dirección, el array vuelve al orden **predeterminado** (sin orden) si se hace clic por tercera vez.
- El ícono en estado predeterminado muestra el **doble chevron tenue** (opacidad 40%).
- El ícono en estado activo (asc/desc) se colorea con `--go-orange`.

**Estados visuales de las cabeceras**:
- **Predeterminado**: texto color tabla normal (`--go-gray-2`), doble chevron tenue a la derecha.
- **Ascendente**: texto naranja (`--go-orange`), chevron arriba naranja.
- **Descendente**: texto naranja (`--go-orange`), chevron abajo naranja.

---

## FASES DE TRABAJO

### Fase única — IMPLEMENTACIÓN Y PRUEBAS

1. **R1**: Crear `LoadingScreen.jsx` con el isotipo animado, barra de progreso, frases rotativas y estado sin conexión. Integrarlo en `App.jsx` reemplazando el `<LoadingSpinner />` actual. Asegurar que el botón "Reintentar" dispara `loadData()`.

2. **R2**: Extraer la lógica de orden de `TransactionTable.jsx` a un hook/util (`useSortable` o `SortableTableHeader`). Refactorizar `TransactionTable.jsx` para usar el hook. Aplicar a `AdminView.jsx` (creadores y marcas) y `UserManagement.jsx` (usuarios). El hook debe ser **lo suficientemente genérico** para manejar tanto strings (localeCompare) como números (resta) y fechas (Date).

3. **Verificación**: `npx vite build` limpio. Prueba visual en navegador (Playwright si está disponible en `/tmp/pw-verify`):
   - R1: forzar una carga lenta (desconectar el backend) → aparece la pantalla sin conexión con botón Reintentar; reconectar y reintentar → entra. En carga normal, al menos 2 frases distintas visibles (capturar si la carga dura lo suficiente).
   - R2: todas las tablas (transacciones, creadores, marcas, usuarios) aceptan clic en cabeceras → íconos cambian → orden correcto (verificar primer y último elemento de cada columna).

4. **Commit**: un commit atómico en `dami-branch` con mensaje descriptivo en español.

---

## CRITERIOS DE ACEPTACIÓN

- [ ] `LoadingScreen.jsx` renderiza el isotipo animado, la barra NProgress y frases que cambian cada ~4s con fade.
- [ ] Si el backend no responde, se muestra el estado sin conexión con botón Reintentar funcional (no se ve el spinner normal).
- [ ] Botón Reintentar llama a `loadData()` sin props adicionales.
- [ ] El `<LoadingSpinner />` de App.jsx ya no existe — fue reemplazado por `<LoadingScreen />`.
- [ ] `TransactionTable.jsx` sigue funcionando exactamente igual pero usa el hook/util extraído.
- [ ] Las cabeceras de las tablas de Creadores, Marcas y Usuarios muestran los íconos de orden y responden al clic con el ciclo de 3 estados.
- [ ] El orden es correcto: numérico para montos/presupuestos, textual con localeCompare para nombres, cronológico para fechas.
- [ ] `npx vite build` limpio.
- [ ] Sin regresiones: el login, el sidebar, el modal de tickets, la validación y el dashboard funcionan sin errores de consola.

---

## ARCHIVOS RELEVANTES

- `frontend/src/App.jsx` — `LoadingSpinner` (a eliminar), `loadData`, `error`
- `frontend/src/components/TransactionTable.jsx` — `SortIcon`, `cycleSort`, `SORTABLE_COLUMNS`, `useMemo` de orden (fuente de verdad de R2)
- `frontend/src/components/AdminView.jsx` — tablas de creadores (línea ~240) y marcas (línea ~340)
- `frontend/src/components/UserManagement.jsx` — tabla de usuarios
- `frontend/src/components/BrandLogo.jsx` — componente de logo (usado en LoadingScreen)
- `frontend/src/api/index.js` — `fetchWithAuthRetry`, manejo de errores (para entender el `TypeError` de red)
- `frontend/src/index.css` — variables CSS `--go-*` y clases utilitarias
