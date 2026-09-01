# Gastos Generales — Manual de Administrador (R12)

> Feature del paquete R12 (`docs/historico/plan-gastos-generales-y-borrado-tickets.md`). Complementa `docs/presupuestos/presupuestos-y-validacion.md` (que cubre presupuestos de creadores) — los Gastos Generales usan tabla propia (`general_expenses`) independiente de `tickets`, pero están vinculados a la tabla de `brands` (marcas) para trazabilidad.
>
> **Fusión con Gastos Operativos (WP fusión, sept-2026)**: lo que antes era un módulo aparte con switch propio (`docs/historico/gastos-operativos-plan-implementacion.md`, `docs/historico/gastos-operativos-manual-usuario.md`) ahora vive **dentro de esta misma sección**: un formulario con selector de tipo y un listado combinado. Siguen siendo **tablas y endpoints separados** — la fusión es de interfaz, no de esquema.

## ¿Qué son?

Esta sección maneja **dos tipos de gasto**, con un formulario y un listado compartidos pero tablas propias cada uno:

| | Gasto **General** | Gasto **Operativo** |
|---|---|---|
| Tabla | `general_expenses` | `operational_expenses` |
| Se clasifica por | **Marca** (`brand_id`, obligatorio) | **Rubro** (`rubro_id` — catálogo editable: E-commerce, IA, Aplicaciones, Campañas, Activaciones…) |
| Fecha que cuenta | `upload_date` (automática, al subir) | `fecha_gasto` (**manual**, la eliges tú — define el mes para dashboard y export) |
| Borrado | Lógico **y físico** | **Solo lógico** (no hay borrado físico) |
| Distintivo en el listado | Badge naranja "General" | Badge turquesa "Operativo" |

Ninguno de los dos tiene ciclo de presupuesto ni pasa por validación — se crean y cuentan de inmediato, sin estado `pendiente`/`aprobado`/`rechazado`, y no afectan ni son afectados por los presupuestos de creadores en ningún cálculo.

Acceso: `admin`, `superadmin`, `marketing_presupuestos` y `marketing_admin` pueden crear, ver, exportar o eliminar cualquiera de los dos tipos — un `creador` no tiene acceso (ni en la barra lateral, ni por URL directa, ni por API: `403` en `/api/general-expenses/*`, `/api/operational-expenses/*` y `/api/rubros/*`). El rol base `operativo` (que antes veía *solo* el módulo aislado de Gastos Operativos) se retiró del catálogo — quien lo tenía hoy es `marketing_admin`.

## Acceder a la sección

Barra lateral → **Gastos Generales** (entre "Validación" y "Administración"). También hay una tarjeta de acceso directo en **Inicio**.

## Crear un gasto

1. En la página de Gastos Generales, botón **"Nuevo Gasto"**.
2. Elige el **tipo** con el selector al inicio del formulario: **General** u **Operativo**.
3. Completa según el tipo elegido:
   - **General**: **Marca** (selecciona del tablero de marcas activas, obligatorio).
   - **Operativo**: **Rubro** (selecciona del catálogo, obligatorio) + **Fecha del gasto** (define el mes al que cuenta, no tiene que ser hoy).
   - Comunes a ambos: **Descripción** (texto libre, obligatorio, hasta 500 caracteres), **Monto** (mayor a $0), **Comprobante** (JPG, PNG o PDF, máximo 10 MB).
4. Al guardar, el gasto queda registrado de inmediato — no requiere aprobación de nadie más.

### Gestionar rubros (solo para gastos operativos)

Botón **"Gestionar rubros"** (junto a "Exportar") abre el catálogo de rubros: crear uno nuevo, renombrar uno existente, o desactivarlo (un rubro desactivado no aparece como opción al crear un gasto nuevo, pero los gastos históricos que ya lo usan lo conservan).

## Consultar el historial

La tabla principal combina **ambos tipos** en un solo listado (más recientes primero, según la fecha que corresponda a cada tipo), con un filtro de rango de fechas. Cada fila muestra el **badge de tipo**, fecha, marca o rubro, descripción, monto y un botón **"Ver"** para abrir el comprobante.

## Exportar a PDF

1. Botón **"Exportar"**.
2. Selecciona uno o más de los últimos 12 meses (checkboxes).
3. **"Generar PDF"** produce un reporte con: título, período seleccionado, tabla, total general, y pie de página con fecha de generación y quién lo generó.

Los dos tipos se exportan por separado (dos flujos de exportación independientes, cada uno con sus propios meses) — no hay, por ahora, un PDF combinado de ambos tipos a la vez. Esta exportación es independiente del reporte PDF del Dashboard (`docs/presupuestos/presupuestos-y-validacion.md` §6).

## Eliminar un gasto

Botón **"Eliminar"** en cada fila:

- **Gastos generales**: dos niveles (mismo mecanismo que el borrado de tickets, ver `docs/presupuestos/borrado-tickets.md`) — **Eliminar** (lógico, recuperable/auditable) y **Eliminar permanentemente** (⚠️ irreversible, con confirmación adicional en rojo).
- **Gastos operativos**: **solo borrado lógico** — el gasto deja de contar en listados, gráficas y exportaciones, pero el registro y el archivo se conservan. No existe la opción de borrado físico para este tipo (el botón de "eliminar permanentemente" no aparece).

## Gráficas en el Dashboard

El Dashboard (`/dashboard`) incluye, respetando el mismo filtro de fechas del resto del Dashboard y excluyendo gastos eliminados:

- **Gastos Generales por Mes** (barras) + KPI con el total del período.
- **Gastos Operativos por Mes** y **Gastos Operativos por Rubro** (barras) + KPI con el total del período.
- **Tickets Subidos por Día** (barras, un tipo de gráfica aparte): cuenta cuántos tickets se subieron cada día del período seleccionado — a diferencia de las demás gráficas de gasto, esta cuenta **todos** los tickets (cualquier estado), es una métrica de actividad, no de gasto aprobado.

El PDF del Dashboard incluye las tres secciones.
