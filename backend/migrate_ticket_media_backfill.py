"""Backfill de `ticket_media`: copia el comprobante de cada ticket existente
(guardado hoy en las columnas `file_name`/`file_path`/`mime_type` de
`tickets`) a una fila de la nueva tabla `ticket_media`, para que tickets de
antes de esta migracion tambien aparezcan en el listado de fotos por ticket
(`ticket.media`, usado por el visor con navegacion multiple).

La tabla `ticket_media` se crea sola al arrancar el backend
(`Base.metadata.create_all` en `main.py`) — este script SOLO hace el backfill
de datos, no el `CREATE TABLE`.

Ejecutar SIEMPRE desde backend/ (mismo requisito que seed.py y uvicorn):

    python migrate_ticket_media_backfill.py

Idempotente: un ticket que ya tiene alguna fila en `ticket_media` (tickets
creados despues de este cambio, o una segunda corrida del script) se salta.
"""

from app.database import SessionLocal
from app import models


def main() -> None:
    db = SessionLocal()
    try:
        tickets = db.query(models.Ticket).all()
        creadas = 0
        for ticket in tickets:
            ya_tiene_media = (
                db.query(models.TicketMedia)
                .filter(models.TicketMedia.ticket_id == ticket.id)
                .first()
            )
            if ya_tiene_media:
                continue
            db.add(
                models.TicketMedia(
                    ticket_id=ticket.id,
                    file_name=ticket.file_name,
                    file_path=ticket.file_path,
                    mime_type=ticket.mime_type,
                    upload_date=ticket.upload_date,
                )
            )
            creadas += 1
        db.commit()
        print(f"Backfill completado: {creadas} fila(s) de ticket_media creadas "
              f"({len(tickets) - creadas} ticket(s) ya tenian media).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
