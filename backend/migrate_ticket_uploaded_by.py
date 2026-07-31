"""Migracion aditiva de `tickets`: agrega la columna `uploaded_by_user_id`
(quien subio el ticket, distinto de `creator_id` que es el creador de
contenido al que pertenece el gasto). La usa el rol `marketing_basico`
(organigrama de accesos, jul-2026) para acotar "ver_propio" a lo que el mismo
subio, ya que no tiene un `creator_id` propio como "creador".

Ejecutar SIEMPRE desde backend/ (mismo requisito que seed.py y uvicorn):

    python migrate_ticket_uploaded_by.py

Idempotente: SQLite no soporta `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`,
asi que el error de "columna ya existe" se descarta explicitamente (no
cualquier OperationalError). Tickets existentes quedan con NULL — no hay
forma retroactiva de saber quien los subio, y no hace falta: solo afecta a
tickets nuevos de marketing_basico, un rol que no existia antes de esta
migracion.
"""

from sqlalchemy.exc import OperationalError

from app.database import engine


def main() -> None:
    with engine.connect() as conn:
        try:
            conn.exec_driver_sql(
                "ALTER TABLE tickets ADD COLUMN uploaded_by_user_id INTEGER "
                "REFERENCES users(id)"
            )
            conn.commit()
            print("  + columna uploaded_by_user_id agregada")
        except OperationalError as exc:
            if "duplicate column name" in str(exc).lower():
                print("  = columna uploaded_by_user_id ya existia")
            else:
                raise
    print("Migracion de tickets.uploaded_by_user_id completada.")


if __name__ == "__main__":
    main()
