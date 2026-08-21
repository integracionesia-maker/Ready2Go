# Manual de usuario — Gastos Operativos

> Módulo de la plataforma GOCreate, hermano de Presupuestos y Equipos.
> Contabilidad de gastos **separada de marketing**.

## Qué es

Un registro de gastos que **solo acumula** (no hay presupuesto, ni límite, ni
aprobación). Cada gasto se clasifica en un **rubro** (E-commerce, IA,
Aplicaciones, Campañas, Activaciones… y los que se agreguen). Sirve para ver,
mes a mes, en qué se gasta más. Es independiente de marketing: sus totales no
aparecen en los dashboards ni exportaciones de Presupuestos.

## Quién puede entrar

| Rol | Acceso |
|---|---|
| `superadmin`, `admin` | Todo el módulo, incluida la gestión de rubros |
| `operativo` (rol nuevo) | Todo el módulo (registrar, ver, borrar, exportar, gestionar rubros). **No** ve Presupuestos ni Equipos |
| Roles de marketing, `creador` | Sin acceso — no ven el módulo ni su switch |

El switch de módulos (arriba en escritorio, abajo en móvil) solo muestra
"Gastos Operativos" a quien tiene permiso; si es tu único módulo, no verás
switch — entras directo.

## Pantallas

### Inicio
Portada del módulo: accesos rápidos a Registro, Dashboard y Rubros, y el total
gastado en el mes en curso. Es a donde lleva el logo de Grupo Ortiz cuando estás
dentro del módulo.

### Registro
Lista de gastos del periodo seleccionado, con su **total**. Filtra por rango de
fechas y por rubro. Botón **Nuevo Gasto** abre el formulario:

- **Rubro** (obligatorio) — de la lista de rubros activos.
- **Fecha del gasto** (obligatoria) — la fecha en que se hizo el gasto. **Define
  el mes al que cuenta**, no la fecha en que lo subes. Si el gasto fue el 30 de
  agosto y lo subes el 4 de septiembre, cuenta en agosto.
- **Monto** (obligatorio, mayor a $0).
- **Descripción** (obligatoria).
- **Comprobante** (obligatorio) — PNG, JPG o PDF, hasta 10 MB. Desde el celular
  aparece además el botón **Tomar foto** para capturarlo con la cámara.

En cada fila: **Ver comprobante** (visor con zoom) y **Eliminar** (borrado
lógico — el gasto deja de contar pero se conserva para auditoría; **no** hay
borrado permanente en este módulo).

### Dashboard
Total gastado, número de gastos y rubros con gasto, más:
- **Distribución por rubro** (dona).
- **Gasto por mes** (barras), calculado por la fecha del gasto.
- **Detalle por rubro** (tabla).

Todo respeta el rango de fechas elegido.

### Rubros
Catálogo de clasificaciones. Crear, renombrar y **activar/desactivar**.
Desactivar un rubro lo oculta de los formularios de alta pero conserva los
gastos históricos que ya lo usaban. Un nombre de rubro no se puede repetir.

## Exportación

Desde el módulo se exporta su propio reporte, **mensual por defecto** y con
rango configurable. Es independiente del exportar de Presupuestos.

## Reglas que conviene tener claras

- El **mes lo define la fecha del gasto**, no la de subida.
- El **comprobante es obligatorio** en toda alta.
- El borrado es **solo lógico**: recuperable/auditable, nunca se borra el archivo.
- Este módulo **no** comparte datos con marketing: ni marcas, ni creadores, ni
  ciclos, ni sus dashboards.

Detalle técnico y de implementación: `docs/gastos-operativos/plan-implementacion.md`.
