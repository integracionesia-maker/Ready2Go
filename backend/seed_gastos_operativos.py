"""Seed idempotente de los rubros iniciales de Gastos Operativos.

Uso (SIEMPRE desde backend/, igual que el resto de seeds y uvicorn):
    python seed_gastos_operativos.py

Crea las tablas si no existen y siembra los 5 rubros iniciales. Reejecutar no
duplica: si un rubro ya existe por nombre, lo deja como esta.
"""

from app.database import SessionLocal, engine, Base
from app import models  # noqa: F401  — registra todas las tablas en Base.metadata

RUBROS_INICIALES = [
    "E-commerce",
    "IA",
    "Aplicaciones",
    "Campañas",
    "Activaciones",
]


def sembrar(db) -> None:
    creados = 0
    for nombre in RUBROS_INICIALES:
        existente = (
            db.query(models.ExpenseRubro)
            .filter(models.ExpenseRubro.nombre == nombre)
            .first()
        )
        if existente:
            print(f"  = ya existe: {nombre}")
            continue
        db.add(models.ExpenseRubro(nombre=nombre, is_active=True))
        db.commit()
        creados += 1
        print(f"  + creado: {nombre}")
    print(f"Rubros nuevos: {creados}")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        sembrar(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
