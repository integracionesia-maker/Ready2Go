"""Crear usuarios para el equipo completo de Ready2Go.
Ejecutar desde backend/: python crear_usuarios_equipo.py
"""

import os, sys
from app.database import SessionLocal
from app.models import User, Creator
from app import crud
from app.security import hash_password
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

db = SessionLocal()

SUPERADMINS = [
    {"username": "integraciones.ia", "full_name": "Integraciones IA", "email": "integraciones.ia@grupo-ortiz.com"},
    {"username": "josue.benitez", "full_name": "Josue Benitez", "email": "josue.benitez@grupo-ortiz.com"},
    {"username": "jose.aguilar", "full_name": "Jose Aguilar", "email": "jose.aguilar@grupo-ortiz.com"},
]

MARKETING = [
    {"username": "melisa", "full_name": "Melisa Avendano", "email": "melisa.avendano@grupo-ortiz.com"},
    {"username": "sara", "full_name": "Sara", "email": "sara@grupo-ortiz.com"},
]

CREATORS_EXTRA = [
    {"name": "Mariana Lopez", "initial_budget": 150_000.00},
    {"name": "Carlos Mendoza", "initial_budget": 85_000.00},
    {"name": "Valentina Ruiz", "initial_budget": 200_000.00},
    {"name": "Diego Fernandez", "initial_budget": 60_000.00},
]

print("=== ANTES ===")
for u in db.query(User).order_by(User.id).all():
    print(f"  {u.username} | {u.full_name} | {u.role} | active={u.is_active}")

# ── Superadmins ──────────────────────────────────────────────────────
print("\n--- Superadmins ---")
for sa in SUPERADMINS:
    u = db.query(User).filter(User.username == sa["username"]).first()
    if u:
        print(f"  YA EXISTE: {sa['username']}")
        continue
    pwd = os.environ["SUPERADMIN_PASSWORD"]
    crud.create_user(db, username=sa["username"], email=sa["email"],
                     password_hash=hash_password(pwd),
                     full_name=sa["full_name"], role="superadmin",
                     creator_id=None, must_change_password=False)
    print(f"  + CREADO: {sa['username']} ({sa['full_name']})")

# ── Marketing ─────────────────────────────────────────────────────────
print("\n--- Marketing ---")
for mk in MARKETING:
    u = db.query(User).filter(User.username == mk["username"]).first()
    if u:
        # Actualizar si ya existe
        if u.role != "colaborador_mkt":
            u.role = "colaborador_mkt"
            print(f"  ~ ACTUALIZADO rol: {mk['username']} -> colaborador_mkt")
        else:
            print(f"  = OK: {mk['username']}")
        continue
    pwd = os.environ["SUPERADMIN_PASSWORD"]
    crud.create_user(db, username=mk["username"], email=mk["email"],
                     password_hash=hash_password(pwd),
                     full_name=mk["full_name"], role="colaborador_mkt",
                     creator_id=None, must_change_password=False)
    print(f"  + CREADO: {mk['username']} ({mk['full_name']})")

# ── Creators + usuarios ───────────────────────────────────────────────
print("\n--- Creators ---")

# NO borrar creators existentes — pueden tener tickets asociados.
# Solo agregar los que falten de la lista.
for data in CREATORS_EXTRA:
    name = data["name"]
    c = db.query(Creator).filter(Creator.name == name).first()
    if not c:
        c = Creator(name=name, initial_budget=data["initial_budget"],
                     remaining_budget=data["initial_budget"])
        db.add(c)
        db.flush()
        print(f"  + CREADO creator: {name} (presupuesto: ${data['initial_budget']:,.0f})")
    else:
        print(f"  = YA EXISTE creator: {name}")

    # Crear usuario creador vinculado si no tiene
    username = name.lower().replace(" ", "")[:20]
    linked = db.query(User).filter(User.creator_id == c.id).first()
    if linked:
        print(f"  = YA TIENE usuario vinculado: {linked.username}")
        continue
    u = db.query(User).filter(User.username == username).first()
    pwd = os.environ["SUPERADMIN_PASSWORD"]
    if not u:
        crud.create_user(db, username=username, email=f"{username}@grupo-ortiz.com",
                         password_hash=hash_password(pwd),
                         full_name=name, role="creador",
                         creator_id=c.id, must_change_password=False)
        print(f"  + CREADO usuario: {username} (creador) -> {name}")
    else:
        u.creator_id = c.id
        u.role = "creador"
        print(f"  ~ VINCULADO existente: {u.username} -> creator {name}")

# Verificar: si hay un Gerardo que no esta en la lista target, desvincularlo
# y marcarlo inactivo sin borrar (tiene tickets)
extras = [c for c in db.query(Creator).all() if c.name not in {d["name"] for d in CREATORS_EXTRA}]
for c in extras:
    linked = db.query(User).filter(User.creator_id == c.id).first()
    if linked:
        linked.creator_id = None
        print(f"  ~ Desvinculado {linked.username} de creator {c.name}")
    c.is_active = False
    print(f"  ~ INACTIVADO creator (tiene tickets, no se borra): {c.name}")

db.commit()

# ── Eliminar superadmin viejo ─────────────────────────────────────────
print("\n--- Limpieza superadmin viejo ---")
old_sa = db.query(User).filter(User.username == "superadmin").first()
if old_sa:
    db.delete(old_sa)
    db.commit()
    print("  - ELIMINADO: superadmin (viejo)")

# ── Resultado final ───────────────────────────────────────────────────
print("\n=== DESPUES ===")
for u in db.query(User).order_by(User.id).all():
    creator_name = u.creator.name if u.creator else "-"
    print(f"  {u.username} | {u.full_name} | {u.role} | active={u.is_active} | creator={creator_name}")

print(f"\nTotal usuarios: {db.query(User).count()}")
print(f"Total creators: {db.query(Creator).count()}")
db.close()
print("Listo.")
