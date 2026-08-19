"""Crea un superadmin ADICIONAL (acceso al servidor, no a la app).

La API no puede crear usuarios con rol superadmin por diseño (R4: el rol
'superadmin' no se crea ni asigna por API). Este script es la via legitima
para sembrar un segundo superadmin — por ejemplo para probar el flujo de
reset de contraseña entre superadmins
(POST /api/users/{id}/reset-password-superadmin, 2026-08-19).

Uso (desde backend/):
    python crear_superadmin_extra.py \
        --username sa2 \
        --email sa2@grupo-ortiz.com \
        --password "Clave-Segura123"

La cuenta nace con must_change_password=True: en su primer login debera
cambiar la contraseña. No reutiliza seed_auth.seed_superadmin a proposito:
aquel hace early-return si YA existe un superadmin.
"""

import argparse
import sys

from app import models, security
from app.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    error = security.validate_password_strength(args.password, args.username)
    if error:
        sys.exit(f"Contrasena invalida: {error}")

    db = SessionLocal()
    existente = (
        db.query(models.User)
        .filter(models.User.username == args.username)
        .first()
    )
    if existente:
        db.close()
        sys.exit(f"Ya existe un usuario '{args.username}'; no se crea otro.")

    usuario = models.User(
        username=args.username,
        email=args.email,
        password_hash=security.hash_password(args.password),
        full_name=args.username,
        role=models.UserRole.SUPERADMIN.value,
        must_change_password=True,
    )
    db.add(usuario)
    db.commit()
    db.close()
    print(
        f"Superadmin adicional '{args.username}' creado. "
        "Debera cambiar la contrasena en su proximo login."
    )


if __name__ == "__main__":
    main()
