"""Script de migración `migrate_retirar_rol_operativo.py`: usuarios con el
rol retirado `role='operativo'` pasan a `marketing_admin`, y queda rastro en
`audit_log`."""

from app import models

from .conftest import make_user
from migrate_retirar_rol_operativo import migrar_usuarios


def test_migra_usuarios_operativo_a_marketing_admin(db):
    u = make_user(db, username="viejo.operativo", password="Passw0rd!", role="operativo")

    n = migrar_usuarios(db)

    db.refresh(u)
    assert n == 1
    assert u.role == "marketing_admin"

    log = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action == "user.role-migrated", models.AuditLog.target_id == u.id)
        .first()
    )
    assert log is not None
    assert "marketing_admin" in log.details


def test_no_toca_usuarios_con_otro_rol(db):
    u = make_user(db, username="ya.admin", password="Passw0rd!", role="admin")

    n = migrar_usuarios(db)

    db.refresh(u)
    assert n == 0
    assert u.role == "admin"


def test_es_idempotente(db):
    make_user(db, username="otro.operativo", password="Passw0rd!", role="operativo")

    primera = migrar_usuarios(db)
    segunda = migrar_usuarios(db)

    assert primera == 1
    assert segunda == 0
