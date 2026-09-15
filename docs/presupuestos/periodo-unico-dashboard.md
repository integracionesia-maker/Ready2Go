# Modo "Periodo Único" del Dashboard (pantalla + PDF)

> Complementa `docs/presupuestos/meta-gasto-mensual.md` (esa es la tarjeta de meta/gasto mensual, con su propia navegación de mes — esto es el resto del Dashboard: KPIs y gráficas según el filtro de fechas de arriba).

## Qué es

Cuando el filtro de fechas del Dashboard resuelve a **exactamente un mes o un año de calendario** ("Este mes", "Mes pasado", "Este año"), las gráficas "por mes" (que con un solo periodo degeneran a una sola barra) se ocultan a favor de los desgloses por categoría que ya existen (por marca/rubro/creador), y los 3 KPIs de gasto del periodo muestran una comparación contra el periodo anterior equivalente (mes pasado / año pasado). "Últimos 3M" y "Todo" se quedan exactamente igual que siempre — nunca activan este modo.

Aplica **tanto en pantalla como en el PDF exportado** — misma lógica, un solo lugar de verdad (nunca se decide dos veces).

## Detección (única fuente de verdad: backend)

`crud.detectar_periodo_unico(start_date, end_date)` — `None` si el rango no es un mes/año de calendario completo (multi-mes, "Todo" con `None`/`None`, etc). Si sí lo es, regresa `(tipo, compare_start, compare_end)`:

- **"mes"**: `start_date` es el día 1 de un mes y `end_date` cae dentro de ese mismo mes. Cubre "Este mes" (a medio mes) y "Mes pasado" (ya cerrado).
- **"año"**: `start_date` es 1-enero y `end_date` cae dentro de ese mismo año.
- El periodo de comparación usa el **mismo día de corte** si el periodo sigue "en curso" (hasta hoy) — para comparar manzanas con manzanas, no un mes a medias contra uno completo — o el mes/año anterior **completo** si el periodo pedido ya cerró. Clamp automático en meses más cortos (ej. día 31 → 28/29 de febrero).
- Caso borde documentado en el código: en enero, "Este mes" y "Este año a la fecha" producen el mismo rango de fechas (1-ene a hoy) — indistinguibles sin rastrear qué botón se pulsó (a propósito no se hace, así un Desde/Hasta manual también activa el modo). Se resuelve a favor de "mes"; solo afecta la etiqueta y el periodo de comparación, nunca si se activa el modo.

## Qué cambia en modo periodo único

| Gráfica | Comportamiento normal | Modo periodo único |
|---|---|---|
| Transacciones por Mes | Barra por mes | Oculta |
| Tendencia de Gasto Acumulado | Área acumulada por mes | Oculta (solo pantalla, nunca estuvo en el PDF) |
| Gastos Generales por Mes | Barra por mes | Reemplazada por **Gastos Generales por Marca** (nueva, mismo componente que "Gastos por Marca" de tickets) |
| Gastos Operativos por Mes | Barra por mes | Oculta ("Gastos Operativos por Rubro" ya cubre ese desglose) |
| Gastos por Marca, Uso por Creador, Gastos Operativos por Rubro, Mayores Gastos, Tickets por Día | Sin cambios | Sin cambios — son las que reemplazan a las de arriba |

`GET /api/dashboard/general-expenses-by-brand?start_date=&end_date=` (nuevo): calco de `get_brand_spend_breakdown` pero sobre `GeneralExpense` en vez de `Ticket` — reutiliza el schema `BrandSpendItem`, así que el frontend reutiliza el componente `BrandSpendApexChart` tal cual (nada nuevo que mantener).

## Comparación vs periodo anterior

Solo a nivel de los **totales generales** (no por gráfica individual): "Gastado en el Período", "Gastos Generales", "Gastos Operativos". `GET /api/dashboard/period-comparison?start_date=&end_date=` regresa `actual`/`anterior` (cada uno con `total_spent`, `general_expenses_total`, `operational_expenses_total`, `ticket_count`) reutilizando `get_dashboard_summary`/`get_general_expenses_monthly`/`crud_operativos.dashboard` con el rango pedido y con el rango de comparación — cero agregación nueva.

Texto: `+12.3% vs el mes pasado` / `−8.0% vs el año pasado` (rojo si subió el gasto, verde si bajó — es gasto, no ingreso). Sin gasto en el periodo anterior: `antes $0.00 vs...` en vez de dividir por cero.

## Permisos

Mismo candado que el resto de `/api/dashboard`: `admin`/`superadmin`/`marketing_presupuestos`/`marketing_admin`.
