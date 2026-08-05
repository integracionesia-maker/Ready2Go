"""Migracion aditiva de `audit_log`: agrega los indices de `created_at` y
`actor_user_id` (ver `app/models.py::AuditLog.__table_args__`). Sin ellos,
cada GET /api/audit-logs/ (orden por defecto + filtro por usuario) es un
table scan completo de la tabla.

Ejecutar SIEMPRE desde backend/ (mismo requisito que seed.py y uvicorn):

    python migrate_audit_indices.py

Idempotente: usa `CREATE INDEX IF NOT EXISTS`, nativo de SQLite (a diferencia
de `ALTER TABLE ... ADD COLUMN`, que no lo soporta).
"""

from app.database import engine

INDICES = [
    ("ix_audit_log_created_at", "created_at"),
    ("ix_audit_log_actor_user_id", "actor_user_id"),
]


def main() -> None:
    with engine.connect() as conn:
        for nombre, columna in INDICES:
            conn.exec_driver_sql(
                f"CREATE INDEX IF NOT EXISTS {nombre} ON audit_log ({columna})"
            )
            conn.commit()
            print(f"  + indice {nombre} listo")
    print("Migracion de indices de audit_log completada.")


if __name__ == "__main__":
    main()
