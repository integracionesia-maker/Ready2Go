# Responsividad Móvil — Qué se implementó

> Implementa `docs/auditoria-responsividad-movil.md` (auditoría original, 21 hallazgos en 4 niveles de severidad). Este documento es el registro de qué se hizo, cómo, y qué queda pendiente — la auditoría original queda como referencia histórica del diagnóstico.

---

## Infraestructura nueva compartida

### `frontend/src/design/useMobile.js`

> Promovido a `src/design/` en I8 lote 7 (compartido entre Presupuestos y Equipos) — antes vivía en `frontend/src/modules/presupuestos/hooks/useMobile.js`.

Hook `useMobile(breakpoint = 640)` que devuelve `true` si el ancho de ventana es menor al breakpoint (se actualiza con el evento `resize`). Se usa **solo** donde Tailwind no alcanza — es decir, donde se necesita un valor numérico en JS, no una clase CSS. En este proyecto eso es exclusivamente:
- La prop `height` de los charts de ApexCharts (`frontend/src/modules/presupuestos/components/charts/*.jsx`) — un número, no CSS.
- El formato de mes en `GeneralExpensesExportModal.jsx` (`Intl.DateTimeFormat` con `month: "short"` vs `"long"`).
- `RowActions.jsx` (ver abajo), para decidir si renderiza botones horizontales o el menú `⋯`.

Para cualquier otro caso de responsividad (tamaños, paddings, grids, mostrar/ocultar), usar clases `sm:`/`md:` de Tailwind directamente — no este hook.

### `frontend/src/design/RowActions.jsx`

> Promovido a `src/design/` en I8 lote 7 (compartido entre Presupuestos y Equipos) — antes vivía en `frontend/src/modules/presupuestos/components/RowActions.jsx`.

Componente compartido para las acciones por fila de una tabla (resuelve C2 y C3 de la auditoría). Contrato:

```jsx
<RowActions actions={[
  { key: "ver", label: "Ver", onClick: () => ... },
  canDelete && { key: "eliminar", label: "Eliminar", variant: "danger", onClick: () => ... },
  { key: "reset", label: "Resetear contraseña", mobileLabel: "Reset", onClick: () => ... },
]} />
```

- `key`, `label`, `onClick` son obligatorios. `mobileLabel` (opcional) es un texto más corto que solo se usa en el menú móvil — así una acción puede tener texto completo en desktop y abreviado en móvil sin duplicar lógica. `variant: "danger"` pinta la acción en rojo (`var(--go-error)`).
- Valores falsy dentro del arreglo (`condición && {...}`) se filtran automáticamente — así se condiciona una acción sin un `if` aparte.
- En desktop renderiza los botones horizontales de siempre. En móvil (`useMobile()`) renderiza un botón `⋯` que abre un menú desplegable con las mismas acciones (cierra al hacer click afuera).

Usado en: `TransactionTable.jsx`, `ValidationQueue.jsx`, `AdminView.jsx` (tablas de creadores y marcas), `UserManagement.jsx`, `GeneralExpensesPage.jsx` (Presupuestos) y, desde I8 lote 7, `ActivosPage.jsx`/`InventarioPage.jsx` (Equipos) — el motivo original de la promoción a `src/design/`.

### `frontend/src/index.css` — clases nuevas

- `.go-table-scroll-wrapper` / `.go-table-scroll`: degradado en el borde derecho de una tabla con scroll horizontal, visible solo bajo 767px (resuelve C1). Envolver el contenedor `overflow-x-auto` existente con un div `.go-table-scroll-wrapper`, y agregar `.go-table-scroll` al propio div con `overflow-x-auto`. No requiere JS — es la alternativa mínima que la auditoría marcaba como aceptable (no se implementó el patrón de *card stacking* alternativo, ni detección de "ya llegué al final del scroll", por simplicidad y menor riesgo).
- `.go-card` ahora usa `p-4 sm:p-6` (antes `p-6` fijo) — beneficia a todas las tarjetas de la app (KPIs, formularios, secciones de Inicio), no solo a las mencionadas explícitamente en la auditoría.

---

## Qué se resolvió, por hallazgo

| Hallazgo | Archivo(s) | Cómo |
|---|---|---|
| C1 — tablas sin pista de scroll | TransactionTable, ValidationQueue, AdminView (creadores, marcas y también histórico de ciclos), UserManagement, GeneralExpensesPage | `.go-table-scroll-wrapper` / `.go-table-scroll` |
| C2 — botones de acción colapsan | TransactionTable, ValidationQueue, AdminView, UserManagement, GeneralExpensesPage | Migrados a `<RowActions>` |
| C3 — "Resetear contraseña" desborda | UserManagement | `mobileLabel: "Reset"` en `RowActions` |
| C4 — date inputs con ancho fijo | DateRangeFilter | `flex-1`/`min-w-[140px]` en móvil, `sm:w-[160px]` en desktop |
| A1 — KPI con fuente fija | KpiCard | `text-2xl sm:text-[28px]` |
| A2 — grid de 4 KPIs en la fila 2 | Dashboard | **Ya estaba resuelto** de una implementación anterior (R12) — solo se verificó |
| A3 — altura fija de gráficas | Los 5 componentes de `charts/` | `height={isMobile ? 220 : 320}` (o 200/280 en `SpendTrendChart`) vía `useMobile` |
| A4 — filtros con min-width fijo | TransactionTable | `min-w-0 sm:min-w-[Npx]` |
| A5 — pestañas de AdminView | AdminView | `px-3 sm:px-4 text-xs sm:text-sm` |
| A6 — paginación cargada en móvil | TransactionTable | Label "Filas por página" oculto en móvil, contador abreviado `X–Y/Z` |
| A7 — botones de header en GeneralExpensesPage | GeneralExpensesPage | Header y botones en `flex-col sm:flex-row`, botones `w-full sm:w-auto` |
| A8 — grid de 3 columnas en Mi Perfil | ProfilePage | `grid-cols-1 sm:grid-cols-3` |
| M1 — padding fijo de Modal | Modal + todos sus consumidores (UploadTicketModal, GeneralExpenseModal, GeneralExpensesExportModal, DeleteConfirmModal, los modales de AdminView, UserManagement y ValidationQueue) | `px-4 sm:px-6` |
| M2 — drop zone muy alta | UploadTicketModal, GeneralExpenseModal | `py-4 sm:py-7` |
| M3 — tarjetas de Inicio muy altas | HomePage | Ícono `h-10 w-10 sm:h-12 sm:w-12` + el padding de `.go-card` ya reducido globalmente |
| M4 — touch target del Sidebar | Sidebar | `py-3` en móvil (drawer), `md:py-2.5` en desktop |
| M5 — labels de meses largos | GeneralExpensesExportModal | `Intl.DateTimeFormat` con `month: "short"` en móvil |
| M6 — sin botón de limpiar filtros | TransactionTable | Botón "Limpiar filtros" condicional (aparece si algún filtro está activo) |
| B2 — logo grande en login | LoginPage | `h-20 sm:h-28` |
| B5 — touch target de ThemeToggle | ThemeToggle | `h-10 w-10 sm:h-9 sm:w-9` |
| B1, B3, B4 | CreatorList, Header, LoadingScreen | Sin cambios — la auditoría ya los marcaba como correctos |

## Cómo se ejecutó

Se usó un workflow de agentes en paralelo para los 5 archivos de tabla (C1/C2/A4-A7/M6, todos consumiendo el mismo `RowActions`/`useMobile`/CSS ya construidos de antemano para evitar que cada uno reinventara el patrón). El resto de los hallazgos (más simples, un archivo cada uno) se aplicó directamente.

**Nota de proceso:** el agente de `TransactionTable.jsx` sufrió un corte de conexión a media edición y dejó el archivo con un `<div>` sin cerrar (rompía `npm run build` por completo) y la migración a `RowActions` a medio hacer (import sin usar, columnas de header/body desalineadas). Un paso de verificación posterior (otro agente, cruzando los 5 archivos) detectó el problema exacto con línea y causa; se corrigió a mano y se confirmó con `npm run build` en verde.

## Verificación

- `npm run build` (Vite) pasa limpio.
- No se corrieron pruebas automatizadas de UI (Playwright) para este cambio — es puramente visual/estructural, sin lógica de negocio nueva; los E2E existentes (`frontend/e2e/*.spec.js`) no deberían verse afectados porque ningún selector de texto/rol cambió (los botones migrados a `RowActions` conservan el mismo `label` visible en desktop).

### Checklist manual recomendado (de la auditoría original, sección "Notas para el agente implementador")

Probar en 320px (iPhone SE), 375px (iPhone 12), 414px (iPhone 14 Pro Max) y 768px (iPad Mini), en tema claro y oscuro:
1. Cada tabla muestra el degradado de scroll cuando hay columnas ocultas, y el menú `⋯` de `RowActions` abre/cierra correctamente al tap y al click afuera.
2. Las gráficas del Dashboard se ven completas sin scroll excesivo.
3. Los modales de creación/edición no dejan los botones de acción fuera del viewport.
4. El drawer móvil del Sidebar tiene targets táctiles cómodos.

## Pendiente / fuera de alcance

- El *card stacking* (alternativa a scroll horizontal mencionada en C1) no se implementó — se optó por la alternativa mínima (degradado + `-webkit-overflow-scrolling: touch`), que la auditoría marcaba como aceptable y de menor riesgo.
- La tabla del modal "Histórico de ciclos" (`AdminView.jsx`) no estaba en la lista original de C1 pero se le aplicó el mismo tratamiento por consistencia.
