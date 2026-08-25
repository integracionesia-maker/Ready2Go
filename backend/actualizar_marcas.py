"""Actualiza las marcas del sistema a la lista real (2026-08-20).

El sistema venia sembrado con marcas de demostracion (Nike, Coca-Cola, ...).
Las unicas marcas reales del contexto son estas nueve. Este script:

1. Renombra "Todo Pal Campo" a "todo pal campo" (la unica real que ya
   existia, con otra capitalizacion) — no se crea duplicada.
2. Crea las marcas que falten (nombre exacto, prioridad 'media').
3. Desactiva (is_active=False) toda marca que no este en la lista real.

No borra nada: los tickets y gastos generales historicos siguen apuntando
a sus marcas originales (integridad del historial). Los selectores del
sistema piden active_only=true, asi que las viejas dejan de aparecer en el
flujo; siguen visibles en Administracion como inactivas por si se quieren
reactivar o editar.

Idempotente: se puede re-ejecutar sin efectos secundarios.

Uso (desde backend/):
    python actualizar_marcas.py
"""

from app import models
from app.database import SessionLocal

MARCAS_REALES = [
    "marketing",
    "del barrio pal barrio",
    "todo pal campo",
    "todo pal negocio",
    "ichigo",
    "plaza madero",
    "hotel punta galeria",
    "grupo ortiz",
    "canchas el fantasma",
]

# nombre real -> nombre con el que ya existia en la DB
RENOMBRES = {"todo pal campo": "Todo Pal Campo"}


def main() -> None:
    db = SessionLocal()
    reales_lower = {m.lower() for m in MARCAS_REALES}

    # 1. Renombrar la real que ya existia con otra capitalizacion.
    for nombre_real, nombre_actual in RENOMBRES.items():
        marca = db.query(models.Brand).filter(models.Brand.name == nombre_actual).first()
        if marca and marca.name != nombre_real:
            marca.name = nombre_real
            db.commit()
            print(f"renombrada: '{nombre_actual}' -> '{nombre_real}'")

    # 2. Crear las que falten.
    for nombre in MARCAS_REALES:
        existe = db.query(models.Brand).filter(models.Brand.name == nombre).first()
        if not existe:
            db.add(models.Brand(name=nombre, priority=models.BrandPriority.MEDIA.value, is_active=True))
            db.commit()
            print(f"creada: '{nombre}' (prioridad media)")

    # 3. Desactivar las que no son reales.
    for marca in db.query(models.Brand).all():
        if marca.name.lower() not in reales_lower and marca.is_active:
            marca.is_active = False
            db.commit()
            print(f"desactivada: '{marca.name}'")

    # Resumen final.
    activas = (
        db.query(models.Brand)
        .filter(models.Brand.is_active.is_(True))
        .order_by(models.Brand.name)
        .all()
    )
    print(f"\nMarcas activas ({len(activas)}):")
    for m in activas:
        print(f"  - {m.name} [{m.priority}]")
    db.close()


if __name__ == "__main__":
    main()
