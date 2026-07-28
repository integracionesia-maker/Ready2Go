"""Migracion del RBAC aditivo (WP1): crea `roles`, `role_permissions` y
`user_role_grants` y siembra el catalogo desde `app/rbac_catalog.py`.

Ejecutar SIEMPRE desde backend/ (mismo requisito que seed.py y uvicorn):

    python migrate_rbac_aditivo.py

Idempotente: correrla dos veces no falla y no duplica nada. La segunda corrida
reporta 0 altas. Reconcilia ademas las filas de permiso que ya no estan en el
catalogo, para que quitar una accion del codigo no deje la fila viva en la base.

**No toca ni una fila de `users`.** El rol base sigue siendo `users.role`; esta
migracion solo agrega la capa aditiva encima.

Rollback (§13 del plan): `RBAC_MODO=legacy` deja de consultar estas tablas sin
borrarlas. Rollback duro: DROP de las tres. `require_role(...)` sigue existiendo,
asi que los endpoints de Presupuestos funcionan sin ellas.
"""

from app.database import Base, SessionLocal, engine

# `app.models` se importa aunque no se use directo: `user_role_grants` tiene FK a
# `users`, y sin ese import la tabla no esta en `Base.metadata`.
from app import crud_rbac, models, rbac_catalog  # noqa: F401
from app.models_rbac import Role, RolePermission, UserRoleGrant

TABLAS = [Role.__table__, RolePermission.__table__, UserRoleGrant.__table__]


def crear_tablas() -> None:
    """Solo las tres del RBAC. `create_all` sin `tables=` crearia tambien las de
    Equipos, que tienen su propia migracion y su propio momento."""
    antes = set(_tablas_existentes())
    Base.metadata.create_all(bind=engine, tables=TABLAS, checkfirst=True)
    despues = set(_tablas_existentes())
    for tabla in [t.name for t in TABLAS]:
        if tabla in despues and tabla not in antes:
            print(f"  + tabla {tabla} creada")
        else:
            print(f"  = tabla {tabla} ya existia")


def exigir_esquema_base() -> None:
    """`users` tiene que existir antes: `user_role_grants` la referencia.

    SQLite **crea igual** una tabla con FK a una tabla inexistente. El error no
    aparece en la migracion sino mucho despues, en el primer INSERT, con un
    "no such table: users" que no dice que falto correr el paso anterior.
    """
    if "users" not in _tablas_existentes():
        raise SystemExit(
            "Falta la tabla 'users'. Esta migracion es aditiva sobre el esquema\n"
            "existente, no lo crea. Corre primero: python seed_auth.py"
        )


def _tablas_existentes() -> list[str]:
    with engine.connect() as conn:
        filas = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    return [fila[0] for fila in filas]


def sembrar() -> None:
    db = SessionLocal()
    try:
        conteo = crud_rbac.sembrar_catalogo(db)
        print(f"  paquetes nuevos:      {conteo['roles_nuevos']}")
        print(f"  paquetes actualizados:{conteo['roles_actualizados']}")
        print(f"  permisos nuevos:      {conteo['permisos_nuevos']}")
        print(f"  permisos borrados:    {conteo['permisos_borrados']}")

        total_paquetes = db.query(Role).count()
        total_permisos = db.query(RolePermission).count()
        total_grants = db.query(UserRoleGrant).count()
        print(f"  total en base: {total_paquetes} paquetes, {total_permisos} permisos, {total_grants} concesiones")
    finally:
        db.close()


def main() -> None:
    print("=== Precondiciones ===")
    exigir_esquema_base()
    print("  = tabla users presente")
    print("=== Tablas ===")
    crear_tablas()
    print("=== Catalogo ===")
    sembrar()
    print("Migracion RBAC aditivo completa.")


if __name__ == "__main__":
    main()
