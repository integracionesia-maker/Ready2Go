# Auditoría de Responsividad Móvil — Control de Presupuestos

> **Fecha:** 2026-07-22
> **Alcance:** Todos los componentes y páginas del frontend
> **Breakpoints Tailwind:** `sm: 640px` | `md: 768px` | `lg: 1024px` | `xl: 1280px` | `2xl: 1536px`
> **Target:** Funcionalidad completa en dispositivos desde 320px de ancho (teléfono pequeño)

---

## Resumen ejecutivo

| Severidad | Cantidad | Descripción |
|---|---|---|
| 🔴 Crítico | 4 | Componentes que rompen en móvil o son inusables |
| 🟠 Alto | 8 | Funcionan pero con experiencia muy degradada |
| 🟡 Medio | 6 | Mejorable, no bloquea al usuario |
| 🟢 Bajo | 5 | Ajustes finos / pulido visual |

---

## 🔴 CRÍTICO — Inusable o roto en móvil

### C1. Tablas con overflow-x sin pista visual de scroll

**Archivos afectados:**
- `frontend/src/components/TransactionTable.jsx`
- `frontend/src/components/AdminView.jsx` (tablas de creadores y marcas)
- `frontend/src/components/UserManagement.jsx`
- `frontend/src/components/ValidationQueue.jsx`
- `frontend/src/pages/GeneralExpensesPage.jsx`

**Problema:** Todas las tablas usan `<div className="overflow-x-auto">` como contenedor. En móvil (320-375px), las tablas de 6-8 columnas se desbordan horizontalmente sin ninguna indicación visual de que hay contenido oculto a la derecha. El usuario no sabe que puede hacer scroll lateral.

**Solución propuesta:**
1. Agregar un gradiente difuminado en el borde derecho como indicador de overflow (`fade-right` indicator)
2. O, para tablas con ≤ 6 columnas: usar patrón de **card stacking** en móvil donde cada fila se convierte en una tarjeta vertical con `label: valor`
3. Como alternativa mínima: agregar `-webkit-overflow-scrolling: touch` y un shadow inset-right cuando hay overflow

**Prioridad de implementación:**
- `TransactionTable` (es la más usada por todos los roles)
- `ValidationQueue` (flujo principal de admin)
- `GeneralExpensesPage`
- `AdminView` / `UserManagement` (solo admin/superadmin)

---

### C2. Botones de acción en celdas de tabla — colapso en móvil

**Archivos afectados:**
- `frontend/src/components/TransactionTable.jsx:162-178` — 3 botones por fila: `Ver`, `Eliminar`
- `frontend/src/components/ValidationQueue.jsx:161-178` — 3 botones: `Ver`, `Aprobar`, `Rechazar`
- `frontend/src/components/AdminView.jsx:422-442` — 3 botones: `Editar`, `Histórico`, `Desactivar`
- `frontend/src/components/UserManagement.jsx:253-271` — 3-4 botones: `Editar`, `Resetear contraseña`, `Desactivar`

**Problema:** Cada fila de tabla tiene 2-4 botones en `<div className="flex items-center justify-end gap-2">`. En pantallas < 400px, el espacio horizontal de la celda es insuficiente y los botones se enciman, desbordan o se cortan. El texto `"Resetear contraseña"` en un botón `px-3` no cabe en ~120px de celda.

**Solución propuesta:**
1. Reemplazar botones de texto por botones de ícono en móvil (tooltip al hacer tap largo)
2. O usar un **menú desplegable** (tres puntos `⋯`) por fila que agrupe todas las acciones
3. Como mínimo: reducir padding a `px-2`, usar texto más corto (`"Reset"` en vez de `"Resetear contraseña"`), y permitir wrap vertical (`flex-wrap`)

---

### C3. UserManagement — `Resetear contraseña` como texto largo en botón

**Archivo:** `frontend/src/components/UserManagement.jsx:259-264`

**Problema:** El botón tiene el texto `"Resetear contraseña"` ocupando ~140px de ancho mínimo. En una tabla de 7 columnas en mobile con scroll horizontal, este botón es el principal causante del desborde.

**Solución propuesta:**
1. En móvil: mostrar solo ícono de llave 🔑 con texto abreviado `"Reset"`
2. En desktop: mantener texto completo

---

### C4. DateRangeFilter — inputs date con ancho fijo en pantallas muy estrechas

**Archivo:** `frontend/src/components/DateRangeFilter.jsx:84,103`

**Problema:** Los inputs de fecha usan `className="go-input w-[160px]"` — ancho fijo de 160px. En pantallas ≤ 360px, dos inputs de 160px + presets no caben en una fila. El `flex-wrap` los manda a otra línea, pero cada input sigue ocupando 160px aunque la pantalla sea más angosta.

**Solución propuesta:**
1. Cambiar `w-[160px]` por `w-full min-w-[140px] max-w-[180px]` o usar `sm:w-[160px] w-full`
2. En móvil, que los inputs ocupen cada uno el 50% del ancho disponible con un gap

---

## 🟠 ALTO — Experiencia muy degradada

### A1. KpiCard — Valor numérico enorme en móvil

**Archivo:** `frontend/src/components/KpiCard.jsx:18`

**Problema:** El valor usa `text-[28px]` fijo. En un grid de 2 columnas en móvil (~170px por KPI), montos como `$1,803.72` se desbordan de la tarjeta.

**Solución propuesta:**
```jsx
// Reemplazar text-[28px] por:
className="font-display text-2xl sm:text-[28px] font-bold tracking-tight"
```

---

### A2. Dashboard — KPIs con 4 columnas colapsan mal en móvil

**Archivo:** `frontend/src/components/Dashboard.jsx:171-196`

**Problema:** La primera fila de KPIs usa `grid gap-4 sm:grid-cols-2 lg:grid-cols-4`. Esto da 2 columnas en sm (bueno) y 1 columna en xs (correcto). Pero la **segunda fila** (período) usa `grid gap-4 sm:grid-cols-2 lg:grid-cols-3` y tiene 3 KPIs — en pantallas xs quedan en 1 columna (3 tarjetas apiladas), lo cual es correcto. Sin embargo, cuando se agregó el KPI de Gastos Generales (R12), quedaron **4 KPIs en esta fila** con grid de solo 3 columnas max en lg. Esto causa que el cuarto KPI quede en una nueva fila desigual.

**Solución propuesta:**
1. Cambiar la segunda fila a `lg:grid-cols-4` para acomodar los 4 KPIs
2. Reducir padding de KPI en móvil: `p-4 sm:p-6`

---

### A3. Gráficas ApexCharts — altura fija de 320px en móvil

**Archivos afectados:**
- `frontend/src/components/charts/MonthlySpendChart.jsx:72`
- `frontend/src/components/charts/GeneralExpensesChart.jsx:79`
- `frontend/src/components/charts/SpendTrendChart.jsx`
- `frontend/src/components/charts/BrandSpendApexChart.jsx`
- `frontend/src/components/charts/CreatorUsageChart.jsx`

**Problema:** Todas las gráficas usan `height={320}` fijo. En un teléfono de 375px de ancho, una gráfica de 320px de alto ocupa casi toda la pantalla, obligando a hacer mucho scroll para ver las demás secciones. ApexCharts con `width="100%"` escala bien el ancho pero la altura es fija.

**Solución propuesta:**
1. Altura responsiva: `height={typeof window !== 'undefined' && window.innerWidth < 640 ? 220 : 320}`
2. O pasar una prop `compact` desde el Dashboard cuando detecte viewport móvil
3. O usar CSS `aspect-ratio` con contenedor y `height: 100%` en el Chart

---

### A4. TransactionTable — Filtros con min-width fijo muy ancho

**Archivo:** `frontend/src/components/TransactionTable.jsx:127-200`

**Problema:** Los filtros usan `min-w-[200px]` (creador) y `min-w-[180px]` (marca), `min-w-[160px]` (prioridad y estado). En móvil de 375px, un solo filtro de 200px ya ocupa más de la mitad de la pantalla.

**Solución propuesta:**
1. Reducir min-width en móvil: `min-w-0 sm:min-w-[200px]` para que usen todo el ancho disponible
2. En xs: filtros full-width apilados verticalmente

---

### A5. AdminView — Pestañas de sección + contenido no optimizados

**Archivo:** `frontend/src/components/AdminView.jsx:288-316`

**Problema:** Las pestañas `Creadores | Marcas | Usuarios` tienen `px-4 py-1.5` con texto `text-sm`. En móvil, 3 pestañas con padding horizontal fijo ocupan ~280px. Con el título "Administración" al lado, no caben en una fila de 375px.

**Solución propuesta:**
1. En móvil: reducir padding a `px-3`, usar `text-xs`
2. O mover las pestañas debajo del título en móvil (stack vertical)
3. Usar `flex-wrap` en el contenedor padre

---

### A6. TransactionTable — Paginación muy cargada en móvil

**Archivo:** `frontend/src/components/TransactionTable.jsx:346-406`

**Problema:** El footer de paginación tiene: contador `"Mostrando X–Y de Z"` + label `"Filas por página"` + select + botones de página. En móvil de 375px, estos 4 elementos no caben en una fila. El `flex-wrap` ayuda, pero el label "Filas por página" es texto innecesario en móvil.

**Solución propuesta:**
1. En móvil: ocultar label, mostrar solo select + botones + contador abreviado (`"X-Y/Z"`)
2. Select más pequeño: `w-auto py-1 text-xs`
3. Botones de página más compactos

---

### A7. GeneralExpensesPage — Botones de acción en header

**Archivo:** `frontend/src/pages/GeneralExpensesPage.jsx:95-119`

**Problema:** El header tiene título "Gastos Generales" + 2 botones (`Exportar`, `Nuevo Gasto General`) en `flex items-center justify-between`. En móvil < 400px, los botones con texto no caben junto al título.

**Solución propuesta:**
1. Botones full-width apilados debajo del título en móvil
2. O usar botones de ícono en móvil (download para exportar, + para nuevo)

---

### A8. ProfilePage — Grid de presupuesto de 3 columnas

**Archivo:** `frontend/src/pages/ProfilePage.jsx:138-169`

**Problema:** Las cifras del ciclo (`Monto`, `Gastado`, `Restante`) usan `grid grid-cols-3 gap-4`. En móvil de 320px, 3 columnas con ~95px cada una apenas caben, pero los montos con formato `$12,345.67` se cortan.

**Solución propuesta:**
1. Cambiar a `grid grid-cols-1 sm:grid-cols-3 gap-4` — apilar verticalmente en móvil

---

## 🟡 MEDIO — Mejorable

### M1. Modal — Padding interno fijo

**Archivo:** `frontend/src/components/Modal.jsx:24,46`

**Problema:** El header usa `px-6 py-4` y el body hereda padding del consumer. En pantallas ≤ 360px, 24px de padding a cada lado deja solo ~312px para contenido. Con `max-w-lg` (512px) esto no es problema en desktop, pero en móviles pequeños reduce el espacio útil.

**Solución propuesta:**
1. Header: `px-4 sm:px-6 py-3 sm:py-4`
2. Documentar que los consumidores usen `px-4 sm:px-6` en el body

---

### M2. UploadTicketModal / GeneralExpenseModal — Drop zone grande en móvil

**Archivos:**
- `frontend/src/components/UploadTicketModal.jsx:294-368`
- `frontend/src/components/GeneralExpenseModal.jsx:197-272`

**Problema:** La drop zone del archivo tiene `px-6 py-7` (padding Y generoso). En móvil, esto ocupa ~180px de alto en la pantalla sin mostrar información útil, empujando los botones de acción fuera del viewport.

**Solución propuesta:**
1. Reducir padding vertical en móvil: `py-4 sm:py-7`

---

### M3. HomePage AdminHome — Tarjetas muy altas

**Archivo:** `frontend/src/pages/HomePage.jsx:56-90`

**Problema:** Las `SectionCard` tienen ícono grande (48px), título, descripción y padding generoso. En móvil con 1 columna, 4 tarjetas ocupan ~600px de scroll vertical. El usuario tiene que hacer scroll para ver el panel de validación.

**Solución propuesta:**
1. Reducir tamaño de ícono en móvil: `h-10 w-10 sm:h-12 sm:w-12`
2. Reducir padding: `p-4 sm:p-6`

---

### M4. Sidebar — Altura de taps de navegación

**Archivo:** `frontend/src/components/Sidebar.jsx:88-118`

**Problema:** Los items del NavLink usan `py-2.5` (10px vertical). En móvil, para cumplir con el mínimo recomendado de 44px de altura touch target (WCAG 2.5.5), con ícono de 20px + padding vertical de 10px = ~40px total. Queda apenas por debajo del mínimo.

**Solución propuesta:**
1. Aumentar a `py-3` en móvil para llegar a 44px mínimo
2. El drawer móvil es el principal medio de navegación — la accesibilidad táctil es crítica aquí

---

### M5. GeneralExpensesExportModal — Checkboxes con labels

**Archivo:** `frontend/src/components/GeneralExpensesExportModal.jsx:89-105`

**Problema:** Los checkboxes de meses usan `grid grid-cols-2 sm:grid-cols-3`. En pantallas de 320px, 2 columnas de ~140px cada una con labels como "Septiembre 2025" apenas caben.

**Solución propuesta:**
1. Labels más cortos: usar formato abreviado `"Sep 2025"` en móvil

---

### M6. Filtros sin botón "Limpiar filtros"

**Archivos afectados:**
- `frontend/src/components/TransactionTable.jsx` (filtros de creador, marca, prioridad, estado)
- `frontend/src/components/DateRangeFilter.jsx` (fechas)

**Problema:** No existe un botón para resetear todos los filtros a sus valores por defecto. En móvil, donde cada interacción es más costosa, limpiar 4 campos manualmente es tedioso.

**Solución propuesta:**
1. Agregar botón "Limpiar filtros" al lado de los filtros
2. En móvil: ícono de X o escoba

---

## 🟢 BAJO — Pulido visual

### B1. CreatorList — Avatar con iniciales en tarjeta

**Archivo:** `frontend/src/components/CreatorList.jsx:126-137`

**Problema:** El círculo naranja con iniciales usa `h-10 w-10 text-sm`. Funciona bien, sin cambios necesarios. Muy menor: la fuente `text-sm` en un círculo de 40px para iniciales de 2 letras como "MR" es legible.

---

### B2. LoginPage — Sin fondo decorativo en móvil

**Archivo:** `frontend/src/pages/LoginPage.jsx:37-108`

**Problema:** La página de login es minimalista: logo + formulario centrado. Se ve bien en móvil. Lo único: el `BrandLogo` con `h-28` (112px) ocupa ~30% de la pantalla en móviles pequeños. Se podría reducir a `h-20 sm:h-28`.

---

### B3. Header — Título "Grupo Ortiz" se oculta correctamente

**Archivo:** `frontend/src/components/Header.jsx:26-33`

**Problema:** Usa `hidden sm:block` para ocultar el texto en móvil, dejando solo el logo + hamburguesa + theme toggle + perfil. Correcto. Sin cambios necesarios.

---

### B4. LoadingScreen — Frase centrada

**Archivo:** `frontend/src/components/LoadingScreen.jsx:38-88`

**Problema:** El texto de frase animada está centrado y usa `max-w-sm` para el mensaje offline. Funciona bien en móvil. Sin cambios necesarios.

---

### B5. ThemeToggle — Tamaño de tap target

**Archivo:** `frontend/src/components/ThemeToggle.jsx:7-33`

**Problema:** El botón usa `h-9 w-9` (36px). El mínimo recomendado es 44px (WCAG). En desktop con mouse esto es aceptable, pero en móvil es pequeño.

**Solución propuesta:**
1. Aumentar a `h-10 w-10 sm:h-9 sm:w-9` para mejor touch target en móvil

---

## Plan de implementación por fases

### Fase 1 — Críticos (ataque inmediato, ~3-4 horas)

| Orden | Issue | Archivo(s) | Estimación |
|---|---|---|---|
| 1 | C1: Indicador de scroll en tablas | 5 archivos de tablas | 1.5h |
| 2 | C2: Botones de acción → menú ⋯ | TransactionTable, ValidationQueue, AdminView, UserManagement | 1.5h |
| 3 | C3: Texto "Resetear contraseña" abreviado | UserManagement.jsx | 15min |
| 4 | C4: Date inputs responsivos | DateRangeFilter.jsx | 30min |

### Fase 2 — Altos (mejora sustancial, ~3-4 horas)

| Orden | Issue | Archivo(s) | Estimación |
|---|---|---|---|
| 5 | A1: KPI font size responsivo | KpiCard.jsx | 15min |
| 6 | A2: Dashboard grid 4 KPIs segunda fila | Dashboard.jsx | 30min |
| 7 | A3: Altura responsiva de gráficas | 5 chart components + apexTheme.js | 1h |
| 8 | A4: Filtros min-width responsivo | TransactionTable.jsx | 45min |
| 9 | A5: Pestañas AdminView responsivas | AdminView.jsx | 30min |
| 10 | A6: Paginación compacta en móvil | TransactionTable.jsx | 45min |
| 11 | A7: Botones header GeneralExpenses | GeneralExpensesPage.jsx | 30min |
| 12 | A8: ProfilePage grid budget responsivo | ProfilePage.jsx | 15min |

### Fase 3 — Medios (pulido de experiencia, ~2-3 horas)

| Orden | Issue | Archivo(s) | Estimación |
|---|---|---|---|
| 13 | M1: Modal padding responsivo | Modal.jsx + consumidores | 45min |
| 14 | M2: Drop zone padding responsivo | UploadTicketModal, GeneralExpenseModal | 20min |
| 15 | M3: HomePage tarjetas compactas | HomePage.jsx | 30min |
| 16 | M4: Sidebar touch target 44px | Sidebar.jsx | 15min |
| 17 | M5: Labels de meses abreviados | GeneralExpensesExportModal.jsx | 15min |
| 18 | M6: Botón limpiar filtros | TransactionTable.jsx, DateRangeFilter.jsx | 1h |

### Fase 4 — Bajos (detalles finales, ~1 hora)

| Orden | Issue | Archivo(s) | Estimación |
|---|---|---|---|
| 19 | B1: Login logo más pequeño en móvil | LoginPage.jsx | 10min |
| 20 | B2: ThemeToggle touch target | ThemeToggle.jsx | 10min |
| 21 | Revisión general | Todos los archivos | 30min |

---

## Estrategia técnica recomendada

### Detección de móvil

Usar un hook personalizado en vez de depender solo de breakpoints CSS:

```jsx
// frontend/src/hooks/useMobile.js (nuevo)
import { useState, useEffect } from "react";

export function useMobile(breakpoint = 640) {
  const [isMobile, setIsMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth < breakpoint : false
  );

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpoint]);

  return isMobile;
}
```

Usar para:
- Cambiar altura de gráficas (`height={isMobile ? 220 : 320}`)
- Mostrar/ocultar etiquetas de texto en botones
- Alternar entre tabla y vista de cards

### Patrón de menú de acciones por fila

Para resolver C2, crear un componente `RowActions`:

```jsx
// frontend/src/components/RowActions.jsx (nuevo)
// En desktop: botones horizontales
// En móvil: botón ⋯ que abre un dropdown con las acciones
```

### Card stacking para tablas en móvil

Para C1, como alternativa al scroll horizontal, crear una variante responsive de `go-table`:

```css
/* En móvil, cada fila se convierte en una tarjeta */
@media (max-width: 639px) {
  .go-table-responsive tbody tr {
    display: flex;
    flex-direction: column;
    padding: 12px;
    border-bottom: 2px solid var(--go-border);
  }
  .go-table-responsive td {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
  }
  .go-table-responsive td::before {
    content: attr(data-label);
    font-weight: 600;
    color: var(--go-text-secondary);
  }
}
```

---

## Notas para el agente implementador

1. **Probar en 4 breakpoints reales:** 320px (iPhone SE), 375px (iPhone 12), 414px (iPhone 14 Pro Max), 768px (iPad Mini)
2. **No uses `display: none` para ocultar columnas** sin proporcionar una alternativa (el dato debe ser accesible en el menú ⋯ o en vista expandida)
3. **No hagas las tablas ilegibles** — el scroll horizontal es preferible a texto cortado o columnas desaparecidas sin alternativa
4. **Las gráficas de ApexCharts** ya son responsive por ancho (`width="100%"`), solo ajustar altura
5. **Nunca asignar `stroke`/`fill`/`plotOptions`/`responsive` como `undefined` explícito** en ApexCharts (regla del proyecto — ver CLAUDE.md)
6. **Probar light y dark theme** en cada cambio — las variables CSS deben funcionar en ambos
7. **No romper la funcionalidad desktop** al hacer cambios mobile-first
8. **Usar las clases de Tailwind** para responsividad (`sm:`, `md:`, `lg:`) siempre que sea posible en vez de JS
9. **Commits separados por fase** — cada fase debe ser autocontenida y no romper los tests existentes
10. **Correr `npm run build` antes de commit** para verificar que no hay errores de compilación
