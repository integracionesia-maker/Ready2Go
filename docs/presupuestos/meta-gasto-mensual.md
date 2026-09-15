# Meta de Gasto Mensual (Dashboard de Presupuestos)

> Complementa `docs/presupuestos/presupuestos-y-validacion.md` (ciclos de presupuesto por creador — esto es distinto: una meta global por mes, no por creador).

## Qué es

Dos metas fijas **independientes** por mes de calendario (I10, 10/09/2026 — antes era un solo total combinado, se separó a petición explícita):

- **Caja Grande**: gastos generales (`general_expenses`) + gastos por rubro (`operational_expenses`).
- **Caja Chica**: gasto de creadores (tickets aprobados, `tickets`).

Cada una se compara contra lo realmente gastado ese mes **en su propio universo de tablas** — nunca se combinan en un solo número. Se muestran como dos bloques dentro de la misma tarjeta al inicio del Dashboard, cada uno con su propia barra de progreso, y navegación de mes propia (independiente del filtro de fechas del resto del Dashboard).

## Reglas

- **Alcance global**, no por marca: un número por mes y categoría cubre todo el departamento.
- Solo se puede **fijar/editar mientras el mes sea futuro** — en cuanto arranca (aunque sea el día 1) queda congelada. `PUT /api/dashboard/monthly-estimates/{year}/{month}/{categoria}` responde `409` si el mes ya inició, `400` si `categoria` no es `caja_grande`/`caja_chica`.
- Permisos: `admin`/`superadmin`/`marketing_presupuestos`/`marketing_admin` (misma puerta que Gastos Generales+Operativos). Ver también `GET /api/dashboard/monthly-estimates?year=` (devuelve 24 items: 12 meses × 2 categorías).
- El "gastado" de cada categoría se calcula igual que el resto del Dashboard: Caja Grande por `upload_date` (generales) y `fecha_gasto` (operativos); Caja Chica por `upload_date` de tickets aprobados — ningún bucketing nuevo.

## Sugerencia automática para meses futuros sin meta

Si un mes futuro no tiene una meta propia guardada todavía (por categoría), el GET propone un valor automático: el promedio del gasto real de los 3 meses de calendario anteriores **de esa misma categoría** (`crud._estimacion_sugerida`) — caja_grande y caja_chica nunca se promedian juntas.

Esta propuesta **ya es una estimación real y funcional**: impulsa el % de cumplimiento y el color de la barra igual que una meta guardada explícitamente (`is_suggested: true` en la respuesta es solo informativo, para que la UI muestre el badge "sugerida" y el botón diga "Confirmar o cambiar"). Un admin de marketing (`superadmin`/`admin`/`marketing_admin`/`marketing_presupuestos`) puede en cualquier momento —mientras el mes siga siendo futuro— fijar un valor definitivo con `PUT`, que la reemplaza y pasa a ser LA meta real hasta que alguien la vuelva a cambiar. Sin ningún gasto real en esos 3 meses (proyecto recién arrancando) no sugiere nada (`amount: null`) en vez de proponer $0.

## Reconciliación histórica (`actual_override`)

La tabla `monthly_spend_estimates` tiene una columna `actual_override`, pensada para meses que **ya habían cerrado antes de que existiera esta función** y que por lo tanto no tienen tickets/gastos individuales que los respalden retroactivamente.

Cuando `actual_override` está presente en una fila (mes + categoría), **sustituye por completo** el cálculo en vivo de "gastado" de esa categoría (nunca se suma a él). Solo la escribe `crud.set_historical_actual` — usada exclusivamente por scripts de migración de una sola vez, **jamás** por el router/API normal (que solo toca `amount` vía `upsert_monthly_estimate`, y solo si el mes sigue siendo futuro).

### Junio y julio 2026

Sara (marketing) reportó por WhatsApp el 10/09/2026 los totales reales de esos dos meses, ya separados en las dos categorías:

| Mes | Caja Grande (generales+rubro) | Caja Chica (creadores) |
|---|---|---|
| Junio 2026 | $16,415.72 | $2,703.75 |
| Julio 2026 | $13,294.79 | $2,912.79 |

No hay comprobantes retroactivos que subir por esos meses, así que **no se crean tickets ni gastos generales/operativos** — se fija cada valor como `amount` (meta) **y** `actual_override` (gasto real) al mismo valor por categoría: ambos meses quedan en 100% de cumplimiento en cada categoría porque antes de esta función no existía una meta real distinta con la que comparar.

Script: `backend/migrate_estimaciones_historicas_2026_06_07.py`. Idempotente (upsert) — correrlo dos veces deja el mismo resultado.

```
cd backend
python migrate_estimaciones_historicas_2026_06_07.py
```

## ⚠️ Pendiente en producción

Este script **todavía no se ha corrido contra la base de datos de producción** (gocreate.mx). La primera vez que se despliegue este cambio ahí:

1. Desplegar el código como siempre (`deploy-app.sh gocreate`) — la tabla `monthly_spend_estimates` (con `categoria` y `actual_override`) se crea sola en el arranque (`Base.metadata.create_all`), no requiere migración de esquema aparte.
2. Por SSH, con el venv de la release activa, desde el `backend/` de esa release:
   ```
   python migrate_estimaciones_historicas_2026_06_07.py
   ```
3. Confirmar en el Dashboard (Julio/Junio 2026) que Caja Grande y Caja Chica muestran los totales de la tabla de arriba al 100% cada una.

Es seguro correrlo más de una vez (idempotente) y seguro correrlo aunque otros meses ya tengan datos reales — solo toca junio y julio 2026.
