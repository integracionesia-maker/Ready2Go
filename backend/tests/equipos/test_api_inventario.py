"""API de inventario (contrato §2): listado, ficha, alta, edicion, auditoria,
baja y dashboard."""

from datetime import date

import pytest

import seed_equipos
from app.models_equipos import EquipmentAudit, EstadoOperativo, EstadoPrestamo

from .conftest import agregar_item, crear_prestamo, logueado, usuario_con


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


# ── Permisos ────────────────────────────────────────────────────────────────


def test_ver_inventario_lo_puede_cualquiera_de_marketing(inventario, db):
    usuario_con(db, username="emily")
    resp = logueado("emily").get("/api/equipment/")
    assert resp.status_code == 200
    assert resp.json()["total"] == 8


def test_un_creador_no_ve_el_inventario(inventario, db, creador_user):
    from ..conftest import PASSWORD_CREADOR

    resp = logueado("creador.a", PASSWORD_CREADOR).get("/api/equipment/")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_colaborador_no_puede_crear_equipos(inventario, db):
    usuario_con(db, username="emily")
    resp = logueado("emily").post("/api/equipment/", json={"nombre": "Camara nueva"})
    assert resp.status_code == 403


def test_el_custodio_si_puede_crear_editar_auditar_y_dar_de_baja(inventario, db):
    """El aditivo CUSTODIO_EQUIPO abre exactamente esas cuatro acciones."""
    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    cliente = logueado("betza")

    alta = cliente.post("/api/equipment/", json={"nombre": "Tripie Manfrotto"})
    assert alta.status_code == 201, alta.text
    nuevo = alta.json()["id"]

    assert cliente.put(f"/api/equipment/{nuevo}", json={"marca": "Manfrotto"}).status_code == 200
    assert (
        cliente.post(
            f"/api/equipment/{nuevo}/auditoria", json={"condicion": "bueno"}
        ).status_code
        == 201
    )
    assert cliente.post(f"/api/equipment/{nuevo}/baja", json={}).status_code == 200


def test_el_aprobador_no_administra_inventario(inventario, db):
    """APROBADOR_EQUIPO abre aprobacion, no inventario. Es el creep de privilegio
    que el plan §10.7 quiere evitar."""
    usuario_con(db, username="mel", aditivos=("APROBADOR_EQUIPO",))
    assert logueado("mel").post("/api/equipment/", json={"nombre": "X"}).status_code == 403


# ── Listado ─────────────────────────────────────────────────────────────────


def test_la_fila_del_listado_tiene_la_forma_del_fixture(inventario, db, fixture_equipos):
    """Campo por campo contra `docs/contratos/fixtures/equipos.json`, para los
    equipos libres. El equipo 1 lo cubre la prueba del tenedor."""
    usuario_con(db, username="emily")
    cuerpo = logueado("emily").get("/api/equipment/").json()

    assert set(cuerpo) == {"items", "total"}
    assert cuerpo["total"] == 8

    obtenidos = {item["id"]: item for item in cuerpo["items"]}
    for esperado in fixture_equipos["items"]:
        if esperado["id"] == 1:
            continue  # tiene prestamo abierto en el fixture; prueba aparte
        obtenido = obtenidos[esperado["id"]]
        assert set(obtenido) == set(esperado)
        for campo, valor in esperado.items():
            assert obtenido[campo] == valor, f"equipo {esperado['id']}, campo {campo}"


def test_el_tenedor_actual_viene_en_la_fila_no_en_otro_request(inventario, db):
    """Contrato §2: la pantalla de inventario lo pinta directo."""
    from app.models_equipos import Equipment

    ana = usuario_con(db, username="ana.ruiz")
    prestamo = crear_prestamo(db, responsable=ana, fecha_regreso_esperada=date(2026, 7, 30))
    agregar_item(db, prestamo, db.get(Equipment, 1))
    usuario_con(db, username="emily")

    fila = next(
        item
        for item in logueado("emily").get("/api/equipment/").json()["items"]
        if item["id"] == 1
    )
    assert fila["disponible"] is False
    assert fila["tenedor_actual"] == {"nombre": ana.full_name, "user_id": ana.id}
    assert fila["fecha_regreso_esperada"] == "2026-07-30"


def test_filtro_por_disponible(inventario, db):
    from app.models_equipos import Equipment

    prestamo = crear_prestamo(db)
    agregar_item(db, prestamo, db.get(Equipment, 1))
    usuario_con(db, username="emily")
    cliente = logueado("emily")

    libres = cliente.get("/api/equipment/", params={"disponible": True}).json()
    ocupados = cliente.get("/api/equipment/", params={"disponible": False}).json()

    assert libres["total"] == 7
    assert ocupados["total"] == 1
    assert ocupados["items"][0]["id"] == 1


def test_filtro_por_condicion_usa_la_ultima_auditoria(inventario, db):
    usuario_con(db, username="emily")
    resp = logueado("emily").get("/api/equipment/", params={"condicion": "atencion"}).json()
    assert [item["id"] for item in resp["items"]] == [2]


def test_la_condicion_refleja_la_auditoria_mas_reciente(inventario, db):
    """Si el filtro mirara cualquier auditoria en vez de la ultima, un equipo
    reparado seguiria apareciendo como danado para siempre."""
    db.add(
        EquipmentAudit(
            equipment_id=2, condicion="bueno", comentario="Cable reemplazado", fecha=date(2026, 7, 20)
        )
    )
    db.commit()
    usuario_con(db, username="emily")
    cliente = logueado("emily")

    assert cliente.get("/api/equipment/", params={"condicion": "atencion"}).json()["total"] == 0
    fila = next(i for i in cliente.get("/api/equipment/").json()["items"] if i["id"] == 2)
    assert fila["condicion"] == "bueno"
    assert fila["comentario_auditoria"] == "Cable reemplazado"


def test_filtro_por_categoria(inventario, db):
    usuario_con(db, username="emily")
    resp = logueado("emily").get(
        "/api/equipment/", params={"categoria": "Estabilizadores"}
    ).json()
    assert [item["id"] for item in resp["items"]] == [5, 6]


def test_busqueda_libre_cubre_varios_campos(inventario, db):
    usuario_con(db, username="emily")
    cliente = logueado("emily")

    assert cliente.get("/api/equipment/", params={"q": "Osmo"}).json()["total"] == 2
    assert cliente.get("/api/equipment/", params={"q": "OSMO-1"}).json()["total"] == 1
    assert cliente.get("/api/equipment/", params={"q": "iPhone 17 Pro Max"}).json()["total"] == 1
    assert cliente.get("/api/equipment/", params={"q": "no-existe-nada"}).json()["total"] == 0


def test_paginacion(inventario, db):
    usuario_con(db, username="emily")
    cliente = logueado("emily")

    pagina = cliente.get("/api/equipment/", params={"limit": 3, "offset": 0}).json()
    assert len(pagina["items"]) == 3
    assert pagina["total"] == 8

    segunda = cliente.get("/api/equipment/", params={"limit": 3, "offset": 3}).json()
    assert [i["id"] for i in segunda["items"]] == [4, 5, 6]


def test_limite_maximo_es_200(inventario, db):
    usuario_con(db, username="emily")
    assert logueado("emily").get("/api/equipment/", params={"limit": 500}).status_code == 422


# ── Ficha ───────────────────────────────────────────────────────────────────


def test_la_ficha_trae_auditorias_e_historial(inventario, db):
    from app.models_equipos import Equipment

    ana = usuario_con(db, username="ana.ruiz")
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0001")
    agregar_item(db, prestamo, db.get(Equipment, 1))
    usuario_con(db, username="emily")

    ficha = logueado("emily").get("/api/equipment/1").json()
    assert ficha["id"] == 1
    assert len(ficha["auditorias"]) == 1
    assert ficha["auditorias"][0]["condicion"] == "bueno"
    assert len(ficha["historial"]) == 1
    assert ficha["historial"][0]["folio"] == "CE-0001"
    assert ficha["historial"][0]["responsable"] == ana.full_name


def test_ficha_de_equipo_inexistente_es_404(inventario, db):
    usuario_con(db, username="emily")
    resp = logueado("emily").get("/api/equipment/9999")
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


# ── Auditoria de condicion ──────────────────────────────────────────────────


def test_la_auditoria_agrega_al_historial_sin_pisar_la_anterior(inventario, db):
    """La maqueta guardaba solo la ultima revision: no habia forma de saber si un
    rayon venia de antes del prestamo."""
    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    usuario_con(db, username="emily")  # colaborador_mkt con permiso `ver`
    cliente = logueado("betza")

    resp = cliente.post(
        "/api/equipment/2/auditoria",
        json={
            "condicion": "bueno",
            "estado_fisico": "usado",
            "comentario": "Cable tipo C reemplazado.",
            "espacio_disponible": "",
        },
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()

    # El POST solo devuelve EquipmentItem (sin auditorias completas — hallazgo #3).
    assert item["condicion"] == "bueno"

    # La ficha completa (con auditorias) se obtiene via GET, que si requiere
    # el permiso `equipos_inventario:ver` (emily = colaborador_mkt, que lo tiene).
    ficha = logueado("emily").get("/api/equipment/2").json()
    assert len(ficha["auditorias"]) == 2
    # La vieja sigue ahi, con su comentario original.
    assert any("cable tipo C presenta falla" in a["comentario"] for a in ficha["auditorias"])


def test_la_auditoria_registra_quien_la_hizo(inventario, db):
    betza = usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    usuario_con(db, username="emily")  # colaborador_mkt con permiso `ver`
    resp = (
        logueado("betza")
        .post("/api/equipment/4/auditoria", json={"condicion": "atencion"})
    )
    assert resp.status_code == 201, resp.text

    # El POST solo devuelve EquipmentItem (sin auditorias completas — hallazgo #3).
    # La ficha completa se obtiene via GET con permiso `ver` (emily = colaborador_mkt).
    ficha = logueado("emily").get("/api/equipment/4").json()
    assert ficha["auditorias"][0]["actor_user_id"] == betza.id
    assert ficha["auditorias"][0]["actor_nombre"] == betza.full_name


def test_la_auditoria_actualiza_el_espacio_vigente_del_equipo(inventario, db):
    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    ficha = (
        logueado("betza")
        .post(
            "/api/equipment/1/auditoria",
            json={"condicion": "bueno", "espacio_disponible": "12.00 GB de 256 GB"},
        )
        .json()
    )
    assert ficha["espacio_disponible"] == "12.00 GB de 256 GB"


def test_condicion_fuera_del_vocabulario_es_422(inventario, db):
    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    resp = logueado("betza").post("/api/equipment/1/auditoria", json={"condicion": "regular"})
    assert resp.status_code == 422
    assert set(resp.json()) == {"detail", "codigo"}


def test_la_fecha_de_auditoria_default_es_hoy_en_cdmx(inventario, db):
    from freezegun import freeze_time

    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))

    # La sesion se abre DENTRO del reloj congelado: si se abriera fuera, el
    # token quedaria vencido respecto del instante congelado y la prueba mediria
    # un 401 en vez de la fecha.
    # 2026-07-29 03:00 UTC = 2026-07-28 21:00 CDMX. Con UTC quedaria el 29.
    with freeze_time("2026-07-29 03:00:00"):
        cliente = logueado("betza")
        resp = cliente.post("/api/equipment/5/auditoria", json={"condicion": "bueno"})

    assert resp.status_code == 201, resp.text
    assert resp.json()["fecha_auditoria"] == "2026-07-28"


# ── Baja ────────────────────────────────────────────────────────────────────


def test_baja_de_equipo_con_prestamo_abierto_es_409(inventario, db):
    from app.models_equipos import Equipment

    prestamo = crear_prestamo(db)
    agregar_item(db, prestamo, db.get(Equipment, 1))
    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))

    resp = logueado("betza").post("/api/equipment/1/baja", json={})
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "EQUIPO_OCUPADO"


def test_baja_saca_el_equipo_del_inventario(inventario, db):
    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    cliente = logueado("betza")

    baja = cliente.post("/api/equipment/6/baja", json={"motivo": "Robado en evento"})
    assert baja.status_code == 200
    assert baja.json()["estado_operativo"] == EstadoOperativo.BAJA.value
    assert baja.json()["disponible"] is False

    assert cliente.get("/api/equipment/").json()["total"] == 7
    assert cliente.get("/api/equipment/6").status_code == 404


def test_el_historial_del_equipo_dado_de_baja_se_conserva(inventario, db):
    """Borrado logico: el registro y sus auditorias quedan porque la responsiva
    ya firmada los referencia."""
    from app.models_equipos import Equipment

    usuario_con(db, username="betza", aditivos=("CUSTODIO_EQUIPO",))
    logueado("betza").post("/api/equipment/6/baja", json={"motivo": "Robado"})

    equipo = db.get(Equipment, 6)
    assert equipo is not None
    assert equipo.is_deleted is True
    assert db.query(EquipmentAudit).filter(EquipmentAudit.equipment_id == 6).count() == 2


# ── Dashboard ───────────────────────────────────────────────────────────────


def test_el_dashboard_no_lo_traga_la_ruta_por_id(inventario, db):
    """Si `/dashboard` se declarara despues de `/{id}` sin `:int`, el enrutador
    lo tomaria como un id y este endpoint desapareceria en silencio."""
    usuario_con(db, username="emily")
    resp = logueado("emily").get("/api/equipment/dashboard")
    assert resp.status_code == 200
    assert "por_estado" in resp.json()


def test_el_dashboard_existe_como_ruta_propia_en_el_esquema():
    """Segunda defensa del mismo error: si `/{id}` se lo tragara, no apareceria
    como ruta en el OpenAPI."""
    from app.main import app

    rutas = set(app.openapi()["paths"])
    assert "/api/equipment/dashboard" in rutas
    assert "/api/equipment/{equipment_id}" in rutas


def test_dashboard_cuenta_lo_que_dice_el_contrato(inventario, db):
    from app.models_equipos import Equipment

    ana = usuario_con(db, username="ana.ruiz")

    prestado = crear_prestamo(db, responsable=ana, folio="CE-0001", fecha_regreso_esperada=date(2026, 7, 30))
    agregar_item(db, prestado, db.get(Equipment, 1))

    atrasado = crear_prestamo(db, responsable=ana, folio="CE-0002", fecha_regreso_esperada=date(2026, 7, 25))
    agregar_item(db, atrasado, db.get(Equipment, 2))

    devuelto = crear_prestamo(
        db, responsable=ana, folio="CE-0003", estado=EstadoPrestamo.PENDIENTE_CONFIRMACION.value
    )
    agregar_item(db, devuelto, db.get(Equipment, 3))

    crear_prestamo(db, responsable=ana, folio="CE-0004", estado=EstadoPrestamo.COMPLETADO.value)

    usuario_con(db, username="emily")
    from freezegun import freeze_time

    with freeze_time("2026-07-28 18:00:00"):
        cuerpo = logueado("emily").get("/api/equipment/dashboard").json()

    assert cuerpo["prestados"] == 2
    assert cuerpo["atrasados"] == 1
    assert cuerpo["pendientes_confirmacion"] == 1
    assert cuerpo["disponibles"] == 5  # 8 menos los 3 con renglon abierto
    assert cuerpo["por_estado"]["prestado"] == 2
    assert cuerpo["por_estado"]["pendiente_confirmacion"] == 1
    assert cuerpo["por_estado"]["completado"] == 1


def test_por_estado_trae_siempre_las_seis_llaves(inventario, db):
    """Devolver solo las que tienen datos hace que una grafica cambie de forma
    sola cuando el ultimo prestamo de un estado se cierra."""
    usuario_con(db, username="emily")
    por_estado = logueado("emily").get("/api/equipment/dashboard").json()["por_estado"]
    assert set(por_estado) == {
        "borrador",
        "prestado",
        "pendiente_confirmacion",
        "completado",
        "incompleto",
        "cancelado",
    }
    assert all(valor == 0 for valor in por_estado.values())


def test_requiere_atencion_da_un_renglon_por_prestamo_con_el_motivo_mas_grave(inventario, db):
    from app.models_equipos import Equipment
    from freezegun import freeze_time

    ana = usuario_con(db, username="ana.ruiz")
    prestamo = crear_prestamo(
        db, responsable=ana, folio="CE-0007", fecha_regreso_esperada=date(2026, 7, 25)
    )
    agregar_item(db, prestamo, db.get(Equipment, 5))
    usuario_con(db, username="emily")

    with freeze_time("2026-07-28 18:00:00"):
        atencion = logueado("emily").get("/api/equipment/dashboard").json()["requiere_atencion"]

    assert len(atencion) == 1
    fila = atencion[0]
    assert fila["loan_id"] == prestamo.id
    assert fila["folio"] == "CE-0007"
    assert fila["motivo"] == "atrasado 3 dias"
    assert fila["responsable"] == ana.full_name
    assert fila["equipos"] == ["(1) Osmo DJI 7"]


def test_requiere_atencion_marca_las_entregas_sin_autorizar(inventario, db):
    from app.models_equipos import Equipment

    ana = usuario_con(db, username="ana.ruiz")
    prestamo = crear_prestamo(
        db, responsable=ana, folio="CE-0008", fecha_regreso_esperada=date(2026, 12, 31)
    )
    agregar_item(db, prestamo, db.get(Equipment, 5))
    usuario_con(db, username="emily")

    atencion = logueado("emily").get("/api/equipment/dashboard").json()["requiere_atencion"]
    assert [f["motivo"] for f in atencion] == ["entrega sin autorizar"]


def test_un_prestamo_borrado_no_cuenta_en_el_dashboard(inventario, db):
    ana = usuario_con(db, username="ana.ruiz")
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0009")
    prestamo.is_deleted = True
    db.commit()

    usuario_con(db, username="emily")
    cuerpo = logueado("emily").get("/api/equipment/dashboard").json()
    assert cuerpo["prestados"] == 0
    assert cuerpo["requiere_atencion"] == []
