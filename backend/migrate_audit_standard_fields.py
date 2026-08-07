"""Migracion aditiva de `audit_log`: agrega la columna `standard_fields` (TEXT,
JSON serializado con el esquema estandar de auditoria para export/ingesta en
proyectos futuros).

Ejecutar SIEMPRE desde backend/ (mismo requisito que seed.py y uvicorn):

    python migrate_audit_standard_fields.py

Idempotente: usa try/except sobre la excepcion de SQLite para "columna ya
existe", ya que SQLite no soporta `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
nativo.
"""

from app.database import engine


def main() -> None:
    with engine.connect() as conn:
        try:
            conn.exec_driver_sql(
                "ALTER TABLE audit_log ADD COLUMN standard_fields TEXT"
            )
            conn.commit()
            print("  + columna standard_fields agregada a audit_log")
        except Exception as exc:
            # SQLite no tiene codigos de error estructurados — si el mensaje
            # menciona "duplicate column", la columna ya existe.
            msg = str(exc).lower()
            if "duplicate column" in msg or "already exists" in msg:
                print("  - columna standard_fields ya existe (omitida)")
            else:
                raise
    print("Migracion de standard_fields en audit_log completada.")


if __name__ == "__main__":
    main()
