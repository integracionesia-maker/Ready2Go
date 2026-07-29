"""Aprobacion (contrato §4): autorizar entrega, confirmar devolucion, cerrar
incidencia.

El caso mas delicado del modulo esta aqui: un prestamo devuelto con todo `ok`
pero **sin autorizacion de entrega** no puede llegar a `completado`. §4 dice
"todas ok -> completado" sin condicion; §3 dice que sin autorizacion no se llega
a completado. Manda §3, y la operacion se rechaza ANTES de escribir nada.
"""

import pytest

import seed_equipos
from app.models_equipos import EstadoOperativo, Equipment

from .conftest import logueado, subir, usuario_con
from ..conftest import PASSWORD_SUPERADMIN


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    # Las razones sociales hacen falta: confirmar genera la carta responsiva, y
    # la emisora sale de la tabla `empresa`. Sin ella el prestamo no se confirma
    # — a proposito: no se entrega equipo sin carta.
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


@pytest.fixture
def ana(inventario, db):
    return usuario_con(db, username="ana.ruiz")


@pytest.fixture
def melisa(inventario, db):
    return usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))


def _prestado(cliente, equipment_ids=(1,)):
    loan_id = cliente.post(
        "/api/loans/", json={"motivo": "Live", "fecha_regreso_esperada": "2026-12-31"}
    ).json()["id"]
    for equipment_id in equipment_ids:
        ficha = cliente.post(
            f"/api/loans/{loan_id}/items", json={"equipment_id": equipment_id}
        ).json()
        item_id = ficha["items"][-1]["id"]
        subir(cliente, loan_id, "foto_entrega_frente", item_id)
        subir(cliente, loan_id, "foto_entrega_atras", item_id)
    subir(cliente, loan_id, "firma_entrega")
    subir(cliente, loan_id, "firma_responsable")
    cliente.post(f"/api/loans/{loan_id}/confirmar")
    return loan_id


def _devuelto(cliente, loan_id):
    items = cliente.get(f"/api/loans/{loan_id}").json()["items"]
    for item in items:
        subir(cliente, loan_id, "foto_dev_frente", item["id"])
        subir(cliente, loan_id, "foto_dev_atras", item["id"])
    cliente.post(
        f"/api/loans/{loan_id}/devolucion",
        json={"items": [{"loan_item_id": i["id"]} for i in items]},
    )
    return [i["id"] for i in items]


# ── Permisos ────────────────────────────────────────────────────────────────


def test_un_colaborador_no_autoriza_entregas(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _prestado(cliente)
    resp = cliente.post(f"/api/loans/{loan_id}/autorizar-entrega")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_un_admin_tampoco_autoriza(inventario, ana, db):
    """`admin` no tiene `equipos_aprobacion:*`: aprobar equipo es del paquete
    aditivo, no del rol base."""
    loan_id = _prestado(logueado("ana.ruiz"))
    usuario_con(db, username="adm", role="admin")
    assert logueado("adm").post(f"/api/loans/{loan_id}/autorizar-entrega").status_code == 403


def test_la_aprobadora_autoriza(inventario, ana, melisa):
    loan_id = _prestado(logueado("ana.ruiz"))
    cuerpo = logueado("melisa").post(f"/api/loans/{loan_id}/autorizar-entrega").json()

    assert cuerpo["entrega_autorizada"] is True
    assert cuerpo["entrega_autorizada_por"]["user_id"] == melisa.id
    assert cuerpo["entrega_autorizada_por"]["nombre"] == melisa.full_name
    assert cuerpo["fecha_autorizacion_entrega"] is not None
    # Ortogonal: no cambia el estado.
    assert cuerpo["estado"] == "prestado"


def test_autorizar_es_idempotente(inventario, ana, melisa):
    loan_id = _prestado(logueado("ana.ruiz"))
    cliente = logueado("melisa")
    primera = cliente.post(f"/api/loans/{loan_id}/autorizar-entrega").json()
    segunda = cliente.post(f"/api/loans/{loan_id}/autorizar-entrega").json()

    assert segunda["fecha_autorizacion_entrega"] == primera["fecha_autorizacion_entrega"]
    eventos = [e["tipo"] for e in segunda["eventos"]]
    assert eventos.count("entrega_autorizada") == 1


def test_no_se_autoriza_un_borrador(inventario, ana, melisa):
    """Todavia no hay folio ni responsiva que autorizar."""
    loan_id = logueado("ana.ruiz").post("/api/loans/", json={}).json()["id"]
    resp = logueado("melisa").post(f"/api/loans/{loan_id}/autorizar-entrega")
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"


# ── Confirmar devolucion ────────────────────────────────────────────────────


def test_todo_ok_con_autorizacion_completa(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    cliente_mel = logueado("melisa")
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")
    cuerpo = cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    ).json()

    assert cuerpo["estado"] == "completado"
    assert cuerpo["confirmada_por"]["user_id"] == melisa.id
    assert cuerpo["items"][0]["devuelto_at"] is not None
    assert cuerpo["items"][0]["decision"] == "ok"


def test_todo_ok_sin_autorizacion_no_completa_y_no_escribe_nada(inventario, ana, melisa):
    """El caso delicado. Se rechaza ANTES de mutar: guardar las decisiones y
    quedarse en pendiente_confirmacion seria un exito falso."""
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    resp = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    )
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"
    assert "no esta autorizada" in resp.json()["detail"]

    ficha = logueado("melisa").get(f"/api/loans/{loan_id}").json()
    assert ficha["estado"] == "pendiente_confirmacion"
    assert ficha["items"][0]["decision"] is None
    assert ficha["items"][0]["devuelto_at"] is None
    assert ficha["confirmada_por"] is None


def test_con_incidencia_si_pasa_a_incompleto_sin_autorizacion(inventario, ana, melisa):
    """La guarda se evalua contra el DESTINO. Si tambien bloqueara aqui, un
    prestamo con incidencia y sin autorizar no tendria a donde ir."""
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    cuerpo = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={
            "decisiones": [
                {"loan_item_id": items[0], "decision": "danado", "nota": "Lente rayado"}
            ]
        },
    ).json()
    assert cuerpo["estado"] == "incompleto"


def test_la_nota_es_obligatoria_si_la_decision_no_es_ok(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    resp = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "faltante"}]},
    )
    assert resp.status_code == 422
    assert resp.json()["codigo"] == "VALOR_INVALIDO"


def test_una_decision_fuera_del_vocabulario_es_422(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    resp = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "regular"}]},
    )
    assert resp.status_code == 422


def test_faltan_decisiones_de_algun_equipo(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana, equipment_ids=(1, 2))
    items = _devuelto(cliente_ana, loan_id)

    resp = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    )
    assert resp.status_code == 409
    assert "Faltan las decisiones" in resp.json()["detail"]


def test_un_renglon_repetido_es_422(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    resp = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={
            "decisiones": [
                {"loan_item_id": items[0], "decision": "ok"},
                {"loan_item_id": items[0], "decision": "ok"},
            ]
        },
    )
    assert resp.status_code == 422


def test_un_renglon_ajeno_es_404(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana, equipment_ids=(1,))
    otro = _prestado(cliente_ana, equipment_ids=(2,))
    _devuelto(cliente_ana, loan_id)
    ajeno = logueado("melisa").get(f"/api/loans/{otro}").json()["items"][0]["id"]

    resp = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": ajeno, "decision": "ok"}]},
    )
    assert resp.status_code == 404


def test_el_equipo_danado_pasa_a_revision_y_deja_de_ofrecerse(inventario, ana, melisa, db):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "danado", "nota": "Lente rayado"}]},
    )

    db.expire_all()
    assert db.get(Equipment, 1).estado_operativo == EstadoOperativo.REVISION.value
    fila = next(i for i in cliente_ana.get("/api/equipment/").json()["items"] if i["id"] == 1)
    assert fila["disponible"] is False


def test_el_equipo_ok_vuelve_a_estar_disponible(inventario, ana, melisa):
    """Se escribe `devuelto_at` en todos los renglones: el prestamo cerro. Lo que
    retiene al danado es `estado_operativo='revision'`, no el renglon abierto."""
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)
    cliente_mel = logueado("melisa")
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")
    cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    )

    fila = next(i for i in cliente_ana.get("/api/equipment/").json()["items"] if i["id"] == 1)
    assert fila["disponible"] is True


def test_el_equipo_faltante_tambien_cierra_su_renglon(inventario, ana, melisa, db):
    """Si el renglon quedara abierto, cerrar la incidencia devolveria el equipo a
    'activo' mientras el indice unico lo sigue bloqueando: la pantalla diria
    disponible y el POST daria 409."""
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)

    cuerpo = logueado("melisa").post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "faltante", "nota": "No aparecio"}]},
    ).json()
    assert cuerpo["items"][0]["devuelto_at"] is not None


def test_confirmar_la_devolucion_dos_veces_es_409(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)
    cliente_mel = logueado("melisa")
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")
    cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    )

    resp = cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    )
    assert resp.status_code == 409


# ── Cerrar incidencia ───────────────────────────────────────────────────────


def _incompleto(cliente_ana, cliente_mel, equipment_id=1):
    loan_id = _prestado(cliente_ana, equipment_ids=(equipment_id,))
    items = _devuelto(cliente_ana, loan_id)
    cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "danado", "nota": "Rayado"}]},
    )
    return loan_id


def test_cerrar_incidencia_devuelve_el_equipo_a_servicio(inventario, ana, melisa, db):
    """En la maqueta `incompleto` era terminal: un equipo danado quedaba en
    revision para siempre (§10.12)."""
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _incompleto(cliente_ana, cliente_mel)
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")

    cuerpo = cliente_mel.post(
        f"/api/loans/{loan_id}/cerrar-incidencia", json={"nota": "Reparado en taller."}
    ).json()

    assert cuerpo["estado"] == "completado"
    db.expire_all()
    assert db.get(Equipment, 1).estado_operativo == EstadoOperativo.ACTIVO.value


def test_cerrar_incidencia_sin_autorizacion_es_409(inventario, ana, melisa):
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _incompleto(cliente_ana, cliente_mel)

    resp = cliente_mel.post(f"/api/loans/{loan_id}/cerrar-incidencia", json={"nota": "Reparado."})
    assert resp.status_code == 409
    assert "no esta autorizada" in resp.json()["detail"]


def test_se_puede_autorizar_un_prestamo_ya_incompleto(inventario, ana, melisa):
    """Sin esto, un prestamo que llego a incompleto sin autorizacion no se
    podria cerrar nunca."""
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _incompleto(cliente_ana, cliente_mel)

    cuerpo = cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega").json()
    assert cuerpo["entrega_autorizada"] is True
    assert cuerpo["estado"] == "incompleto"


def test_la_nota_de_cierre_es_obligatoria(inventario, ana, melisa):
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _incompleto(cliente_ana, cliente_mel)
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")

    assert cliente_mel.post(f"/api/loans/{loan_id}/cerrar-incidencia", json={"nota": ""}).status_code == 422
    assert cliente_mel.post(f"/api/loans/{loan_id}/cerrar-incidencia", json={}).status_code == 422


def test_no_se_cierra_incidencia_de_un_prestamo_completado(inventario, ana, melisa):
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _incompleto(cliente_ana, cliente_mel)
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")
    cliente_mel.post(f"/api/loans/{loan_id}/cerrar-incidencia", json={"nota": "Listo."})

    resp = cliente_mel.post(f"/api/loans/{loan_id}/cerrar-incidencia", json={"nota": "Otra vez."})
    assert resp.status_code == 409


def test_cerrar_incidencia_solo_toca_los_equipos_de_ese_prestamo(inventario, ana, melisa, db):
    """Hacerlo por equipo podria sacar de revision uno que quedo asi por otro
    prestamo o por una auditoria de condicion."""
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _incompleto(cliente_ana, cliente_mel, equipment_id=1)

    # Otro equipo en revision por una causa ajena.
    db.get(Equipment, 4).estado_operativo = EstadoOperativo.REVISION.value
    db.commit()

    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")
    cliente_mel.post(f"/api/loans/{loan_id}/cerrar-incidencia", json={"nota": "Reparado."})

    db.expire_all()
    assert db.get(Equipment, 1).estado_operativo == EstadoOperativo.ACTIVO.value
    assert db.get(Equipment, 4).estado_operativo == EstadoOperativo.REVISION.value


# ── Bitacora ────────────────────────────────────────────────────────────────


def test_la_bitacora_registra_el_ciclo_completo(inventario, ana, melisa):
    cliente_ana, cliente_mel = logueado("ana.ruiz"), logueado("melisa")
    loan_id = _prestado(cliente_ana)
    items = _devuelto(cliente_ana, loan_id)
    cliente_mel.post(f"/api/loans/{loan_id}/autorizar-entrega")
    cuerpo = cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": items[0], "decision": "ok"}]},
    ).json()

    tipos = [e["tipo"] for e in cuerpo["eventos"]]
    assert tipos == [
        "creado",
        "item_agregado",
        "confirmado",
        "responsiva_generada",
        "devolucion_registrada",
        "entrega_autorizada",
        "devolucion_confirmada",
    ]
    # El actor se copia por nombre: la bitacora sigue legible si el usuario se
    # da de baja.
    assert cuerpo["eventos"][-1]["actor"] == melisa.full_name


def test_quien_autoriza_sale_de_la_sesion_no_del_cuerpo(inventario, ana, melisa, db):
    """En la maqueta cualquiera elegia "Melisa" en un `<select>` y aprobaba en su
    nombre (§10.4, CRITICO)."""
    otra = usuario_con(db, username="otra.aprobadora", aditivos=("APROBADOR_EQUIPO",))
    loan_id = _prestado(logueado("ana.ruiz"))

    cuerpo = logueado("otra.aprobadora").post(f"/api/loans/{loan_id}/autorizar-entrega").json()
    assert cuerpo["entrega_autorizada_por"]["user_id"] == otra.id
    assert cuerpo["entrega_autorizada_por"]["user_id"] != melisa.id
