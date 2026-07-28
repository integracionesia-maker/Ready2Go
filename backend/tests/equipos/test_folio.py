"""Folio unico bajo carrera.

La maqueta llevaba el contador en el estado del navegador: dos pestañas producian
`CE-0007` las dos y nadie lo notaba hasta tener dos cartas responsivas firmadas
con el mismo numero (§10.5 del plan).
"""

import threading

import pytest
from sqlalchemy.exc import IntegrityError

from app import folio as folio_mod
from app.database import SessionLocal
from app.models_equipos import FolioCounter, Loan

from .conftest import crear_prestamo


def test_formato_es_ce_cuatro_digitos():
    assert folio_mod.formatear(1) == "CE-0001"
    assert folio_mod.formatear(7) == "CE-0007"
    assert folio_mod.formatear(1234) == "CE-1234"
    # No se trunca al pasar de 4 digitos: perder un digito duplicaria folios.
    assert folio_mod.formatear(12345) == "CE-12345"


def test_asigna_folios_consecutivos(db):
    folios = []
    for _ in range(5):
        prestamo = crear_prestamo(db)
        folios.append(folio_mod.asignar_folio(db, prestamo))
        db.commit()
    assert folios == ["CE-0001", "CE-0002", "CE-0003", "CE-0004", "CE-0005"]


def test_no_reasigna_folio_a_un_prestamo_que_ya_lo_tiene(db):
    """Un folio ya impreso en una carta firmada no se cambia."""
    prestamo = crear_prestamo(db, folio="CE-0099")
    assert folio_mod.asignar_folio(db, prestamo) == "CE-0099"


def test_la_base_rechaza_dos_prestamos_con_el_mismo_folio(db):
    crear_prestamo(db, folio="CE-0007")
    db.add(Loan(folio="CE-0007", responsable_nombre="Otro", estado="borrador"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_contador_atrasado_reintenta_hasta_encontrar_hueco(db):
    """Escenario real: se restauro un respaldo o se sembraron datos de demo con
    folios fijos y el contador quedo atras. El reintento tiene que resolverlo,
    no producir un duplicado ni reventar."""
    crear_prestamo(db, folio="CE-0001")
    crear_prestamo(db, folio="CE-0002")
    folio_mod.asegurar_contador(db)
    db.get(FolioCounter, "CE").last_value = 0
    db.commit()

    prestamo = crear_prestamo(db)
    asignado = folio_mod.asignar_folio(db, prestamo)
    db.commit()

    assert asignado == "CE-0003"
    assert db.query(Loan).filter(Loan.folio == "CE-0003").count() == 1


def test_se_rinde_con_error_explicito_en_vez_de_duplicar(db):
    """Si tras los reintentos no hay hueco, sale error. Un folio repetido en dos
    cartas firmadas es peor que un prestamo que no se confirmo."""
    for numero in range(1, folio_mod.REINTENTOS + 2):
        crear_prestamo(db, folio=folio_mod.formatear(numero))
    folio_mod.asegurar_contador(db)
    db.get(FolioCounter, "CE").last_value = 0
    db.commit()

    with pytest.raises(folio_mod.FolioNoDisponible):
        folio_mod.asignar_folio(db, crear_prestamo(db))


def test_sincronizar_contador_lo_sube_al_folio_mas_alto(db):
    crear_prestamo(db, folio="CE-0007")
    crear_prestamo(db, folio="CE-0003")
    folio_mod.sincronizar_contador(db)
    db.commit()
    assert db.get(FolioCounter, "CE").last_value == 7


def test_sincronizar_ignora_folios_con_forma_rara(db):
    crear_prestamo(db, folio="CE-0002")
    crear_prestamo(db, folio="CE-VIEJO")
    folio_mod.sincronizar_contador(db)
    db.commit()
    assert db.get(FolioCounter, "CE").last_value == 2


def test_concurrencia_real_no_produce_folios_repetidos(db):
    """Hilos de verdad, sesiones independientes, misma base.

    No prueba el planificador del sistema operativo: prueba que si dos
    transacciones se cruzan, ninguna se lleva un folio repetido. El arbitro es el
    UNIQUE de la base mas el reintento, no el orden en que corran.
    """
    folio_mod.asegurar_contador(db)
    db.commit()

    hilos_n = 6
    resultados: list[str] = []
    errores: list[Exception] = []
    candado = threading.Lock()
    arranque = threading.Barrier(hilos_n)

    def trabajo(indice: int) -> None:
        sesion = SessionLocal()
        try:
            prestamo = Loan(responsable_nombre=f"Hilo {indice}", estado="borrador")
            sesion.add(prestamo)
            sesion.flush()
            arranque.wait(timeout=10)
            asignado = folio_mod.asignar_folio(sesion, prestamo)
            sesion.commit()
            with candado:
                resultados.append(asignado)
        except Exception as exc:  # noqa: BLE001 — se reportan al final
            sesion.rollback()
            with candado:
                errores.append(exc)
        finally:
            sesion.close()

    hilos = [threading.Thread(target=trabajo, args=(i,)) for i in range(hilos_n)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    # Lo unico inaceptable es un folio repetido. Que alguno falle por bloqueo de
    # SQLite es tolerable —reintenta el usuario—; que dos cartas lleven el mismo
    # numero no lo es.
    assert len(resultados) == len(set(resultados)), f"folios repetidos: {resultados}"

    en_base = [f for (f,) in db.query(Loan.folio).filter(Loan.folio.isnot(None)).all()]
    assert len(en_base) == len(set(en_base)), f"folios repetidos en base: {en_base}"
    assert resultados or errores, "ningun hilo termino"
