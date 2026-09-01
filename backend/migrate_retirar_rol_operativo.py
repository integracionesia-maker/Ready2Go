"""Retira el rol base `operativo` (WP fusion Gastos Operativos -> Presupuestos).

Migra cada `User` con `role == "operativo"` a `role = "marketing_admin"` (ya
tiene acceso completo a Presupuestos, incluida la parte operativa fusionada),
deja un rastro en `audit_log`, y borra la fila huerfana `roles.name='operativo'`
que deja atras `migrate_rbac_aditivo.py` al reconciliar `role_permissions` (esa
reconciliacion nunca borra `Role`, solo `RolePermission`).

Ejecutar SIEMPRE desde backend/, DESPUES de correr `python migrate_rbac_aditivo.py`
para que la reconciliacion de `role_permissions` ya haya corrido:

    python migrate_retirar_rol_operativo.py

Idempotente: correrla dos veces no falla (la segunda no encuentra usuarios que
migrar ni la fila `roles.name='operativo'`).
"""

from app.database import SessionLocal
from app import crud, models
from app.models_rbac import Role, UserRoleGrant


def migrar_usuarios(db) -> int:
    afectados = db.query(models.User).filter(models.User.role == "operativo").all()
    for u in afectados:
        print(f"  {u.username} (id={u.id}): operativo -> marketing_admin")
        u.role = "marketing_admin"
        crud.log_audit(
            db,
            actor_user_id=None,
            action="user.role-migrated",
            target_type="user",
            target_id=u.id,
            details="operativo -> marketing_admin (retiro del rol, fusion gastos operativos)",
        )
    db.commit()
    return len(afectados)


def borrar_rol_huerfano(db) -> bool:
    rol = db.query(Role).filter(Role.name == "operativo").first()
    if rol is None:
        return False
    # Un rol BASE nunca deberia tener grants aditivos apuntandole (ver
    # test_no_se_puede_conceder_un_paquete_base_como_aditivo). Si esto revienta
    # por la FK de UserRoleGrant, es un dato corrupto a investigar a mano, no a
    # silenciar con un try/except.
    grants = db.query(UserRoleGrant).filter(UserRoleGrant.role_name == "operativo").count()
    if grants:
        raise SystemExit(
            f"Hay {grants} UserRoleGrant apuntando a 'operativo' (un rol base). "
            "Esto no deberia pasar nunca — investigar antes de continuar."
        )
    db.delete(rol)
    db.commit()
    return True


def main() -> None:
    db = SessionLocal()
    try:
        print("=== Migrando usuarios con role='operativo' ===")
        n = migrar_usuarios(db)
        print(f"Usuarios migrados: {n}")

        print("=== Borrando fila huerfana roles.name='operativo' (si existe) ===")
        borrada = borrar_rol_huerfano(db)
        print("  borrada" if borrada else "  no existia (ya limpio)")

        restantes = db.query(models.User).filter(models.User.role == "operativo").count()
        if restantes:
            raise SystemExit(f"ERROR: siguen quedando {restantes} usuarios con role='operativo'")
        print("Verificacion OK: 0 usuarios con role='operativo'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
