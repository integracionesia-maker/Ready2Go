"""Maquina de estados, enumerada. Sin base de datos y sin app.

La tabla del contrato tiene 7 transiciones validas. Aqui se prueban las 7 **y las
25 invalidas**: 6 estados x 5 acciones = 30 pares posibles, ninguno sin cubrir.
Probar solo el camino feliz deja pasar exactamente el bug que el contrato quiere
evitar — que un prestamo completado acepte una devolucion, o que uno cancelado se
confirme.
"""

import itertools

import pytest

from app import loan_state
from app.loan_state import Accion, TransicionNoPermitida
from app.models_equipos import EstadoPrestamo

ESTADOS = [e.value for e in EstadoPrestamo]
ACCIONES = [
    Accion.CONFIRMAR,
    Accion.CANCELAR,
    Accion.DEVOLUCION,
    Accion.CONFIRMAR_DEVOLUCION,
    Accion.CERRAR_INCIDENCIA,
]

VALIDAS = {
    ("borrador", Accion.CONFIRMAR): "prestado",
    ("borrador", Accion.CANCELAR): "cancelado",
    ("prestado", Accion.DEVOLUCION): "pendiente_confirmacion",
    ("pendiente_confirmacion", Accion.CONFIRMAR_DEVOLUCION): None,  # depende de decisiones
    ("incompleto", Accion.CERRAR_INCIDENCIA): "completado",
}


def test_hay_exactamente_seis_estados():
    assert set(ESTADOS) == {
        "borrador",
        "prestado",
        "pendiente_confirmacion",
        "completado",
        "incompleto",
        "cancelado",
    }


def test_la_tabla_de_transiciones_tiene_exactamente_cinco_entradas():
    """Cinco entradas, siete transiciones: la de confirmar-devolucion se bifurca
    en dos destinos segun las decisiones."""
    assert set(loan_state.TRANSICIONES) == set(VALIDAS)


@pytest.mark.parametrize("estado,accion", list(VALIDAS))
def test_las_transiciones_validas_llevan_al_destino_del_diagrama(estado, accion):
    esperado = VALIDAS[(estado, accion)]
    if esperado is None:
        pytest.skip("destino variable; cubierto por las pruebas de decisiones")
    assert loan_state.estado_destino(estado, accion) == esperado


INVALIDAS = [
    (estado, accion)
    for estado, accion in itertools.product(ESTADOS, ACCIONES)
    if (estado, accion) not in VALIDAS
]


@pytest.mark.parametrize("estado,accion", INVALIDAS)
def test_cada_transicion_invalida_levanta(estado, accion):
    """23 pares. Ninguno esta en el diagrama, asi que ninguno pasa."""
    with pytest.raises(TransicionNoPermitida):
        loan_state.estado_destino(estado, accion, ["ok"])


def test_se_cubren_las_treinta_combinaciones_posibles():
    """6 estados x 5 acciones = 30 pares. 5 validos, 25 invalidos, ninguno sin
    probar. Si estos numeros cambian, alguien agrego un estado o una accion sin
    decidir que pasa con las combinaciones nuevas."""
    assert len(ESTADOS) * len(ACCIONES) == 30
    assert len(VALIDAS) == 5
    assert len(INVALIDAS) == 25


# ── Bifurcacion de confirmar-devolucion ─────────────────────────────────────


def test_todas_ok_lleva_a_completado():
    assert loan_state.destino_por_decisiones(["ok", "ok", "ok"]) == "completado"


def test_una_sola_incidencia_lleva_a_incompleto():
    assert loan_state.destino_por_decisiones(["ok", "danado", "ok"]) == "incompleto"
    assert loan_state.destino_por_decisiones(["faltante"]) == "incompleto"


def test_sin_decisiones_no_completa_en_silencio():
    """Un prestamo sin renglones no deberia llegar aqui. Si llega, se trata como
    incompleto en vez de dar por bueno algo que nadie reviso."""
    assert loan_state.destino_por_decisiones([]) == "incompleto"


def test_estado_destino_usa_las_decisiones():
    assert (
        loan_state.estado_destino("pendiente_confirmacion", Accion.CONFIRMAR_DEVOLUCION, ["ok"])
        == "completado"
    )
    assert (
        loan_state.estado_destino(
            "pendiente_confirmacion", Accion.CONFIRMAR_DEVOLUCION, ["danado"]
        )
        == "incompleto"
    )


# ── entrega_autorizada ──────────────────────────────────────────────────────


def test_solo_completado_exige_autorizacion_de_entrega():
    """La guarda se evalua contra el DESTINO. Pasar a incompleto sin autorizar
    tiene que poder hacerse: si no, un prestamo con incidencia y sin autorizacion
    no tendria a donde ir."""
    assert loan_state.exige_autorizacion_de_entrega("completado") is True
    assert loan_state.exige_autorizacion_de_entrega("incompleto") is False
    assert loan_state.exige_autorizacion_de_entrega("prestado") is False
    assert loan_state.exige_autorizacion_de_entrega("pendiente_confirmacion") is False


def test_autorizar_no_se_acepta_en_borrador_ni_en_terminales():
    """En borrador no hay folio ni responsiva que autorizar; completado y
    cancelado son terminales."""
    assert loan_state.acepta_autorizacion("borrador") is False
    assert loan_state.acepta_autorizacion("completado") is False
    assert loan_state.acepta_autorizacion("cancelado") is False


def test_autorizar_si_se_acepta_en_incompleto():
    """El caso menos obvio y el mas importante: sin el, un prestamo que llego a
    incompleto sin autorizacion no se puede cerrar nunca."""
    assert loan_state.acepta_autorizacion("incompleto") is True
    assert loan_state.acepta_autorizacion("prestado") is True
    assert loan_state.acepta_autorizacion("pendiente_confirmacion") is True


# ── devuelto_at ─────────────────────────────────────────────────────────────


def test_solo_dos_acciones_escriben_devuelto_at():
    """Si esta lista crece sin querer, un equipo queda libre antes de tiempo. Si
    encoge, queda bloqueado para siempre."""
    escriben = [a for a in ACCIONES if loan_state.escribe_devuelto_at(a)]
    assert escriben == [Accion.CANCELAR, Accion.CONFIRMAR_DEVOLUCION]


def test_registrar_devolucion_no_escribe_devuelto_at():
    """Si lo escribiera, el equipo apareceria disponible mientras el aprobador
    todavia no lo revisa, y uno marcado no_devuelto volveria a ser prestable."""
    assert loan_state.escribe_devuelto_at(Accion.DEVOLUCION) is False


def test_confirmar_no_escribe_devuelto_at():
    """Los renglones quedan abiertos: eso es lo que mantiene el equipo
    reservado."""
    assert loan_state.escribe_devuelto_at(Accion.CONFIRMAR) is False


# ── Items y media por estado ────────────────────────────────────────────────


def test_solo_el_borrador_acepta_items():
    assert loan_state.acepta_items("borrador") is True
    for estado in ESTADOS:
        if estado != "borrador":
            assert loan_state.acepta_items(estado) is False, estado


def test_las_fotos_de_entrega_y_las_firmas_solo_en_borrador():
    for kind in loan_state.kinds_de_entrega():
        assert loan_state.acepta_media("borrador", kind) is True, kind
        for estado in ESTADOS:
            if estado != "borrador":
                assert loan_state.acepta_media(estado, kind) is False, (estado, kind)


def test_las_fotos_de_devolucion_solo_en_prestado():
    for kind in loan_state.kinds_de_devolucion():
        assert loan_state.acepta_media("prestado", kind) is True, kind
        assert loan_state.acepta_media("borrador", kind) is False, kind
        assert loan_state.acepta_media("completado", kind) is False, kind


def test_un_kind_desconocido_no_se_acepta_en_ningun_estado():
    for estado in ESTADOS:
        assert loan_state.acepta_media(estado, "foto_inventada") is False, estado


def test_la_maquina_no_importa_base_de_datos_ni_fastapi():
    """"Aislada y pura": si alguien le mete una sesion o un Request, se pierde la
    posibilidad de probarla sin levantar la app."""
    import inspect

    fuente = inspect.getsource(loan_state)
    assert "from fastapi" not in fuente
    assert "sqlalchemy" not in fuente
    assert "get_db" not in fuente
