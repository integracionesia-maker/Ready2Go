"""Seed the database with sample creators and brands for quick evaluation."""

from app.database import SessionLocal, engine, Base
from app import models

Base.metadata.create_all(bind=engine)

db = SessionLocal()

brand_names = [
    "MARKETING", "CANCHAS EL FANTASMA", "DEL BARRIO PAL BARRIO",
    "GRUPO ORTIZ", "HOTEL PUNTA GALERIA", "ICHIGO",
    "PLAZA MADERO", "TODO PAL CAMPO", "TODO PAL NEGOCIO",
]

brands = []
for name in brand_names:
    existing = db.query(models.Brand).filter(models.Brand.name == name).first()
    if existing:
        brands.append(existing)
    else:
        b = models.Brand(name=name, priority="alta" if name == "MARKETING" else "media")
        db.add(b)
        db.flush()
        brands.append(b)

creator_data = [
    {"name": "Mariana López", "initial_budget": 150_000.00},
    {"name": "Carlos Mendoza", "initial_budget": 85_000.00},
    {"name": "Valentina Ruiz", "initial_budget": 200_000.00},
    {"name": "Diego Fernández", "initial_budget": 60_000.00},
    {"name": "Sofía Herrera", "initial_budget": 120_000.00},
    {"name": "Alejandro Torres", "initial_budget": 95_000.00},
]

for entry in creator_data:
    existing = db.query(models.Creator).filter(models.Creator.name == entry["name"]).first()
    if existing:
        continue
    c = models.Creator(
        name=entry["name"],
        initial_budget=entry["initial_budget"],
        remaining_budget=entry["initial_budget"],
    )
    db.add(c)

db.commit()
db.close()

print("Base de datos poblada exitosamente.")
print(f"  - {len(brand_names)} marcas")
print(f"  - {len(creator_data)} creadores")
