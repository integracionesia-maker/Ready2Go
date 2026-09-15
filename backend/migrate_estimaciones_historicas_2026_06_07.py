"""Reconciliación histórica de junio y julio 2026 para "Meta de Gasto
Mensual" (Dashboard de Presupuestos) — meses que ya habían cerrado ANTES de
que existiera esta función, así que no hay tickets/gastos individuales
retroactivos que subir por ellos.

Sara (marketing) reportó por WhatsApp el 10/09/2026 los totales reales de esos
dos meses, ya separados en las DOS categorías independientes de esta función:

    "caja_grande" (gastos generales + por rubro):
        Junio 2026: $16,415.72
        Julio 2026: $13,294.79
    "caja_chica" (gasto de creadores):
        Junio 2026: $2,703.75
        Julio 2026: $2,912.79

Se fija cada valor como `amount` (meta) Y `actual_override` (gasto real) al
MISMO valor por categoría — ver crud.set_historical_actual: esos dos meses
quedan en 100% de cumplimiento en cada categoría porque antes de esta función
no existía una meta real distinta con la que comparar. A propósito no se
crean/editan tickets ni general_expenses/operational_expenses por este monto
(no hay comprobantes retroactivos que subir; ver
docs/presupuestos/meta-gasto-mensual.md).

Ejecutar UNA sola vez, desde `backend/`:
    python migrate_estimaciones_historicas_2026_06_07.py

Es idempotente (upsert) — correrlo dos veces deja el mismo resultado.

*** PENDIENTE EN PRODUCCIÓN ***: este script todavía NO se ha corrido contra
la base de datos de producción (gocreate.mx). La primera vez que se despliegue
este cambio ahí, correrlo una sola vez con el mismo comando (por SSH, con el
venv de esa release activado) — ver docs/presupuestos/meta-gasto-mensual.md
§Producción.
"""

from app.database import SessionLocal, engine, Base
from app import crud

Base.metadata.create_all(bind=engine)

DATOS = [
    # (year, month, categoria, monto)
    (2026, 6, "caja_grande", 16415.72),
    (2026, 6, "caja_chica", 2703.75),
    (2026, 7, "caja_grande", 13294.79),
    (2026, 7, "caja_chica", 2912.79),
]


def migrate():
    db = SessionLocal()
    try:
        for year, month, categoria, amount in DATOS:
            fila = crud.set_historical_actual(db, year=year, month=month, categoria=categoria, amount=amount)
            print(f"{year}-{month:02d} [{categoria}]: meta y gasto real fijados en ${fila.amount:,.2f}")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
