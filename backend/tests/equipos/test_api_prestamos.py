"""Flujo completo de prestamos por HTTP: borrador, items, media, confirmar,
devolucion, aprobacion, cierre. Mas scoping, listado y CSV.
"""

from datetime import date

import pytest

import seed_equipos
from app.models_equipos import EstadoOperativo, EstadoPrestamo, Equipment, LoanItem

from .conftest import (
    PASSWORD_MKT,
    crear_prestamo,
    logueado,
    png_bytes,
    subir,
    usuario_con,
)
from ..conftest import PASSWORD_SUPERADMIN


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


@pytest.fixture
def ana(inventario, db):
    return usuario_con(db, username="ana.ruiz")


@pytest.fixture
def melisa(inventario, db):
    return usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))


def _borrador_listo(cliente, *, equipment_ids=(1,), **datos):
    """Crea un borrador con sus equipos, sus 2 fotos por equipo y las 2 firmas:
    todo lo que `POST /confirmar` exige."""
    cuerpo = {
        "area": "Contenido",
        "empresa": "MERCASYSTEM SA DE CV",
        "motivo": "Live Plaza Madero",
        "fecha_entrega": "2026-07-25",
        "fecha_regreso_esperada": "2026-07-30",
    }
    cuerpo.update(datos)
    prestamo = cliente.post("/api/loans/", json=cuerpo).json()
    loan_id = prestamo["id"]

    for equipment_id in equipment_ids:
        ficha = cliente.post(
            f"/api/loans/{loan_id}/items",
            json={
                "equipment_id": equipment_id,
                "accesorios_seleccionados": ["Cargador", "Funda"],
                "cargador_con": "responsable",
            },
        ).json()
        item_id = ficha["items"][-1]["id"]
        subir(cliente, loan_id, "foto_entrega_frente", item_id)
        subir(cliente, loan_id, "foto_entrega_atras", item_id)

    subir(cliente, loan_id, "firma_entrega")
    subir(cliente, loan_id, "firma_responsable")
    return loan_id


# ── Alta y permisos ─────────────────────────────────────────────────────────


def test_crear_borrador_nace_sin_folio_y_sin_items(inventario, ana):
    cuerpo = logueado("ana.ruiz").post("/api/loans/", json={"motivo": "Live"}).json()
    assert cuerpo["estado"] == "borrador"
    assert cuerpo["folio"] is None
    assert cuerpo["items"] == []
    assert cuerpo["entrega_autorizada"] is False
    assert cuerpo["responsiva"] is None
    assert cuerpo["responsable"]["user_id"] == ana.id


def test_un_creador_no_puede_pedir_equipo(inventario, db, creador_user):
    from ..conftest import PASSWORD_CREADOR

    resp = logueado("creador.a", PASSWORD_CREADOR).post("/api/loans/", json={})
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_el_borrador_nace_con_evento_de_bitacora(inventario, ana):
    cuerpo = logueado("ana.ruiz").post("/api/loans/", json={}).json()
    assert [e["tipo"] for e in cuerpo["eventos"]] == ["creado"]
    assert cuerpo["eventos"][0]["actor"] == ana.full_name


# ── Renglones ───────────────────────────────────────────────────────────────


def test_agregar_equipo_lo_saca_del_inventario_disponible(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1})

    fila = next(
        i for i in cliente.get("/api/equipment/").json()["items"] if i["id"] == 1
    )
    assert fila["disponible"] is False


def test_un_equipo_en_dos_prestamos_abiertos_da_409(inventario, ana, db):
    cliente = logueado("ana.ruiz")
    primero = cliente.post("/api/loans/", json={}).json()["id"]
    cliente.post(f"/api/loans/{primero}/items", json={"equipment_id": 1})

    segundo = cliente.post("/api/loans/", json={}).json()["id"]
    resp = cliente.post(f"/api/loans/{segundo}/items", json={"equipment_id": 1})

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "EQUIPO_OCUPADO"


def test_el_mismo_equipo_dos_veces_en_el_mismo_prestamo_da_409(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1})
    resp = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1})
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "DUPLICADO"


def test_un_equipo_en_revision_no_se_puede_pedir(inventario, ana, db):
    """§10.14: la maqueta lo validaba solo al pintar."""
    db.get(Equipment, 1).estado_operativo = EstadoOperativo.REVISION.value
    db.commit()

    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    resp = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1})

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "EQUIPO_NO_DISPONIBLE"


def test_quitar_un_renglon_libera_el_equipo(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    ficha = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1}).json()
    item_id = ficha["items"][0]["id"]

    cliente.delete(f"/api/loans/{loan_id}/items/{item_id}")

    fila = next(i for i in cliente.get("/api/equipment/").json()["items"] if i["id"] == 1)
    assert fila["disponible"] is True


def test_no_se_agregan_equipos_a_un_prestamo_ya_confirmado(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _borrador_listo(cliente)
    cliente.post(f"/api/loans/{loan_id}/confirmar")

    resp = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 2})
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"


# ── Confirmar ───────────────────────────────────────────────────────────────


def test_confirmar_sin_equipos_no_quema_folio(inventario, ana):
    """El contrato no exige un minimo de equipos, asi que la regla de "2 fotos
    por equipo" se cumple de forma vacia. Sin esta guarda se confirma un prestamo
    sin nada, se quema un folio y se genera una responsiva en blanco."""
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]

    resp = cliente.post(f"/api/loans/{loan_id}/confirmar")
    assert resp.status_code == 409
    assert "al menos un equipo" in resp.json()["detail"]
    assert cliente.get(f"/api/loans/{loan_id}").json()["folio"] is None


def test_confirmar_sin_fotos_dice_que_falta(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1})

    resp = cliente.post(f"/api/loans/{loan_id}/confirmar")
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"
    # El detalle dice QUE falta, no un texto generico (contrato §3).
    assert "fotos" in resp.json()["detail"]


def test_confirmar_sin_firmas_dice_cual_falta(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    ficha = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1}).json()
    item_id = ficha["items"][0]["id"]
    subir(cliente, loan_id, "foto_entrega_frente", item_id)
    subir(cliente, loan_id, "foto_entrega_atras", item_id)
    subir(cliente, loan_id, "firma_entrega")

    resp = cliente.post(f"/api/loans/{loan_id}/confirmar")
    assert resp.status_code == 409
    assert "firma de quien recibe" in resp.json()["detail"]


def test_dos_fotos_del_mismo_lado_no_cuentan_como_dos_fotos(inventario, ana):
    """Se cuentan kinds distintos, no filas. Con COUNT(*)=2 un renglon con dos
    fotos de frente y cero de atras pasaria la validacion."""
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    ficha = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1}).json()
    item_id = ficha["items"][0]["id"]

    subir(cliente, loan_id, "foto_entrega_frente", item_id)
    subir(cliente, loan_id, "foto_entrega_frente", item_id)
    subir(cliente, loan_id, "firma_entrega")
    subir(cliente, loan_id, "firma_responsable")

    resp = cliente.post(f"/api/loans/{loan_id}/confirmar")
    assert resp.status_code == 409
    assert "atras" in resp.json()["detail"]


def test_confirmar_asigna_folio_y_genera_responsiva_v1(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _borrador_listo(cliente)

    cuerpo = cliente.post(f"/api/loans/{loan_id}/confirmar").json()
    assert cuerpo["estado"] == "prestado"
    assert cuerpo["folio"] == "CE-0001"
    assert cuerpo["responsiva"]["version"] == 1
    assert cuerpo["responsiva"]["url"] == f"/api/loans/{loan_id}/responsiva.pdf"
    assert cuerpo["entrega_autorizada"] is False
    assert cuerpo["items"][0]["devuelto_at"] is None


def test_confirmar_dos_veces_no_reasigna_folio(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _borrador_listo(cliente)
    primera = cliente.post(f"/api/loans/{loan_id}/confirmar").json()

    segunda = cliente.post(f"/api/loans/{loan_id}/confirmar")
    assert segunda.status_code == 409
    assert cliente.get(f"/api/loans/{loan_id}").json()["folio"] == primera["folio"]


def test_confirmar_deja_el_equipo_ocupado(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _borrador_listo(cliente)
    cliente.post(f"/api/loans/{loan_id}/confirmar")

    fila = next(i for i in cliente.get("/api/equipment/").json()["items"] if i["id"] == 1)
    assert fila["disponible"] is False
    assert fila["tenedor_actual"]["nombre"] == "ana.ruiz"


def test_confirmar_no_toca_estado_operativo_del_equipo(inventario, ana, db):
    """No existe `estado_operativo='prestado'`: escribirlo seria la doble fuente
    de verdad que el modulo existe para evitar."""
    cliente = logueado("ana.ruiz")
    cliente.post(f"/api/loans/{_borrador_listo(cliente)}/confirmar")
    assert db.get(Equipment, 1).estado_operativo == EstadoOperativo.ACTIVO.value


# ── Cancelar ────────────────────────────────────────────────────────────────


def test_cancelar_exige_un_permiso_que_solo_tiene_superadmin(inventario, ana):
    """Defecto del catalogo congelado: `equipos_prestamos:cancelar` no lo
    concede ningun paquete. Quien crea un borrador no puede cancelarlo."""
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]

    resp = cliente.post(f"/api/loans/{loan_id}/cancelar", json={})
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_cancelar_libera_los_equipos(inventario, db, superadmin_user):
    """Sin escribir `devuelto_at` al cancelar, el indice unico dejaria el equipo
    bloqueado mientras la formula de disponibilidad lo muestra libre."""
    cliente = logueado("superadmin", PASSWORD_SUPERADMIN)
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1})

    cuerpo = cliente.post(f"/api/loans/{loan_id}/cancelar", json={"motivo": "Se pospuso"}).json()
    assert cuerpo["estado"] == "cancelado"
    assert cuerpo["items"][0]["devuelto_at"] is not None

    fila = next(i for i in cliente.get("/api/equipment/").json()["items"] if i["id"] == 1)
    assert fila["disponible"] is True

    # Y el equipo se puede volver a pedir de verdad, no solo en la pantalla.
    otro = cliente.post("/api/loans/", json={}).json()["id"]
    assert cliente.post(f"/api/loans/{otro}/items", json={"equipment_id": 1}).status_code == 201


def test_un_cancelado_nunca_tiene_folio(inventario, superadmin_user):
    cliente = logueado("superadmin", PASSWORD_SUPERADMIN)
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    assert cliente.post(f"/api/loans/{loan_id}/cancelar", json={}).json()["folio"] is None


def test_no_se_cancela_un_prestamo_ya_entregado(inventario, ana, superadmin_user):
    """El diagrama del contrato solo dibuja la flecha desde borrador. El plan §5
    decia "borrador/prestado"; manda el contrato."""
    loan_id = _borrador_listo(logueado("ana.ruiz"))
    logueado("ana.ruiz").post(f"/api/loans/{loan_id}/confirmar")

    resp = logueado("superadmin", PASSWORD_SUPERADMIN).post(
        f"/api/loans/{loan_id}/cancelar", json={}
    )
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"


# ── Devolucion ──────────────────────────────────────────────────────────────


def _confirmado(cliente, equipment_ids=(1,)):
    loan_id = _borrador_listo(cliente, equipment_ids=equipment_ids)
    cliente.post(f"/api/loans/{loan_id}/confirmar")
    return loan_id


def test_devolucion_exige_fotos_de_devolucion(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]

    resp = cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={"items": [{"loan_item_id": item_id, "no_devuelto": False}]},
    )
    assert resp.status_code == 409
    assert "fotos de devolucion" in resp.json()["detail"]


def test_devolucion_con_fotos_pasa_a_pendiente_confirmacion(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]
    subir(cliente, loan_id, "foto_dev_frente", item_id)
    subir(cliente, loan_id, "foto_dev_atras", item_id)

    cuerpo = cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={"items": [{"loan_item_id": item_id, "no_devuelto": False}]},
    ).json()

    assert cuerpo["estado"] == "pendiente_confirmacion"
    assert cuerpo["fecha_regreso_real"] is not None
    # NO escribe devuelto_at: el equipo sigue fuera hasta que el aprobador mire.
    assert cuerpo["items"][0]["devuelto_at"] is None


def test_el_equipo_sigue_ocupado_mientras_espera_confirmacion(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]
    subir(cliente, loan_id, "foto_dev_frente", item_id)
    subir(cliente, loan_id, "foto_dev_atras", item_id)
    cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={"items": [{"loan_item_id": item_id}]},
    )

    fila = next(i for i in cliente.get("/api/equipment/").json()["items"] if i["id"] == 1)
    assert fila["disponible"] is False


def test_no_devuelto_exige_nota(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]

    resp = cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={"items": [{"loan_item_id": item_id, "no_devuelto": True}]},
    )
    assert resp.status_code == 409
    assert "nota" in resp.json()["detail"]


def test_no_devuelto_con_nota_no_pide_fotos(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]

    cuerpo = cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={
            "items": [
                {
                    "loan_item_id": item_id,
                    "no_devuelto": True,
                    "nota_devolucion": "Se quedo en la plaza, se recupera el lunes.",
                }
            ]
        },
    ).json()
    assert cuerpo["estado"] == "pendiente_confirmacion"
    assert cuerpo["items"][0]["no_devuelto"] is True


def test_la_devolucion_es_atomica_sobre_todos_los_equipos(inventario, ana):
    """No hay devolucion parcial: o se resuelven los N renglones, o no pasa
    nada."""
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente, equipment_ids=(1, 2))
    items = cliente.get(f"/api/loans/{loan_id}").json()["items"]
    subir(cliente, loan_id, "foto_dev_frente", items[0]["id"])
    subir(cliente, loan_id, "foto_dev_atras", items[0]["id"])

    resp = cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={"items": [{"loan_item_id": items[0]["id"]}]},
    )
    assert resp.status_code == 409
    assert cliente.get(f"/api/loans/{loan_id}").json()["estado"] == "prestado"


def test_un_renglon_de_otro_prestamo_es_404(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente, equipment_ids=(1,))
    otro = _confirmado(cliente, equipment_ids=(2,))
    ajeno = cliente.get(f"/api/loans/{otro}").json()["items"][0]["id"]

    resp = cliente.post(
        f"/api/loans/{loan_id}/devolucion", json={"items": [{"loan_item_id": ajeno}]}
    )
    assert resp.status_code == 404


# ── Scoping y visibilidad ───────────────────────────────────────────────────


def test_un_colaborador_no_ve_el_prestamo_de_otro(inventario, ana, db):
    otro = usuario_con(db, username="betza")
    loan_id = logueado("ana.ruiz").post("/api/loans/", json={}).json()["id"]

    resp = logueado("betza").get(f"/api/loans/{loan_id}")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_la_aprobadora_si_ve_prestamos_ajenos(inventario, ana, melisa):
    """`APROBADOR_EQUIPO` trae `ver_global`: sin eso, Melisa no podria revisar lo
    que tiene que aprobar."""
    loan_id = logueado("ana.ruiz").post("/api/loans/", json={}).json()["id"]
    assert logueado("melisa").get(f"/api/loans/{loan_id}").status_code == 200


def test_el_listado_de_un_colaborador_solo_trae_lo_suyo(inventario, ana, db):
    usuario_con(db, username="betza")
    logueado("ana.ruiz").post("/api/loans/", json={"motivo": "De Ana"})
    logueado("betza").post("/api/loans/", json={"motivo": "De Betza"})

    cuerpo = logueado("betza").get("/api/loans/").json()
    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["motivo"] == "De Betza"


def test_mios_filtra_incluso_para_quien_ve_todo(inventario, ana, melisa):
    logueado("ana.ruiz").post("/api/loans/", json={"motivo": "De Ana"})
    logueado("melisa").post("/api/loans/", json={"motivo": "De Melisa"})
    cliente = logueado("melisa")

    assert cliente.get("/api/loans/").json()["total"] == 2
    propios = cliente.get("/api/loans/", params={"mios": True}).json()
    assert propios["total"] == 1
    assert propios["items"][0]["motivo"] == "De Melisa"


def test_el_wizard_recupera_su_borrador(inventario, ana):
    """`?estado=borrador&mios=1` es el unico mecanismo de recuperacion si la
    persona cierra la pestaña."""
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={"motivo": "A medias"}).json()["id"]
    cliente.post(f"/api/loans/{_borrador_listo(cliente, equipment_ids=(2,))}/confirmar")

    cuerpo = cliente.get("/api/loans/", params={"estado": "borrador", "mios": True}).json()
    assert [i["id"] for i in cuerpo["items"]] == [loan_id]


def test_prestamo_inexistente_es_404_no_403(inventario, ana):
    resp = logueado("ana.ruiz").get("/api/loans/9999")
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_by_folio_devuelve_la_misma_ficha(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    por_id = cliente.get(f"/api/loans/{loan_id}").json()
    por_folio = cliente.get(f"/api/loans/by-folio/{por_id['folio']}").json()
    assert por_folio == por_id


def test_by_folio_de_un_folio_inexistente_es_404(inventario, ana):
    assert logueado("ana.ruiz").get("/api/loans/by-folio/CE-9999").status_code == 404


def test_export_no_se_lo_traga_la_ruta_por_id(inventario, db):
    """`/export` va declarado antes de `/{loan_id:int}`."""
    usuario_con(db, username="adm", role="admin")
    resp = logueado("adm").get("/api/loans/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")


def test_el_csv_lleva_bom_y_las_columnas_declaradas(inventario, ana, db):
    from app import crud_loans

    logueado("ana.ruiz")
    cliente_ana = logueado("ana.ruiz")
    _confirmado(cliente_ana)

    usuario_con(db, username="adm", role="admin")
    texto = logueado("adm").get("/api/loans/export").text

    assert texto.startswith("﻿"), "sin BOM, Excel destroza los acentos"
    encabezado = texto.lstrip("﻿").splitlines()[0]
    assert encabezado.split(",") == crud_loans.COLUMNAS_CSV


def test_un_colaborador_no_puede_exportar(inventario, ana):
    assert logueado("ana.ruiz").get("/api/loans/export").status_code == 403


def test_el_atraso_lo_calcula_el_servidor(inventario, ana, db):
    from freezegun import freeze_time

    prestamo = crear_prestamo(
        db,
        responsable=usuario_con(db, username="tarde"),
        estado=EstadoPrestamo.PRESTADO.value,
        fecha_regreso_esperada=date(2026, 7, 25),
        folio="CE-0100",
    )
    with freeze_time("2026-07-28 18:00:00"):
        cuerpo = logueado("tarde").get(f"/api/loans/{prestamo.id}").json()

    assert cuerpo["atrasado"] is True
    assert cuerpo["dias_atraso"] == 3


def test_un_prestamo_ya_cerrado_no_se_atrasa_para_siempre(inventario, db):
    """Comparar contra hoy diria "atrasado 90 dias" de un prestamo cerrado hace
    tres meses. Se compara contra la fecha real de regreso."""
    from freezegun import freeze_time

    prestamo = crear_prestamo(
        db,
        responsable=usuario_con(db, username="cerrado"),
        estado=EstadoPrestamo.COMPLETADO.value,
        fecha_regreso_esperada=date(2026, 7, 25),
        folio="CE-0101",
    )
    prestamo.fecha_regreso_real = date(2026, 7, 24)
    db.commit()

    with freeze_time("2026-12-31 18:00:00"):
        cuerpo = logueado("cerrado").get(f"/api/loans/{prestamo.id}").json()

    assert cuerpo["atrasado"] is False
    assert cuerpo["dias_atraso"] == 0
