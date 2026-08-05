"""Database engine, session factory, and base model for SQLAlchemy."""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./presupuesto.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    # Defaults de SQLAlchemy (5+10=15) se agotaban en rafagas de trafico
    # concurrente y tumbaban requests con timeout/500. SQLite solo permite un
    # escritor a la vez de todos modos (WAL arriba), pero mas conexiones en
    # el pool le dan margen a los lectores y absorben picos sin bloquear.
    pool_size=20,
    max_overflow=20,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key enforcement on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    # WAL: lectores no se bloquean con un escritor activo. En modo `delete`
    # (el default) cada escritura toma lock exclusivo del archivo completo y
    # agota el pool de conexiones bajo trafico concurrente.
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session and closes it on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
