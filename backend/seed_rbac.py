"""Seed del RBAC aditivo: siembra el catalogo y concede `APROBADOR_EQUIPO` a la
aprobadora del area de marketing (Melisa, acordado en la reunion del 27/07).

Ejecutar desde backend/:

    python seed_rbac.py
    python seed_rbac.py --aprobador melisa
    python seed_rbac.py --aprobador melisa.avendano@grupo-ortiz.com --crear-si-falta

Idempotente: correrlo dos veces no duplica la concesion.

Por que aqui y no una constante en el codigo: §7 del plan exige que los
destinatarios de aprobacion se resuelvan por rol desde la base. Si Melisa cambia
de puesto se revoca el aditivo — no se toca ni una linea de codigo.

La identidad de la aprobadora (usuario `melisa`, correo
melisa.avendano@grupo-ortiz.com, rol base `colaborador_mkt`) sale de
`docs/contratos/auth_me.json`. `--crear-si-falta` la da de alta con contraseña
temporal impresa una sola vez; sin esa bandera, si no existe, el seed avisa y no
inventa usuarios.
"""

import argparse

from app.database import Base, SessionLocal, engine
from app import crud_rbac, models, rbac_catalog, security
from app.models_rbac import Role, RolePermission, UserRoleGrant

APROBADOR = "APROBADOR_EQUIPO"

# Datos de la aprobadora segun docs/contratos/auth_me.json.
MELISA_USERNAME = "melisa"
MELISA_EMAIL = "melisa.avendano@grupo-ortiz.com"
MELISA_NOMBRE = "Melisa Avendano"


def _buscar_usuario(db, identificador: str):
    return (
        db.query(models.User)
        .filter(
            (models.User.username == identificador) | (models.User.email == identificador)
        )
        .first()
    )


def _crear_aprobadora(db) -> models.User:
    temp = security.generate_temp_password()
    user = models.User(
        username=MELISA_USERNAME,
        email=MELISA_EMAIL,
        password_hash=security.hash_password(temp),
        full_name=MELISA_NOMBRE,
        role=models.UserRole.COLABORADOR_MKT.value,
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  + usuario '{user.username}' creado (rol base {user.role})")
    print(f"    contraseña temporal (se imprime una sola vez): {temp}")
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed del RBAC aditivo.")
    parser.add_argument(
        "--aprobador",
        default=MELISA_USERNAME,
        help="username o correo de quien recibe APROBADOR_EQUIPO",
    )
    parser.add_argument(
        "--crear-si-falta",
        action="store_true",
        help="Da de alta a la aprobadora si no existe, con contraseña temporal.",
    )
    args = parser.parse_args()

    Base.metadata.create_all(
        bind=engine,
        tables=[Role.__table__, RolePermission.__table__, UserRoleGrant.__table__],
        checkfirst=True,
    )

    db = SessionLocal()
    try:
        print("=== Catalogo ===")
        conteo = crud_rbac.sembrar_catalogo(db)
        print(
            f"  paquetes nuevos {conteo['roles_nuevos']}, "
            f"permisos nuevos {conteo['permisos_nuevos']}, "
            f"permisos borrados {conteo['permisos_borrados']}"
        )

        print("=== Aprobadora de equipo ===")
        user = _buscar_usuario(db, args.aprobador)
        if user is None:
            if args.crear_si_falta and args.aprobador in (MELISA_USERNAME, MELISA_EMAIL):
                user = _crear_aprobadora(db)
            else:
                print(f"  ! no existe usuario '{args.aprobador}'. No se concede nada.")
                print("    Da de alta el usuario y vuelve a correr, o usa --crear-si-falta.")
                _resumen(db)
                return

        if user.role == models.UserRole.SUPERADMIN.value:
            print("  ! el objetivo es superadmin: ya tiene todo por bypass, no se concede aditivo.")
        elif crud_rbac.tiene_grant(db, user.id, APROBADOR):
            print(f"  = '{user.username}' ya tenia {APROBADOR}")
        else:
            crud_rbac.conceder(db, user.id, APROBADOR, granted_by=None)
            print(f"  + {APROBADOR} concedido a '{user.username}'")

        efectivos = rbac_catalog.a_json(
            rbac_catalog.unir(
                rbac_catalog.permisos_de_paquete(rbac_catalog.PISO),
                rbac_catalog.permisos_de_paquete(user.role),
                *[
                    rbac_catalog.permisos_de_paquete(g.role_name)
                    for g in crud_rbac.listar_grants(db, user.id)
                ],
            )
        )
        print(f"  permisos efectivos de '{user.username}':")
        for modulo, acciones in efectivos.items():
            print(f"    {modulo}: {', '.join(acciones)}")
        if "presupuestos" in efectivos:
            print("    ! OJO: el aprobador tiene permisos de presupuestos. Revisa su rol base.")

        _resumen(db)
    finally:
        db.close()


def _resumen(db) -> None:
    print("=== Resumen ===")
    print(f"  paquetes:    {db.query(Role).count()}")
    print(f"  permisos:    {db.query(RolePermission).count()}")
    print(f"  concesiones: {db.query(UserRoleGrant).count()}")


if __name__ == "__main__":
    main()
