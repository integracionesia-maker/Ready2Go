"""Migracion aditiva de `audit_log`: agrega las columnas del middleware de
auditoria automatica (http_method, endpoint_path, request_params,
request_body_summary, response_status, user_agent, duration_ms) sin tocar
las filas existentes.

Ejecutar SIEMPRE desde backend/ (mismo requisito que seed.py y uvicorn):

    python migrate_audit_enhanced.py

Idempotente: SQLite no soporta `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`,
asi que cada columna se intenta y el error de "columna ya existe" se
descarta explicitamente (no cualquier OperationalError).
"""

from sqlalchemy.exc import OperationalError

from app.database import engine

COLUMNAS_NUEVAS = [
    ("http_method", "VARCHAR(10)"),
    ("endpoint_path", "VARCHAR(255)"),
    ("request_params", "TEXT"),
    ("request_body_summary", "TEXT"),
    ("response_status", "INTEGER"),
    ("user_agent", "VARCHAR(255)"),
    ("duration_ms", "INTEGER"),
]


def main() -> None:
    with engine.connect() as conn:
        for nombre, tipo in COLUMNAS_NUEVAS:
            try:
                conn.exec_driver_sql(f"ALTER TABLE audit_log ADD COLUMN {nombre} {tipo}")
                conn.commit()
                print(f"  + columna {nombre} agregada")
            except OperationalError as exc:
                if "duplicate column name" in str(exc).lower():
                    print(f"  = columna {nombre} ya existia")
                else:
                    raise
    print("Migracion de audit_log completada.")


if __name__ == "__main__":
    main()
