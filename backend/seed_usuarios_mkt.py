"""Seeder de usuarios del equipo de marketing.
Idempotente: si un usuario ya existe (mismo username), lo salta.

Uso (ejecutar SIEMPRE desde backend/):
    python seed_usuarios_mkt.py

Los usuarios se crean con rol `colaborador_mkt` y la contraseña definida en
la variable de entorno DEFAULT_USER_PASSWORD. Si no está definida, se usa una
contraseña temporal aleatoria (se imprime una sola vez).

Antes de sembrar, ELIMINA todos los usuarios que NO sean superadmin para
dejar la base limpia. Los 3 superadmins no se tocan.
"""

import os
import unicodedata

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from app.database import SessionLocal, engine, Base
from app import models, security, crud_rbac

Base.metadata.create_all(bind=engine)

# ── Usuarios del equipo de marketing ────────────────────────────────────
# (nombre completo, email, username)
# Si el email es compartido, se deriva uno único a partir del nombre.
# Rol base: colaborador_mkt (ver inventario, solicitar préstamo, devolver).

USUARIOS_MKT = [
    ("Melisa Avendaño Zúñiga",          "melisa.avendano@grupo-ortiz.com"),
    ("Bárbara Montserrat Ayala Escobar", "barbara.escobar@grupo-ortiz.com"),
    ("Sara Jion mi Benito Reyes",        "Sara.benito@grupo-ortiz.com"),
    ("Edgar Martínez",                   "edgar.martinez@grupo-ortiz.com"),
    ("Gerson Fabricio Martínez Guerrero","gerson.martinez@grupo-ortiz.com"),
    ("Juan Pablo Corona Corona",         "Juan.corona@grupo-ortiz.com"),
    ("Emily Vianney Pérez Morales",      "emily.perez@grupo-ortiz.com"),
    ("Alejandra Paola Aparicio Romero",  "alejandra.aparicio@grupo-ortiz.com"),
    ("Hillary Stephanie Torres Bravo",   "hillary.torres@grupo-ortiz.com"),
    ("Jeziel Teodoro Rodríguez",         "jeziel.rodriguez@grupo-ortiz.com"),
    ("Paola Berenice Gonzalez Ambriz",   "paola.gonzalez@grupo-ortiz.com"),
    ("Betzabeth Fuentes Ramos",          "betzabet.fuentes@grupo-ortiz.com"),
    ("Naydelin Sepúlveda Mendoza",       "naydelin.sepulveda@grupo-ortiz.com"),
]

# Paquetes aditivos por username (llave = nombre completo exacto).
# Melisa es la aprobadora de equipo; el resto solo colaborador_mkt base.
ADITIVOS: dict[str, tuple[str, ...]] = {
    "Melisa Avendaño Zúñiga": ("APROBADOR_EQUIPO",),
}


def _slugify(name: str) -> str:
    """Normaliza un nombre completo a username: 'emily.perez'."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", ".")


def _unique_username(db, base: str) -> str:
    username = base
    suffix = 1
    while db.query(models.User).filter(models.User.username == username).first():
        suffix += 1
        username = f"{base}{suffix}"
    return username


def _unique_email(db, base: str) -> str:
    email = base
    suffix = 1
    while db.query(models.User).filter(models.User.email == email).first():
        suffix += 1
        local, _, domain = base.partition("@")
        email = f"{local}+{suffix}@{domain}"
    return email


def limpiar_usuarios(db) -> int:
    """Elimina todos los usuarios que NO sean superadmin. Retorna cuántos borró."""
    eliminados = (
        db.query(models.User)
        .filter(models.User.role != models.UserRole.SUPERADMIN.value)
        .delete(synchronize_session="fetch")
    )
    db.commit()
    return eliminados


def sembrar(db, default_password: str) -> list[models.User]:
    creados: list[models.User] = []
    for full_name, email in USUARIOS_MKT:
        username = _unique_username(db, _slugify(full_name))
        unique_email = _unique_email(db, email)

        existente = (
            db.query(models.User)
            .filter(
                (models.User.username == username)
                | (models.User.email == unique_email)
            )
            .first()
        )
        if existente:
            print(f"  [existe] {full_name} -> {existente.username} / {existente.email}")
            creados.append(existente)
            continue

        user = models.User(
            username=username,
            email=unique_email,
            password_hash=security.hash_password(default_password),
            full_name=full_name,
            role=models.UserRole.COLABORADOR_MKT.value,
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Paquetes aditivos
        extras = ADITIVOS.get(full_name, ())
        for nombre_paquete in extras:
            crud_rbac.conceder(db, user.id, nombre_paquete, granted_by=None)

        tag = f" +{','.join(extras)}" if extras else ""
        print(f"  [creado] {full_name} -> {user.username} / {user.email}{tag}")
        creados.append(user)

    return creados


def main() -> None:
    default_password = os.getenv("DEFAULT_USER_PASSWORD", "")
    if not default_password:
        default_password = security.generate_temp_password()
        print(f"DEFAULT_USER_PASSWORD no definida en .env — contraseña temporal: {default_password}")
        print("Guárdala y agrégala a .env como DEFAULT_USER_PASSWORD=<valor> para futuros seeds.\n")

    db = SessionLocal()
    try:
        n = limpiar_usuarios(db)
        print(f"Usuarios no-superadmin eliminados: {n}\n")

        print("Sembrando usuarios de marketing...")
        creados = sembrar(db, default_password)
        print(f"\nUsuarios creados: {len(creados)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
