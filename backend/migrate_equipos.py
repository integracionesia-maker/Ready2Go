"""Migracion del modulo Control de Equipos (WP2): 10 tablas + el indice unico
parcial que sostiene la invariante de disponibilidad.

Ejecutar SIEMPRE desde backend/:

    python migrate_equipos.py

Idempotente: correrla dos veces no falla y la segunda no reporta altas.

**No toca ninguna tabla de Presupuestos.** El rollback es un DROP de las 10:
nada de lo existente las referencia.

Verifica ademas que `ux_loan_item_equipo_abierto` quedo creado *y* que es
parcial. `create_all` no falla si el indice ya existe con otra definicion —una
base vieja podria tener el indice sin el `WHERE`, que bloquearia un equipo aun
despues de devolverlo—, asi que se comprueba el SQL, no solo el nombre.
"""

from app.database import Base, SessionLocal, engine

# `app.models` tiene que importarse aunque no se use directo: casi todas las
# tablas de Equipos tienen FK a `users`, y sin ese import la tabla `users` no
# esta en `Base.metadata` y `create_all` no puede resolver las referencias.
from app import folio, models  # noqa: F401
from app.models_equipos import (
    Empresa,
    Equipment,
    EquipmentAudit,
    FolioCounter,
    Loan,
    LoanEvent,
    LoanItem,
    MediaAsset,
    NotificationLog,
    ResponsivaDoc,
)

TABLAS = [
    Equipment.__table__,
    EquipmentAudit.__table__,
    Loan.__table__,
    LoanItem.__table__,
    MediaAsset.__table__,
    ResponsivaDoc.__table__,
    LoanEvent.__table__,
    NotificationLog.__table__,
    Empresa.__table__,
    FolioCounter.__table__,
]

INDICE_ABIERTO = "ux_loan_item_equipo_abierto"


def _nombres_de(tipo: str) -> set[str]:
    with engine.connect() as conn:
        filas = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = ?", (tipo,)
        ).fetchall()
    return {fila[0] for fila in filas}


def exigir_esquema_base() -> None:
    """`users` tiene que existir antes: casi todas las tablas de aqui la
    referencian. SQLite crea igual una FK a una tabla inexistente y el error
    aparece mucho despues, en el primer INSERT, sin decir que falto un paso."""
    if "users" not in _nombres_de("table"):
        raise SystemExit(
            "Falta la tabla 'users'. Esta migracion es aditiva sobre el esquema\n"
            "existente, no lo crea. Corre primero: python seed_auth.py"
        )


def crear_tablas() -> None:
    antes = _nombres_de("table")
    Base.metadata.create_all(bind=engine, tables=TABLAS, checkfirst=True)
    despues = _nombres_de("table")
    for tabla in TABLAS:
        marca = "+" if tabla.name in despues and tabla.name not in antes else "="
        estado = "creada" if marca == "+" else "ya existia"
        print(f"  {marca} tabla {tabla.name} {estado}")


def verificar_indice_parcial() -> None:
    """El indice tiene que existir Y llevar el `WHERE devuelto_at IS NULL`.

    Sin el `WHERE` seria un unique total sobre `equipment_id`: un equipo no se
    podria prestar dos veces **nunca**, ni siquiera despues de devolverlo. Es un
    fallo que no se nota hasta el segundo prestamo del mismo equipo.
    """
    with engine.connect() as conn:
        fila = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name = ?",
            (INDICE_ABIERTO,),
        ).fetchone()

    if fila is None:
        raise SystemExit(f"  ! FALTA el indice {INDICE_ABIERTO}. La invariante no esta puesta.")

    sql = (fila[0] or "").lower()
    if "where" not in sql or "devuelto_at is null" not in sql.replace('"', ""):
        raise SystemExit(
            f"  ! El indice {INDICE_ABIERTO} existe pero NO es parcial.\n"
            f"    SQL actual: {fila[0]}\n"
            "    Un unique total sobre equipment_id impide volver a prestar un equipo devuelto.\n"
            "    Hay que borrarlo a mano y volver a correr esta migracion."
        )
    print(f"  = indice {INDICE_ABIERTO} presente y parcial")


def sembrar_contador() -> None:
    db = SessionLocal()
    try:
        folio.asegurar_contador(db)
        valor = folio.sincronizar_contador(db)
        db.commit()
        print(f"  = folio_counter '{folio.SCOPE_EQUIPOS}' en {valor}")
    finally:
        db.close()


def resumen() -> None:
    db = SessionLocal()
    try:
        print(f"  equipos:       {db.query(Equipment).count()}")
        print(f"  auditorias:    {db.query(EquipmentAudit).count()}")
        print(f"  prestamos:     {db.query(Loan).count()}")
        print(f"  renglones:     {db.query(LoanItem).count()}")
        print(f"  media:         {db.query(MediaAsset).count()}")
        print(f"  responsivas:   {db.query(ResponsivaDoc).count()}")
        print(f"  eventos:       {db.query(LoanEvent).count()}")
        print(f"  notificaciones:{db.query(NotificationLog).count()}")
        print(f"  empresas:      {db.query(Empresa).count()}")
    finally:
        db.close()


def main() -> None:
    print("=== Precondiciones ===")
    exigir_esquema_base()
    print("  = tabla users presente")
    print("=== Tablas ===")
    crear_tablas()
    print("=== Invariantes ===")
    verificar_indice_parcial()
    print("=== Contador de folio ===")
    sembrar_contador()
    print("=== Resumen ===")
    resumen()
    print("Migracion de Equipos completa.")


if __name__ == "__main__":
    main()
