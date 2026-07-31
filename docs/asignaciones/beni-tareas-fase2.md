# Beni — Tareas Fase 2: Header glow, Dashboard split, Mobile QA

> Rama: `BeniBranch`
> Fecha: 2026-07-31
> Base: `master` ya incluye overhaul RBAC + liquid glass en todo Presupuestos y Equipos

---

## C1 ✨ Header con iluminación líquida al hover

### Objetivo

El Header actual tiene glass estático (`glass` + `borderRadius: 0` + `boxShadow: none`). Se busca un efecto de "cristal iluminado" que reaccione al mouse: un degradado de luz que se mueva siguiendo el cursor, simulando que detrás del header hay una fuente de luz o imagen que se difumina a través del cristal.

### Especificación técnica

**Archivo**: `frontend/src/modules/presupuestos/components/Header.jsx`

Agregar un pseudo-elemento o div overlay que:
1. Use un `radial-gradient` con centro en la posición del mouse
2. El gradiente sea sutil: blanco semitransparente en el centro (~8-10% opacity), desvaneciendo a transparente en los bordes
3. Se actualice vía `onMouseMove` en el header, calculando la posición relativa del cursor (porcentaje X e Y)
4. Transición suave cuando el mouse sale (`onMouseLeave`): el glow se desvanece en ~400ms
5. Todo el efecto debe estar debajo del contenido del header (texto, botones) pero sobre el fondo glass

### Implementación sugerida

```jsx
// Hook dentro de Header
const headerRef = useRef(null);
const [glowPos, setGlowPos] = useState({ x: 0.5, y: 0.5, active: false });

function handleMouseMove(e) {
  const rect = headerRef.current.getBoundingClientRect();
  setGlowPos({
    x: (e.clientX - rect.left) / rect.width,
    y: (e.clientY - rect.top) / rect.height,
    active: true,
  });
}

function handleMouseLeave() {
  setGlowPos(prev => ({ ...prev, active: false }));
}
```

El overlay:
```html
<div
  className="pointer-events-none absolute inset-0 transition-opacity duration-500"
  style={{
    opacity: glowPos.active ? 1 : 0,
    background: `radial-gradient(circle at ${glowPos.x * 100}% ${glowPos.y * 100}%, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.03) 40%, transparent 70%)`,
  }}
/>
```

### Notas
- Respetar `prefers-reduced-motion`: si está activo, el glow se mantiene estático al centro
- El overlay debe ser `pointer-events: none` para no interferir con clics
- La iluminación es sutil — no un spotlight agresivo. Es un "brillo de cristal", no una linterna
- Mismo efecto para ambos temas (oscuro/claro). En light mode, usar `rgba(0,0,0,0.04)` en vez de blanco

---

## C2 📊 Separar Inicio y Dashboard en Equipos

### Objetivo

Actualmente `/equipos` (InicioPage) tiene KPIs, gráficas ApexCharts, donuts — todo mezclado. El módulo de Presupuestos tiene esta separación clara:
- **Inicio** (`/` → HomePage): cards de acceso rápido (Dashboard, Creadores, Transacciones, etc.)
- **Dashboard** (`/dashboard` → Dashboard): fecha, KPIs, gráficas ApexCharts, exportación PDF

Equipos debe replicar ese patrón.

### Cambios requeridos

#### 2.1 Nueva ruta: `/equipos/dashboard`

**Archivo**: `frontend/src/App.jsx` (línea ~63-78)

Agregar ruta hija dentro de `<Route path="/equipos" element={<EquiposLayout />}>`:

```jsx
<Route path="dashboard" element={<DashboardEquiposPage />} />
```

Agregar el lazy import correspondiente:
```jsx
const DashboardEquiposPage = lazy(() => import("./modules/equipos/pages/DashboardEquiposPage"));
```

#### 2.2 Nueva página: `DashboardEquiposPage.jsx`

**Archivo**: `frontend/src/modules/equipos/pages/DashboardEquiposPage.jsx`

Esta página toma el contenido ANALÍTICO actual de InicioPage y lo expande:

| Sección | Contenido | Origen |
|---------|-----------|--------|
| Filtro de fechas | DateRangeFilter (desde/hasta + presets) + botón Exportar | Nuevo (patrón: `Dashboard.jsx`) |
| KPIs | 5 KPI tiles: Prestados, Atrasados, Pend. confirmación, Disponibles, Tiempo promedio | Migrar de InicioPage |
| Préstamos por mes | LoansByMonthChart | Migrar de InicioPage |
| Top equipos + Devolución | 2-column: TopEquipmentChart + StatusDonut (tasa devolución) | Migrar de InicioPage |
| Distribución de estados | StatusDonut | Migrar de InicioPage |

**Datasource**: mismos endpoints que InicioPage actual (`fetchEquipmentDashboard`, `fetchLoans`)

**Patrón de referencia**: `frontend/src/modules/presupuestos/components/Dashboard.jsx`

#### 2.3 Simplificar `InicioPage.jsx`

**Archivo**: `frontend/src/modules/equipos/pages/InicioPage.jsx`

Reescribir para que sea SOLO cards de acceso rápido, como Presupuestos' HomePage:

```jsx
const EQUIPOS_SECTIONS = [
  { to: "/equipos/dashboard", title: "Dashboard", description: "KPIs, gráficas y tendencias de préstamos.", icon: "..." },
  { to: "/equipos/inventario", title: "Inventario", description: "Catálogo de equipos disponible.", icon: "..." },
  { to: "/equipos/nuevo", title: "Nuevo préstamo", description: "Solicitar equipo con firma y fotos.", icon: "..." },
  { to: "/equipos/activos", title: "Préstamos activos", description: "Equipos prestados actualmente.", icon: "..." },
  { to: "/equipos/aprobaciones", title: "Aprobaciones", description: "Autorizar entregas y confirmar devoluciones.", icon: "..." },
  { to: "/equipos/historial", title: "Historial", description: "Registro completo de préstamos.", icon: "..." },
];
```

Estructura: grid de cards (2 columnas en desktop, 1 en mobile) usando `GlassPanel` como tarjeta. Mismo patrón que `SectionCard` de `HomePage.jsx`.

#### 2.4 Actualizar EquiposSidebar

**Archivo**: `frontend/src/modules/equipos/components/EquiposSidebar.jsx`

Agregar item "Dashboard" a `NAV_ITEMS`, entre "Inicio" y "Inventario":

```javascript
{
  to: "/equipos/dashboard",
  label: "Dashboard",
  icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
  permiso: ["equipos_inventario", "ver"],
},
```

### Verificación

- [ ] `/equipos` → cards de acceso rápido (sin gráficas)
- [ ] `/equipos/dashboard` → filtro fechas + KPIs + gráficas + exportación
- [ ] Sidebar muestra "Dashboard" entre Inicio e Inventario
- [ ] El nuevo Dashboard usa `GlassPanel` en filtros y secciones de gráficas
- [ ] La nueva Inicio usa `GlassPanel` en las cards de acceso rápido
- [ ] Ambas páginas usan los mismos endpoints sin duplicar lógica de fetch

---

## C3 📱 Responsividad móvil completa

### Objetivo

Asegurar que TODAS las vistas de Equipos funcionen correctamente en viewport 320-428px (iPhone SE a iPhone Pro Max).

### Checklist por página

| Página | Verificaciones |
|--------|---------------|
| **InicioPage** (nueva) | Grid de cards: `grid-cols-1 sm:grid-cols-2`. A 320px: 1 columna, sin overflow. Cards con padding `p-4`. |
| **DashboardEquiposPage** (nueva) | KPIs: `grid-cols-2 lg:grid-cols-5`. Filtro fechas: inputs date sin desbordar. Charts: ApexCharts responsive con `useMobile` para altura. |
| **InventarioPage** | Grid rejilla: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`. Tabla: `go-table-scroll-wrapper`. Filtros: `flex-wrap`. |
| **NuevoPrestamoPage** | Stepper: labels ocultas en mobile, sin overflow horizontal. Paso 2: 2 columnas colapsan a 1. Fotos: `grid-cols-2` mínimo. Firmas: `max-w-xl`. |
| **ActivosPage** | Tabla: `go-table-scroll-wrapper`. Filtros: `flex-wrap`. Paginación: botones accesibles (min 44px touch target). |
| **AprobacionesPage** | Cards de items: `flex-wrap`, botones no se enciman. Sin overflow. |
| **HistorialPage** | 4 filtros: colapsan correctamente en mobile. Tabla: `go-table-scroll-wrapper`. |
| **FichaPrestamoPage** | Grid datos: `grid-cols-2`. Miniaturas: `flex-wrap`. Timeline: sin overflow. GlassModal: fullscreen en mobile. |

### Reglas

- **Tablas**: siempre envueltas en `go-table-scroll-wrapper` + `go-table-scroll`
- **Touch targets**: mínimo 44×44px para botones interactivos
- **No horizontal overflow**: ningún elemento debe causar scroll horizontal en la página
- **`useMobile(breakpoint)`**: usar para valores JS (altura de charts), NO para layout (usar Tailwind `sm:`/`md:`/`lg:`)
- **`RowActions`**: verificar que todas las tablas con acciones lo usen

---

## Resumen

| # | Tarea | Esfuerzo |
|---|-------|----------|
| C1 | Header glow al hover | Bajo (1 archivo, CSS + hook) |
| C2 | Split Inicio/Dashboard en Equipos | Alto (3 archivos nuevos, 3 modificados) |
| C3 | QA Mobile completo | Medio (testing + fixes puntuales) |
