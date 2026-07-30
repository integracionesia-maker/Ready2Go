# Gastos Generales — Manual de Administrador (R12)

> Feature del paquete R12 (`docs/historico/plan-gastos-generales-y-borrado-tickets.md`). Complementa `docs/presupuestos/presupuestos-y-validacion.md` (que cubre presupuestos de creadores) — los Gastos Generales usan tabla propia (`general_expenses`) independiente de `tickets`, pero están vinculados a la tabla de `brands` (marcas) para trazabilidad.

## ¿Qué son?

Gastos operativos que **no** están ligados a un creador pero **sí a una marca** (suscripciones de software, servicios, herramientas internas, pagos varios, etc.). Viven en su propia tabla (`general_expenses`) en vez de reutilizar `tickets`:

- No tienen ciclo de presupuesto (semanal/mensual) — no hay un monto "asignado" contra el cual medirse.
- No pasan por validación — se crean y cuentan de inmediato, sin estado `pendiente`/`aprobado`/`rechazado`.
- No afectan ni son afectados por los presupuestos de creadores en ningún cálculo.
- **Están vinculados a una marca** — cada gasto general debe asociarse a una marca existente y activa al momento de crearlo.

Solo `admin` y `superadmin` pueden crear, ver, exportar o eliminar gastos generales — un `creador` no tiene acceso a esta sección (ni en la barra lateral, ni por URL directa, ni por API: `403` en todo `/api/general-expenses/*`).

## Acceder a la sección

Barra lateral → **Gastos Generales** (entre "Validación" y "Administración"). También hay una tarjeta de acceso directo en **Inicio** para admin/superadmin.

## Crear un gasto general

1. En la página de Gastos Generales, botón **"Nuevo Gasto General"**.
2. Completa:
   - **Marca**: selecciona del tablero de marcas activas (obligatorio). Solo aparecen marcas con estado "Activo". Si necesitas una marca nueva, créala primero en Administración → Marcas.
   - **Descripción**: texto libre (obligatorio, hasta 500 caracteres).
   - **Monto**: mayor a $0.
   - **Comprobante**: JPG, PNG o PDF, máximo 10 MB (misma validación que los comprobantes de tickets).
3. Al guardar, el gasto queda registrado de inmediato — no requiere aprobación de nadie más.

## Consultar el historial

La tabla principal lista los gastos generales (más recientes primero), con un filtro de rango de fechas. Cada fila muestra fecha, marca, descripción, monto y un botón **"Ver"** para abrir el comprobante en una pestaña nueva.

## Exportar a PDF

1. Botón **"Exportar"**.
2. Selecciona uno o más de los últimos 12 meses (checkboxes).
3. **"Generar PDF"** produce un reporte con: título, período seleccionado, tabla (Fecha | Marca | Descripción | Monto | Comprobante), total general, y pie de página con fecha de generación y quién lo generó.

Esta exportación es independiente del reporte PDF del Dashboard (`docs/presupuestos/presupuestos-y-validacion.md` §6) — es un documento propio, más simple, enfocado solo en gastos generales.

## Eliminar un gasto general

Botón **"Eliminar"** en cada fila, con dos niveles (mismo mecanismo que el borrado de tickets, ver `docs/presupuestos/borrado-tickets.md`):

- **Eliminar** (borrado lógico): el gasto deja de contar en listados, gráficas y exportaciones, pero el registro y el archivo se conservan (auditable).
- **Eliminar permanentemente**: ⚠️ irreversible — borra el registro de la base de datos y el archivo del disco. Requiere un paso adicional de confirmación con advertencia en rojo.

## Gráfica en el Dashboard

El Dashboard (`/dashboard`, admin/superadmin) incluye una sección "Gastos Generales por Mes" (gráfica de barras) y un KPI con el total del período — respetan el mismo filtro de fechas del resto del Dashboard y excluyen gastos eliminados. El PDF del Dashboard también incluye esta sección.
