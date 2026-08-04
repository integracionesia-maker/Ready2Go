# Prompt: Unificación visual de Equipos con Presupuestos

> **Objetivo**: Que el módulo de Equipos se vea, navegue y se comporte exactamente como el
> módulo de Presupuestos — un solo proyecto unificado, no dos apps pegadas con cinta.
>
> **Rama objetivo**: `dami-branch`
> **Fecha**: 2026-07-30
> **Para**: Agente especializado de implementación (no ejecutar sin revisión humana)
>
> ⚠️ **ESTE PROMPT ES SOLO INSTRUCCIONES. No implementes nada directamente.**
> Entrégalo al agente especializado.

---

## 1. Diagnóstico: qué está roto

### 1.1 Arquitectura actual (cómo funciona hoy)

```
App.jsx
├── /login → LoginPage
└── ProtectedRoute
    └── AppShell                              ← ModuleTabs (Presupuestos | Equipos) + Outlet
        ├── /equipos/* → EquiposLayout        ← SOLO pt-16 + container + EquiposSubNav + Outlet
        │   ├── / → InicioPage
        │   ├── /inventario → InventarioPage
        │   ├── /nuevo → NuevoPrestamoPage
        │   ├── /activos → ActivosPage
        │   ├── /aprobaciones → AprobacionesPage
        │   ├── /historial → HistorialPage
        │   └── /prestamo/:folio → FichaPrestamoPage
        └── /* → PresupuestosLayout           ← Header + Sidebar + main + Outlet
            ├── / → HomePage
            ├── /dashboard → Dashboard
            ├── /creadores → CreatorList
            ├── /transacciones → TransactionTable
            ├── /validacion → ValidationQueue
            ├── /gastos-generales → GeneralExpensesPage
            ├── /administracion → AdminView
            ├── /perfil → ProfilePage
            └── /403 → ForbiddenPage
```

**Problema raíz**: `PresupuestosLayout` tiene el **chrome completo** (Header fijo + Sidebar colapsable + área de contenido con offset). `EquiposLayout` es un cascarón vacío — solo `pt-16` para despejar los ModuleTabs del shell, un contenedor `max-w-7xl`, y un `EquiposSubNav` inline. **No tiene Header, no tiene Sidebar, no tiene nada del chrome de la app.**

Esto hace que Presupuestos y Equipos parezcan dos aplicaciones completamente distintas aunque comparten:
- Misma app React, mismo Vite bundle
- Mismo sistema de diseño (tokens CSS, clases go-*, GlassNav)
- Mismo backend, misma sesión, mismos roles
- Mismos componentes compartidos (`@/design`)

### 1.2 Lo que SÍ está bien en Equipos (no tocar)

Las páginas individuales de Equipos ya usan correctamente:
- **Clases del design system**: `btn-go`, `btn-go-ghost`, `go-card`, `go-input`, `go-select`, `go-badge`, `go-eyebrow`, `go-table`, `go-table-scroll-wrapper`, `go-table-scroll`
- **Variables CSS**: `var(--go-bg)`, `var(--go-surface)`, `var(--go-text-primary)`, `var(--go-orange)`, `var(--go-border)`, `var(--go-text-secondary)`, `var(--go-text-muted)`, `var(--go-error)`
- **Tipografía correcta**: `font-display` para headings, `font-body` para texto, `font-mono` para folios/fechas/cifras
- **Componentes compartidos**: `EmptyState`, `SkeletonShimmer`, `RowActions`, `KpiTile`, `StatusDonut`, `Timeline`, `GlassModal`, `useToast`, `useMobile`
- **Patrones de estado**: loading → skeleton, error → banner rojo `var(--go-error)`, vacío → `EmptyState`, 503 `PERMISOS_NO_DISPONIBLES` → reintentar
- **Responsividad móvil**: `go-table-scroll-wrapper` + `RowActions` + clases `sm:`/`md:`/`lg:`

**Esto NO se toca.** El problema no está en las páginas — está en la cáscara que las envuelve.

---

## 2. Especificación detallada de cambios

### 2.1 NUEVO componente: `EquiposSidebar.jsx`

Crear `frontend/src/modules/equipos/components/EquiposSidebar.jsx`.

**Debe ser estructuralmente IDÉNTICO a `Presupuestos/components/Sidebar.jsx`** (mismos dimensiones, mismos tokens CSS, mismo comportamiento colapsable, mismo drawer móvil con backdrop). La única diferencia: los items de navegación son los de Equipos, no los de Presupuestos.

#### Especificaciones precisas:

```jsx
// ── Dimensiones y posicionamiento ──────────────────────────────
// - fixed, left-0, top-16, z-40
// - altura: h-[calc(100%-4rem)]
// - ancho expandido: w-60 (240px)
// - ancho colapsado: md:w-16 (64px)
// - transición: transition-all duration-300
// - border-right, mismo color de borde que Presupuestos
// - fondo: var(--go-surface), borde: var(--go-border)

// ── Props ──────────────────────────────────────────────────────
// collapsed, onToggle, mobileOpen, onCloseMobile
// NO recibe onNewTicket ni pendingCount (son específicos de Presupuestos)

// ── Comportamiento móvil ───────────────────────────────────────
// - <md: drawer oculto con translate-x: -translate-x-full
// - mobileOpen: translate-x-0
// - Backdrop: div fixed inset-0 z-30 md:hidden con fondo var(--go-overlay)
// - onClick en backdrop → onCloseMobile
// - Cada NavLink llama onCloseMobile al hacer click

// ── Toggle de colapso ──────────────────────────────────────────
// - Botón en la parte inferior, solo visible en md:flex
// - Ícono de chevron que rota 180° cuando collapsed
// - Mismo borde superior, mismo hover, misma transición
```

#### Items de navegación (usar `usePermisos` para filtrar):

```javascript
const NAV_ITEMS = [
  {
    to: "/equipos",
    end: true,
    label: "Inicio",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
    permiso: ["equipos_inventario", "ver"],
  },
  {
    to: "/equipos/inventario",
    label: "Inventario",
    icon: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
    permiso: ["equipos_inventario", "ver"],
  },
  {
    to: "/equipos/nuevo",
    label: "Nuevo préstamo",
    icon: "M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_prestamos", "solicitar"],
  },
  {
    to: "/equipos/activos",
    label: "Activos",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_prestamos", "ver_propios"],
  },
  {
    to: "/equipos/aprobaciones",
    label: "Aprobaciones",
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_aprobacion", "autorizar_entrega"],  // o confirmar_devolucion, o cerrar_incidencia
  },
  {
    to: "/equipos/historial",
    label: "Historial",
    icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
    permiso: ["equipos_prestamos", "ver_propios"],
  },
];
```

#### Estilo de cada NavLink (EXACTAMENTE igual a Presupuestos):

```jsx
<NavLink
  to={item.to}
  end={item.end}
  title={item.label}
  onClick={onCloseMobile}
  className="flex items-center gap-3 rounded-go px-3 py-3 md:py-2.5 font-display text-sm font-semibold tracking-wide transition-all duration-200"
  style={({ isActive }) => ({
    background: isActive ? "var(--go-surface-sunken)" : "transparent",
    color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)",
  })}
>
  <svg className="h-5 w-5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
  </svg>
  <span className={`${collapsed ? "md:hidden" : ""} truncate flex-1`}>{item.label}</span>
</NavLink>
```

#### Filtrado por permisos:

```javascript
const { puede } = usePermisos();

const visibleItems = NAV_ITEMS.filter((item) => {
  // Si el item requiere múltiples permisos (aprobaciones), basta con tener al menos uno
  if (Array.isArray(item.permiso[0])) {
    return item.permiso.some(([mod, acc]) => puede(mod, acc));
  }
  return puede(item.permiso[0], item.permiso[1]);
});
```

Para el ítem de Aprobaciones, el permiso debe ser un OR: mostrar la pestaña si el usuario puede `autorizar_entrega` O `confirmar_devolucion` O `cerrar_incidencia`. Cualquiera de los tres abre la página; dentro, las colas individuales ya se esconden si el permiso específico falta.

#### Ítem de perfil (solo móvil):

```javascript
const PROFILE_ITEM = {
  to: "/equipos/perfil",  // o la ruta de perfil que corresponda
  label: "Mi Perfil",
  icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
};
```

Mismo patrón: visible solo en `md:hidden`, mismo estilo que los demás items.

#### Botón "Nuevo préstamo" en la parte inferior:

Reemplaza al botón "Nuevo Ticket" de Presupuestos:

```jsx
<div className="px-2.5 pb-3">
  <RequierePermiso modulo="equipos_prestamos" accion="solicitar">
    <Link
      to="/equipos/nuevo"
      title="Nuevo préstamo"
      className={`btn-go w-full ${collapsed ? "justify-center px-0" : "justify-center px-0 md:justify-start md:px-5"}`}
      onClick={onCloseMobile}
    >
      <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
      </svg>
      <span className={collapsed ? "md:hidden" : ""}>Nuevo préstamo</span>
    </Link>
  </RequierePermiso>
</div>
```

### 2.2 MODIFICAR: `EquiposLayout.jsx`

Reescribir completamente para que sea estructuralmente idéntico a `PresupuestosLayout.jsx`.

```jsx
import { Outlet } from "react-router-dom";
import Header from "@/modules/presupuestos/components/Header";  // ← REUSAR, no duplicar
import EquiposSidebar from "../components/EquiposSidebar";

export default function EquiposLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed-equipos") === "true"
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed-equipos", next ? "true" : "false");
      return next;
    });
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--go-bg)" }}>
      <Header onOpenMobileMenu={() => setMobileMenuOpen(true)} />
      <EquiposSidebar
        collapsed={sidebarCollapsed}
        onToggle={handleToggleSidebar}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <main
        className={`min-h-screen pt-16 transition-all duration-300 ${
          sidebarCollapsed ? "md:ml-16" : "md:ml-60"
        }`}
      >
        <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

**Cambios clave vs el EquiposLayout actual:**
1. Agrega `<Header>` (reusando el componente existente de Presupuestos)
2. Reemplaza `<EquiposSubNav />` por `<EquiposSidebar />`
3. El `<main>` ahora tiene el mismo offset del sidebar (`md:ml-60` / `md:ml-16`)
4. La clave de localStorage usa sufijo diferente (`sidebar-collapsed-equipos`) para no pisar la preferencia de Presupuestos
5. Estado de colapso y menú móvil manejado igual que en Presupuestos

### 2.3 Header: hacerlo module-aware

El `Header.jsx` actual tiene hardcodeado:

```jsx
<h1>Grupo Ortiz</h1>
<p>Control de Presupuestos</p>
```

**Opción A (recomendada — mínimo cambio)**: Cambiar el subtítulo a algo genérico que funcione para ambos módulos:

```jsx
<p>GOCreate</p>
```

Esto requiere editar SOLO esa línea en `frontend/src/modules/presupuestos/components/Header.jsx`.

**Opción B (más elegante)**: Hacer que el Header reciba una prop `subtitle`:

```jsx
export default function Header({ onOpenMobileMenu, subtitle = "GOCreate" }) {
  // ...
  <p>{subtitle}</p>
}
```

Y cada Layout lo invoca con su subtítulo:
- `PresupuestosLayout`: `<Header ... subtitle="Control de Presupuestos" />`
- `EquiposLayout`: `<Header ... subtitle="Control de Equipos" />`

La Opción B es preferible si el tiempo lo permite. La Opción A es aceptable como quick win.

### 2.4 ELIMINAR o degradar: `EquiposSubNav.jsx`

Con el sidebar nuevo, `EquiposSubNav` se vuelve redundante. Hay dos caminos:

**Camino A (recomendado)**: Eliminar `EquiposSubNav` por completo. El sidebar ya provee toda la navegación.

**Camino B (transicional)**: Mantenerlo pero solo como navegación secundaria dentro de la página de Inicio (si hay sub-secciones dentro de una misma página que lo justifiquen).

Elige el Camino A a menos que haya una razón concreta para mantener sub-navegación inline.

### 2.5 Eliminar `EquiposSubNav` de `EquiposLayout`

Ya cubierto en 2.2 — el nuevo `EquiposLayout` no importa ni renderiza `EquiposSubNav`.

---

## 3. Verificación de consistencia página por página

Cada página de Equipos debe ser auditada contra estos criterios. Si algo falla, CORRÍGELO.

### 3.1 Checklist universal (aplica a TODAS las páginas)

- [ ] **Título de página**: `font-display text-lg font-bold uppercase tracking-[0.06em]` con color `var(--go-text-primary)`, contador en naranja `var(--go-orange)`.
- [ ] **Tarjeta de filtros**: `go-card` + `flex flex-wrap items-end gap-3`.
- [ ] **Labels de filtros**: `go-eyebrow mb-1.5 block`.
- [ ] **Inputs**: `go-input`.
- [ ] **Selects**: `go-select`.
- [ ] **Botones primarios**: `btn-go` (nunca inline styles para botones naranjas — ya existe la clase).
- [ ] **Botones secundarios/ghost**: `btn-go-ghost` (nunca inline styles para botones de borde).
- [ ] **Badges de estado**: `go-badge go-badge-success|warning|error|neutral`.
- [ ] **Tablas**: envueltas en `go-table-scroll-wrapper` > `overflow-x-auto rounded-go-lg border go-table-scroll` > `<table className="go-table w-full">`.
- [ ] **Celdas numéricas**: `font-mono` + `tabular-nums` (clase `num` de `go-table td.num`).
- [ ] **Estados**: loading → `SkeletonShimmer`, error → banner rojo con tokens `var(--go-error)` + fondo semitransparente, vacío → `EmptyState`, 503 → `EmptyState` con botón "Reintentar".
- [ ] **Paginación**: `btn-go-ghost text-xs px-3 py-1.5 disabled:opacity-40` para botones Anterior/Siguiente.

### 3.2 InicioPage (Dashboard de Equipos)

- ✅ Ya usa `KpiTile`, `StatusDonut`, `EmptyState`, `SkeletonShimmer`
- ✅ Ya usa `go-card` para las secciones
- ✅ Ya usa `font-mono` para cifras
- ⚠️ Verificar que los KPI tiles tengan `glass` donde corresponde (solo `pendientes_confirmacion`)
- ⚠️ Verificar que la página tenga título: "Inicio" o "Dashboard"
- **InventarioPage** — ya está bien. Revisar los botones de toggle rejilla/tabla: usan `btn-go`/`btn-go-ghost` correctamente.
- **AprobacionesPage** — ya está bien.
- **ActivosPage** — ya está bien.
- **HistorialPage** — ya está bien. El botón "Exportar CSV" usa `btn-go` correctamente.
- **NuevoPrestamoPage** — ya está bien. El stepper, los `go-card`, `go-input`, `go-select`, `btn-go`, `btn-go-ghost` están correctos.
- **FichaPrestamoPage** — ya está bien. Usa `GlassModal`, `Timeline`, `go-card`, badges y Miniaturas correctamente.

### 3.4 Componentes de Equipos a revisar

Revisar que estos componentes usen las clases del design system y no inline styles arbitrarios:

- `EquipmentCard.jsx`
- `EquipmentFormModal.jsx`
- `EquipmentAuditModal.jsx`
- `EquipmentFichaModal.jsx`
- `ConfirmarDevolucionModal.jsx`
- `CerrarIncidenciaModal.jsx`
- `RegistrarDevolucionModal.jsx`
- `AccesoriosPicker.jsx`
- `PhotoCapture.jsx`
- `SignaturePad.jsx`

---

## 4. Lo que NO se debe hacer

### 4.1 NO tocar Presupuestos

Los archivos bajo `frontend/src/modules/presupuestos/` no se modifican, excepto el cambio puntual en `Header.jsx` (2.3) para que el subtítulo sea genérico o parametrizable.

### 4.2 NO crear nuevos tokens CSS ni clases

Todas las clases necesarias YA EXISTEN en `index.css` y `tokens.css`:
- `btn-go`, `btn-go-ghost`, `go-card`, `go-input`, `go-select`, `go-badge-*`, `go-eyebrow`, `go-table`, `go-table-scroll-wrapper`, `go-table-scroll`
- Variables `--go-*` para colores, fondos, bordes, texto

NO inventar nuevas clases. NO agregar estilos inline que dupliquen lo que ya hace una clase `go-*`.

### 4.3 NO usar `:root` en selectores de tema

El tema claro usa `[data-theme="light"]` sin `:root` — esto es a propósito para que el PDF (R8) pueda forzar tema claro en un contenedor local sin afectar al `<html>`. No cambiar esto.

### 4.4 NO agregar imports estáticos de `jspdf`/`html2canvas`

Son dependencias de runtime cargadas con `import()` dinámico solo al descargar PDF. NoLas importes estáticamente.

### 4.5 NO usar estilos inline para botones

`btn-go` y `btn-go-ghost` ya existen. Si un botón necesita un color específico (ej. rojo para "Cerrar incidencia"), usa `style={{ color: "var(--go-error)" }}` como complemento, no reemplaces toda la clase.

### 4.6 NO romper el patrón glass

El cristal (`glass.css`) NO se aplica en:
- Tablas
- Contenedores con scroll
- Componentes que no tienen un velo sólido detrás del texto

---

## 5. Orden de implementación

1. **Crear `EquiposSidebar.jsx`** — copiar estructura de `Sidebar.jsx`, adaptar items de navegación y filtros de permisos.
2. **Modificar `Header.jsx`** — hacer el subtítulo genérico o parametrizable (Opción A o B de §2.3).
3. **Reescribir `EquiposLayout.jsx`** — agregar Header + EquiposSidebar + main con offset, eliminar EquiposSubNav.
4. **Eliminar `EquiposSubNav.jsx`** — ya no se usa.
5. **Auditar componentes modales de Equipos** — verificar que usen `GlassModal` donde aplique y clases `go-*` consistentemente.
6. **Auditar páginas de Equipos** — pasar la checklist de §3.1 en cada página, corregir cualquier inline style o clase incorrecta.
7. **Probar en móvil** — verificar que el sidebar colapsa a drawer con backdrop, que las tablas tienen scroll horizontal con `go-table-scroll-wrapper`, que `RowActions` funciona en cada tabla.
8. **Probar cambio de módulo** — navegar de Presupuestos a Equipos y viceversa con los ModuleTabs. Verificar que el sidebar correcto se muestra en cada módulo.

---

## 6. Referencias de archivos clave

| Archivo | Rol |
|---------|-----|
| `frontend/src/App.jsx` | Enrutador raíz — NO modificar |
| `frontend/src/shell/AppShell.jsx` | ModuleTabs + Outlet — NO modificar |
| `frontend/src/shell/ModuleTabs.jsx` | Navegación Presupuestos/Equipos — NO modificar |
| `frontend/src/shell/navItems.js` | Items del ModuleTabs — NO modificar |
| `frontend/src/modules/presupuestos/PresupuestosLayout.jsx` | **REFERENCIA** — así debe verse EquiposLayout |
| `frontend/src/modules/presupuestos/components/Header.jsx` | Header a REUSAR (con cambio de subtítulo) |
| `frontend/src/modules/presupuestos/components/Sidebar.jsx` | **REFERENCIA** — así debe verse EquiposSidebar |
| `frontend/src/modules/equipos/EquiposLayout.jsx` | **REESCRIBIR** — igualar a PresupuestosLayout |
| `frontend/src/modules/equipos/EquiposSubNav.jsx` | **ELIMINAR** — reemplazado por sidebar |
| `frontend/src/modules/equipos/components/` | Directorio para el NUEVO `EquiposSidebar.jsx` |
| `frontend/src/modules/equipos/pages/*.jsx` | Páginas a AUDITAR (checklist §3.1) |
| `frontend/src/modules/equipos/permisos/usePermisos.js` | Hook de permisos para filtrar items del sidebar |
| `frontend/src/design/tokens.css` | Variables CSS de diseño — NO modificar |
| `frontend/src/design/index.js` | Re-exports de componentes compartidos |
| `frontend/src/index.css` | Clases `go-*` del design system — NO modificar |
| `frontend/CLAUDE.md` | Convenciones de frontend |

---

## 7. Verificación final

Después de implementar, estas cosas deben ser verdad:

1. Navego a `/equipos` → veo el Header (logo + "Grupo Ortiz" + theme toggle + perfil) y el Sidebar con items de Equipos.
2. El sidebar de Equipos se colapsa/expande igual que el de Presupuestos, con preferencia independiente en localStorage.
3. En móvil, el sidebar es un drawer con backdrop que se abre con la hamburguesa del Header.
4. Los ModuleTabs (Presupuestos | Equipos) en el centro del Header cambian de módulo y cada módulo muestra su propio sidebar.
5. Todas las páginas de Equipos usan exclusivamente clases `go-*` y variables `--go-*` para estilos.
6. No hay `EquiposSubNav` inline — la navegación es solo por sidebar.
7. El subtítulo del Header refleja el módulo activo o es genérico ("GOCreate").
8. Ningún botón tiene estilos inline que dupliquen `btn-go` o `btn-go-ghost`.
9. Las tablas en móvil tienen el degradado de scroll horizontal (`go-table-scroll-wrapper`).
10. El cambio de tema (oscuro/claro) funciona en todas las páginas de Equipos sin inconsistencias.

---

## 8. Hallazgos adicionales de la auditoría (agente explorador)

Estos son detalles más finos encontrados por el agente que auditó todas las páginas de ambos módulos:

### 8.1 Jerarquía de headings inconsistente

- **Equipos**: usa `<h1>` para el título de página (ej. "Inventario", "Préstamos activos", "Historial")
- **Presupuestos**: usa `<h2>` para el título de página

**Corregir**: Uniformar a `<h1>` en ambos módulos (es el heading principal del contenido de la página). O alternativamente, si el Header ya tiene un `<h1>` (dice "Grupo Ortiz"), entonces ambos deberían usar `<h2>`. **Decisión: usar `<h1>` en el contenido de página** — el `<h1>` del Header es el nombre de la app, el de la página es el título del contenido.

### 8.2 Íconos SVG en botones de acción

- **Presupuestos**: los botones frecuentemente incluyen SVGs inline (ícono + texto). Ej: "Exportar" tiene ícono de descarga, "Nuevo Ticket" tiene `+`.
- **Equipos**: los botones generalmente son solo texto. Ej: "+ Nuevo equipo", "Exportar CSV", "Autorizar entrega".

**Corregir**: Agregar SVGs inline a los botones principales de Equipos donde tenga sentido:
- "Exportar CSV" → ícono de descarga
- "+ Nuevo equipo" → ícono de `+`
- "Autorizar entrega" → ícono de check
- "Confirmar devolución" → ícono de check doble
- "Cerrar incidencia" → ya usa `btn-go-ghost` correctamente, solo verificar consistencia

### 8.3 Paginación: dos patrones distintos

- **Presupuestos** (TransactionTable): select de page size (10/25/50/100) + "Mostrando X-Y de Z" + botones ← → + "Página N de M", todo integrado como footer de la tabla.
- **Equipos** (InventarioPage, ActivosPage, HistorialPage): solo botones "Anterior"/"Siguiente" + "Página N de M" debajo de la tabla, sin selector de page size ni rango "Mostrando X-Y de Z".

**Corregir**: Uniformar la paginación de Equipos al patrón de Presupuestos (el más completo). Agregar:
- Selector de `limit` (10/25/50/100) que actualice la URL y el offset
- Texto "Mostrando X-Y de Z"
- Mismo estilo visual (footer con `border-top: 1px solid var(--go-border)`, padding, fuentes)

### 8.4 Tablas sin ordenamiento en Equipos

- **Presupuestos** (TransactionTable): columnas ordenables con `SortableHeaderCell` + hook `useSortable`.
- **Equipos**: ninguna tabla tiene columnas ordenables.

**No implementar aún** — requiere tocar la API si el ordenamiento es server-side, o el hook `useSortable` si es client-side. Se deja como mejora futura (WP7 o similar). El prompt actual no lo pide.

### 8.5 Componente Modal duplicado

- **Equipos**: usa `GlassModal` de `@/design` (accesible, animado, con focus-trap)
- **Presupuestos**: usa `Modal` local de `./Modal` (más simple, sin focus-trap, sin animaciones)

**No tocar en este prompt** — migrar Presupuestos a `GlassModal` es un refactor separado que no rompe la unificación visual. Los modales de Equipos ya usan la versión correcta.

### 8.6 Contenedor de filtros

- **Equipos**: usa `go-card` (que aplica `var(--go-surface-raised)`)
- **Presupuestos**: usa `rounded-go-lg border p-4` con background explícito `var(--go-surface)`

La diferencia visual es mínima (un tono más claro en Equipos). **No es crítica**, pero si se quiere pixel-perfect, unificar a `go-card` en ambos.

### 8.7 Spinner de carga vs SkeletonShimmer

- **Equipos**: usa exclusivamente `SkeletonShimmer` para estados de carga
- **Presupuestos**: usa una mezcla — `SkeletonShimmer` para lazy-loading de rutas, pero un spinner CSS (`animate-spin`) para carga de datos

**Corregir**: No hay nada que corregir. `SkeletonShimmer` es superior para datos tabulares/de lista (da contexto visual). El spinner es aceptable para cargas pequeñas. Cada página debe usar lo que mejor comunique el estado — el prompt no prescribe uno sobre otro.

---

## 9. Notas para el agente implementador

1. **Este prompt describe CAMBIOS ESTRUCTURALES al layout de Equipos**, no cambios cosméticos a páginas individuales. Las páginas ya están bien construidas.

2. **La migración de Sidebar es el cambio más delicado.** Asegúrate de que:
   - Los permisos se resuelven igual que en `EquiposSubNav` (mismo `usePermisos`)
   - Los NavLink cierran el drawer móvil al navegar
   - El estado de colapso se persiste en una clave de localStorage distinta a la de Presupuestos
   - El botón "Nuevo préstamo" usa `<Link to="/equipos/nuevo">` (no onClick + modal como en Presupuestos)

3. **No modificar `App.jsx`** — las rutas existentes funcionan. Solo se cambia lo que hay DENTRO de `EquiposLayout`.

4. **No tocar ninguna página de Equipos** a menos que la checklist de §3.1 encuentre algo roto. Las páginas ya usan las clases correctas.

5. **Después de implementar, probar**: login → navegar a Equipos → verificar Header, Sidebar, colapso, móvil, cambio de tema, navegación entre páginas de Equipos, cambio a Presupuestos y vuelta.
