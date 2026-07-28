"""La invariante que sostiene todo el modulo: un equipo no puede estar en dos
prestamos abiertos.

La maqueta solo lo evitaba filtrando la lista al pintar. Entre que dos personas
abren la pantalla y guardan pasa tiempo suficiente para que las dos se lleven el
mismo iPhone. Aqui lo resuelve la base, no la interfaz.
"""

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app import disponibilidad, tz
from app.models_equipos import EstadoOperativo, EstadoPrestamo, LoanItem

from .conftest import HOY_CONGELADO, agregar_item, crear_equipo, crear_prestamo, usuario_con


def test_un_equipo_no_puede_estar_en_dos_prestamos_abiertos(db):
    equipo = crear_equipo(db)
    agregar_item(db, crear_prestamo(db), equipo)

    otro = crear_prestamo(db)
    db.add(LoanItem(loan_id=otro.id, equipment_id=equipo.id))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_tras_devolver_el_equipo_vuelve_a_poder_prestarse(db):
    """El indice es parcial (`WHERE devuelto_at IS NULL`). Si fuera un unique
    total, un equipo solo podria prestarse una vez en su vida."""
    equipo = crear_equipo(db)
    primero = agregar_item(db, crear_prestamo(db), equipo)

    primero.devuelto_at = tz.ahora_utc_naive()
    db.commit()

    segundo = agregar_item(db, crear_prestamo(db), equipo)
    assert segundo.id != primero.id


def test_el_mismo_equipo_no_se_repite_dentro_de_un_prestamo(db):
    """UNIQUE(loan_id, equipment_id): pedir dos veces el mismo equipo en la misma
    solicitud es un error de captura, no una cantidad."""
    equipo = crear_equipo(db)
    prestamo = crear_prestamo(db)
    agregar_item(db, prestamo, equipo)

    db.add(LoanItem(loan_id=prestamo.id, equipment_id=equipo.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_un_borrador_con_renglon_tambien_reserva(db):
    """Contrato §3: `POST /loans/{id}/items` da 409 si el equipo ya esta en otro
    prestamo abierto, y el arbitro es el indice. Un borrador con renglones
    reserva igual que un prestamo entregado.

    (El plan §4.3 dice lo contrario —"un borrador no reserva"— pero tambien dice
    que los renglones se insertan al confirmar, cosa que el contrato contradice
    al exponer POST /items sobre un borrador. Se sigue el contrato; reportado en
    docs/avances/servidor.md.)
    """
    equipo = crear_equipo(db)
    borrador = crear_prestamo(db, estado=EstadoPrestamo.BORRADOR.value)
    agregar_item(db, borrador, equipo)

    otro = crear_prestamo(db)
    db.add(LoanItem(loan_id=otro.id, equipment_id=equipo.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert disponibilidad.esta_disponible_en_db(db, equipo) is False


# ── Formula de disponibilidad ───────────────────────────────────────────────


def test_equipo_libre_y_activo_esta_disponible(db):
    equipo = crear_equipo(db)
    assert disponibilidad.esta_disponible_en_db(db, equipo) is True


def test_equipo_en_revision_no_esta_disponible_aunque_no_tenga_prestamo(db):
    equipo = crear_equipo(db, estado_operativo=EstadoOperativo.REVISION.value)
    assert disponibilidad.esta_disponible_en_db(db, equipo) is False


def test_equipo_dado_de_baja_no_esta_disponible(db):
    equipo = crear_equipo(db, estado_operativo=EstadoOperativo.BAJA.value)
    assert disponibilidad.esta_disponible_en_db(db, equipo) is False


def test_no_existe_estado_prestado(db):
    """§4.2: la disponibilidad se deriva. Si alguien agrega `prestado` al
    vocabulario de `estado_operativo`, vuelve la doble fuente de verdad que dejo
    equipos prestados para siempre."""
    assert {e.value for e in EstadoOperativo} == {"activo", "revision", "baja"}


def test_prestamo_borrado_libera_el_equipo_en_la_formula(db):
    """`is_deleted` excluye el renglon de la formula.

    OJO: el indice unico parcial NO conoce `is_deleted`. Por eso borrar un
    prestamo tiene que cerrar sus renglones (`devuelto_at`) ademas de marcarlo.
    Esta prueba documenta el hueco: la formula ya lo dice libre.
    """
    equipo = crear_equipo(db)
    prestamo = crear_prestamo(db)
    agregar_item(db, prestamo, equipo)

    prestamo.is_deleted = True
    db.commit()

    assert disponibilidad.esta_disponible_en_db(db, equipo) is True
    # Y la base sigue bloqueando: es la inconsistencia que la API debe evitar
    # cerrando los renglones al borrar.
    otro = crear_prestamo(db)
    db.add(LoanItem(loan_id=otro.id, equipment_id=equipo.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_mapa_de_prestamos_abiertos_resuelve_en_una_consulta(db):
    ana = usuario_con(db, username="ana.ruiz")
    equipo_a = crear_equipo(db, nombre="A")
    equipo_b = crear_equipo(db, nombre="B")
    equipo_libre = crear_equipo(db, nombre="C")

    prestamo = crear_prestamo(
        db, responsable=ana, fecha_regreso_esperada=date(2026, 7, 30), folio="CE-0007"
    )
    agregar_item(db, prestamo, equipo_a)
    agregar_item(db, prestamo, equipo_b)

    mapa = disponibilidad.mapa_prestamos_abiertos(db, referencia=HOY_CONGELADO)

    assert set(mapa) == {equipo_a.id, equipo_b.id}
    assert equipo_libre.id not in mapa
    abierto = mapa[equipo_a.id]
    assert abierto.folio == "CE-0007"
    assert abierto.responsable_nombre == ana.full_name
    assert abierto.responsable_user_id == ana.id
    assert abierto.fecha_regreso_esperada == date(2026, 7, 30)
    assert abierto.atrasado is False
    assert abierto.dias_atraso == 0


def test_mapa_calcula_el_atraso_en_servidor(db):
    equipo = crear_equipo(db)
    prestamo = crear_prestamo(db, fecha_regreso_esperada=date(2026, 7, 25))
    agregar_item(db, prestamo, equipo)

    mapa = disponibilidad.mapa_prestamos_abiertos(db, referencia=HOY_CONGELADO)
    assert mapa[equipo.id].atrasado is True
    assert mapa[equipo.id].dias_atraso == 3


def test_mapa_con_lista_vacia_no_consulta_nada(db):
    assert disponibilidad.mapa_prestamos_abiertos(db, equipment_ids=[]) == {}


# ── Atraso y zona horaria ───────────────────────────────────────────────────


def test_el_dia_de_vencimiento_todavia_no_es_atraso(db):
    """Vence al terminar el dia: entregar el mismo dia no es atraso."""
    assert tz.dias_de_atraso(date(2026, 7, 28), date(2026, 7, 28)) == 0
    assert tz.esta_atrasado(date(2026, 7, 28), date(2026, 7, 28)) is False
    assert tz.dias_de_atraso(date(2026, 7, 28), date(2026, 7, 29)) == 1


def test_sin_fecha_de_regreso_no_hay_atraso(db):
    assert tz.dias_de_atraso(None) == 0
    assert tz.esta_atrasado(None) is False


def test_la_fecha_de_hoy_sale_de_cdmx_no_de_utc():
    """El bug de la maqueta: entre las 18:00 y la medianoche de CDMX, `hoy` en
    UTC ya es el dia siguiente y marca atrasado un dia antes."""
    from freezegun import freeze_time

    # 2026-07-29 03:00 UTC = 2026-07-28 21:00 en CDMX.
    with freeze_time("2026-07-29 03:00:00"):
        assert tz.hoy() == date(2026, 7, 28)
        assert tz.dias_de_atraso(date(2026, 7, 28)) == 0


def test_iso_cdmx_convierte_utc_naive_con_offset():
    """Lo que se guarda es UTC sin tzinfo; lo que sale es CDMX con offset, como
    pide el contrato §0."""
    assert tz.iso_cdmx(datetime(2026, 7, 25, 16, 14, 0)) == "2026-07-25T10:14:00-06:00"


def test_iso_cdmx_recorta_microsegundos():
    """Un microsegundo suelto rompe cualquier comparacion literal contra un
    fixture congelado."""
    assert tz.iso_cdmx(datetime(2026, 7, 25, 16, 14, 0, 123456)).endswith("10:14:00-06:00")


def test_iso_cdmx_respeta_un_datetime_que_ya_trae_zona():
    from datetime import timezone

    valor = datetime(2026, 7, 25, 16, 14, 0, tzinfo=timezone.utc)
    assert tz.iso_cdmx(valor) == "2026-07-25T10:14:00-06:00"


def test_iso_cdmx_de_none_es_none():
    assert tz.iso_cdmx(None) is None
