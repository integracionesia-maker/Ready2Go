# Beni — Bugs y tareas post-unificación visual

> Rama: `BeniBranch` (ya actualizada con master, commit `afdd87c`)
> Fecha: 2026-07-30
> Backend: `dami-branch` → `master` (ya mergeado)

---

## B1 🐛 Sidebar de Equipos vacío al iniciar sesión

**Síntoma**: Al iniciar sesión y navegar a `/equipos`, el sidebar izquierdo no muestra ítems. Presupuestos funciona bien.

**Causa raíz**:

`POST /api/auth/login` devuelve `UserResponse` con `permisos: {}` por diseño — solo `GET /api/auth/me` los llena (`backend/app/routers/auth.py:166-175`). `EquiposSidebar` usa `usePermisos()` que depende de `user.permisos`. El `Sidebar` de Presupuestos no tiene el problema porque filtra por `user.role`, no por permisos RBAC.

**Fix** (`frontend/src/context/AuthContext.jsx`, ~3 líneas):

```js
// Después de setUser(loggedInUser) en login(), llamar fetchMe()
const login = useCallback(async (identificador, password) => {
    const { user: loggedInUser } = await apiLogin(identificador, password);
    setUser(loggedInUser);                  // respuesta rápida (sin permisos)
    const me = await fetchMe();             // permisos reales desde /auth/me
    setUser(me);
    return me;
}, []);
```

---

## B2 🎨 Íconos SVG en botones de acción

Los botones de acción en ambas secciones son texto plano. `RowActions` (`frontend/src/design/RowActions.jsx`) solo acepta `{ key, label, onClick, variant? }` — no tiene prop para íconos.

### Cambios

**1. `RowActions.jsx`** — Agregar prop opcional `icon` (string SVG path, mismo formato que `Sidebar.jsx`). Desktop: `<svg>` + label. Móvil (menú `⋯`): icon + label.

**2. Equipos** — Pasar `icon` en cada `RowActions`:

| Acción | SVG path |
|--------|----------|
| Ver ficha | `M15 12a3 3 0 11-6 0 3 3 0 016 0zm-3 7a9 9 0 100-18 9 9 0 000 18z` |
| Editar | `M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z` |
| Eliminar | `M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16` |
| Auditar | `M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4` |
| Registrar devolución | `M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3` |
| Ver responsiva | `M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z` |

**3. Presupuestos** — Mismos íconos en sus `RowActions` para consistencia.

**4. Botones standalone** — Agregar `<svg>` inline a: "Exportar CSV", "+ Nuevo equipo", "Autorizar entrega", "Confirmar devolución".

> ⚠️ NO usar emojis. Todo SVG inline (patrón: `Sidebar.jsx` líneas 5-56).

---

## B3 📊 Dashboard de Equipos (nueva vista)

`InicioPage.jsx` tiene 4 KPIs + donut. El Dashboard de Presupuestos (`Dashboard.jsx`) es mucho más completo: ApexCharts con tendencias, barras, gasto por marca.

**Endpoint actual**: `GET /api/equipos/dashboard`
```json
{ "prestados": int, "atrasados": int, "pendientes_confirmacion": int,
  "disponibles": int, "por_estado": {...}, "requiere_atencion": [...] }
```

**Dashboard propuesto**:

| Sección | Contenido | Datos necesarios |
|---------|-----------|------------------|
| Fila KPIs | Los 4 actuales (OK) | Ya existe |
| Préstamos por mes | Barras ApexCharts | `GET /loans/` con filtro de fechas, o nuevo endpoint |
| Top equipos prestados | Barras horizontales (top 5-10) | Agregar a endpoint dashboard o procesar loans |
| Tasa de devolución | % completados a tiempo vs atrasados. Donut. | Ya existe en `por_estado` |
| Tiempo promedio | KPI: días promedio de préstamo activo | Procesar loans activos |

Si el backend no tiene los endpoints, coordinar con backend. Puede implementarse con datos mock o procesando `GET /loans/` en el cliente mientras tanto.

---

## B4 📱 Responsividad móvil

Infraestructura ya lista: `useMobile` (`frontend/src/design/useMobile.js`), `RowActions`, `go-table-scroll-wrapper`. Detalle en `docs/presupuestos/responsividad-movil.md`.

### Checklist por página

| Página | Verificar |
|--------|-----------|
| `InicioPage` | KPIs `grid-cols-2 lg:grid-cols-4`. Donut + lista en `lg:grid-cols-2`. ¿Se apilan bien en 320px? |
| `InventarioPage` | Grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`. Tabla con `go-table-scroll-wrapper`. |
| `NuevoPrestamoPage` | Paso 2: `lg:grid-cols-2` se apila en móvil. Stepper: overflow-x sin desbordar página. |
| `ActivosPage` | Filtros `flex-wrap`. Tabla con `go-table-scroll-wrapper`. |
| `AprobacionesPage` | Cards con `flex-wrap`, sin tabla. |
| `HistorialPage` | 4 campos de filtro + tabla con scroll wrapper. |
| `FichaPrestamoPage` | Grid datos `grid-cols-2 lg:grid-cols-3`. Miniaturas `flex-wrap`. Timeline. |

**Probar en**: 320×568 (iPhone SE) y 375×812 (iPhone X). Reportar y arreglar cualquier overflow horizontal, botón cortado, o texto ilegible.

---

## B5 ✨ Liquid Glass / estilo iPhone

El sistema Liquid Glass ya existe: `frontend/src/design/glass.css`, componentes `GlassPanel`, `GlassNav`, `GlassModal`.

### Reglas duras

- ❌ NUNCA glass en tablas o contenedores con scroll
- ✅ SIEMPRE `.veil` detrás de texto sobre glass (contraste 4.5:1)
- ⚠️ `backdrop-filter: blur()` solo funciona en Chromium. En Firefox/Safari el glass degrada a superficie semitransparente sin blur.

### Dónde aplicar

| Elemento | Cómo | Prioridad |
|----------|------|-----------|
| Sidebar (`EquiposSidebar` + `Sidebar`) | Fondo glass en `<aside>`, `.veil` en el nav | Alta |
| Header | Fondo glass con `.veil` | Alta |
| KPIs (`InicioPage`) | `KpiTile` con `glass={true}` en los 4 | Media |
| Cards (`AprobacionesPage`) | `GlassPanel` en cards de autorizaciones | Media |
| Filtros (`go-card`) | Glass en cards de filtro | Baja |

> No abusar — cada `backdrop-filter` consume GPU. Medir performance en mobile antes de deployar.

---

## Resumen

| # | Tarea | Tipo | Esfuerzo |
|---|-------|------|----------|
| B1 | Sidebar vacío al iniciar sesión | Bug | ~3 líneas |
| B2 | Íconos SVG en botones | Mejora UX | Medio (6-8 archivos) |
| B3 | Dashboard de Equipos | Feature | Alto (charts + posible backend) |
| B4 | Responsividad móvil | QA + fixes | Medio-Bajo |
| B5 | Liquid Glass | Mejora visual | Medio |
