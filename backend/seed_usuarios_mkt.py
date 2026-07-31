"""Seeder de usuarios del equipo de marketing + superadmins.
Idempotente: si un usuario ya existe (mismo username), lo salta.

Uso (ejecutar SIEMPRE desde backend/):
    python seed_usuarios_mkt.py

Los usuarios se crean con la contraseña definida en DEFAULT_USER_PASSWORD
del .env. Si no está definida, se genera una temporal aleatoria.

NO crea datos falsos (tickets, marcas, etc.) — solo usuarios reales.
Para datos demo de prueba usa seed_demo_completo.py.
"""

import os
import unicodedata

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from app.database import SessionLocal, engine, Base
from app import models, security

Base.metadata.create_all(bind=engine)

# ── Superadministradores ────────────────────────────────────────────────

SUPERADMINS = [
    ("integraciones.ia", "integraciones.ia@grupo-ortiz.com", "Integraciones IA"),
    ("josue.benitez",     "josue.benitez@grupo-ortiz.com",     "Josue Benitez"),
    ("jose.aguilar",      "jose.aguilar@grupo-ortiz.com",      "Jose Aguilar"),
]

# ── Usuarios del equipo de marketing ────────────────────────────────────
# (nombre completo, email)
# El username se deriva del nombre (slug). Rol base: colaborador_mkt.

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

# Rol de cada persona (organigrama de accesos, jul-2026 —
# docs/asignaciones + diagrama de Grupo Ortiz). Fuente de verdad unica: quien
# no aparezca aqui cae al default de DEFAULT_ROLE_MKT.
#
#   admin             Jefa de departamento. Acceso completo (incluye aprobar
#                      prestamos de Equipos) — ver rbac_catalog.PAQUETES["admin"].
#   marketing_admin    Tier "Administrador" del organigrama: Presupuestos +
#                      Equipos completos, SIN aprobacion (esa sigue siendo
#                      exclusiva de la jefa).
#   marketing_basico   Resto del equipo: solo subir tickets propios y
#                      solicitar prestamos de equipo (ver lo propio).
ROLES_ESPECIALES: dict[str, str] = {
    "Melisa Avendaño Zúñiga":            "admin",
    "Alejandra Paola Aparicio Romero":   "marketing_admin",
    "Emily Vianney Pérez Morales":       "marketing_admin",
    "Gerson Fabricio Martínez Guerrero": "marketing_admin",
    "Sara Jion mi Benito Reyes":         "marketing_admin",
}

# Rol por defecto para cualquiera en USUARIOS_MKT que no este en
# ROLES_ESPECIALES (hoy: los 8 del tier "tickets y solicitud de prestamos
# unicamente"). `colaborador_mkt` es legacy — ver models.UserRole — y este
# seeder ya no lo asigna a nadie nuevo.
DEFAULT_ROLE_MKT = models.UserRole.MARKETING_BASICO.value


def _slugify(name: str) -> str:
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


def sembrar_superadmins(db, default_password: str) -> list[models.User]:
    creados = []
    for username, email, full_name in SUPERADMINS:
        existente = db.query(models.User).filter(
            (models.User.username == username) | (models.User.email == email)
        ).first()
        if existente:
            # Si ya existe pero no es superadmin, no se toca (el usuario puede
            # haber cambiado de rol manualmente).
            print(f"  [existe] superadmin {username} ({email})")
            creados.append(existente)
            continue

        user = models.User(
            username=username,
            email=email,
            password_hash=security.hash_password(default_password),
            full_name=full_name,
            role=models.UserRole.SUPERADMIN.value,
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"  [creado] superadmin {username} ({email})")
        creados.append(user)
    return creados


def sembrar_mkt(db, default_password: str) -> list[models.User]:
    """Idempotente Y reconciliadora: a este roster nominal (13 personas fijas
    del equipo de marketing) el organigrama de accesos es la fuente de verdad
    de su rol, asi que si alguien ya existe con un rol distinto al que le toca
    hoy (ej. quedo en el default viejo antes de que existiera su tier), se
    actualiza — no se pisa una cuenta creada por fuera de este roster."""
    creados = []
    for full_name, email in USUARIOS_MKT:
        base_username = _slugify(full_name)
        role_objetivo = ROLES_ESPECIALES.get(full_name, DEFAULT_ROLE_MKT)

        # Buscar por el username/email BASE (sin desambiguar) antes de generar
        # una variante unica: `_unique_username`/`_unique_email` desambiguan
        # incrementando un sufijo apenas detectan CUALQUIER fila con ese valor
        # -- incluida la propia cuenta de esta misma persona en una corrida
        # posterior. Buscar con la variante ya desambiguada nunca encuentra a
        # quien ya existe, y esta funcion terminaria creando un duplicado en
        # cada corrida en vez de reconciliar (bug real, encontrado al probar
        # la reconciliacion antes de tocar la base real).
        existente = db.query(models.User).filter(
            (models.User.username == base_username) | (models.User.email == email)
        ).first()
        if existente:
            if existente.role != role_objetivo:
                anterior = existente.role
                existente.role = role_objetivo
                db.commit()
                db.refresh(existente)
                print(
                    f"  [actualizado] {full_name} -> {existente.username}: "
                    f"{anterior} -> {role_objetivo}"
                )
            else:
                print(f"  [existe] {full_name} -> {existente.username} / {existente.email} [{existente.role}]")
            creados.append(existente)
            continue

        # Nadie coincide con el username/email base: ahora si desambiguar,
        # por si choca con una cuenta DISTINTA (ej. alguien creado a mano con
        # el mismo slug).
        username = _unique_username(db, base_username)
        unique_email = _unique_email(db, email)
        user = models.User(
            username=username,
            email=unique_email,
            password_hash=security.hash_password(default_password),
            full_name=full_name,
            role=role_objetivo,
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"  [creado] {full_name} -> {user.username} / {user.email} [{role_objetivo}]")
        creados.append(user)

    return creados


def main() -> None:
    default_password = os.getenv("DEFAULT_USER_PASSWORD", "")
    if not default_password:
        default_password = security.generate_temp_password()
        print(f"DEFAULT_USER_PASSWORD no definida en .env - contraseña temporal: {default_password}")
        print("Agregala a .env como DEFAULT_USER_PASSWORD=<valor> para futuros seeds.\n")

    db = SessionLocal()
    try:
        print("=== Superadministradores ===")
        supers = sembrar_superadmins(db, default_password)

        print("\n=== Marketing ===")
        mkt = sembrar_mkt(db, default_password)

        print(f"\nTotal: {len(supers)} superadmins + {len(mkt)} marketing = {len(supers) + len(mkt)} usuarios")
    finally:
        db.close()


if __name__ == "__main__":
    main()
