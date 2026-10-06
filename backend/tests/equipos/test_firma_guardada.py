"""Firma predeterminada del perfil (docs/equipos/firma-guardada.md): guardarla,
leerla, borrarla y usarla para firmar un prestamo con un solo boton.
"""

from pathlib import Path

import pytest

import seed_equipos
from app.models import UserSignature
from app.models_equipos import MediaAsset

from .conftest import logueado, png_bytes, subir, usuario_con
from .test_api_prestamos import _borrador_listo


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
    return usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO", "TITULAR_FIRMA_EQUIPO"))


def _guardar(cliente, contenido=None):
    return cliente.put(
        "/api/auth/me/signature",
        files={"file": ("firma.png", contenido if contenido is not None else png_bytes(), "image/png")},
    )


def _firmar_con_guardada(cliente, loan_id, kind):
    return cliente.post(f"/api/loans/{loan_id}/media", data={"kind": kind, "usar_firma_guardada": "true"})


def _prestamo_de_ana(cliente_ana):
    loan_id = _borrador_listo(cliente_ana)
    assert cliente_ana.post(f"/api/loans/{loan_id}/confirmar").status_code == 200
    return loan_id


# ── Perfil: guardar / leer / borrar ─────────────────────────────────────────


def test_sin_firma_guardada_me_lo_dice_y_el_get_es_404(ana):
    cliente = logueado("ana.ruiz")
    assert cliente.get("/api/auth/me").json()["tiene_firma_guardada"] is False
    assert cliente.get("/api/auth/me/signature").status_code == 404


def test_guardar_leer_y_borrar_la_firma_del_perfil(ana):
    cliente = logueado("ana.ruiz")
    original = png_bytes(60, 30)
    assert _guardar(cliente, original).status_code == 200

    assert cliente.get("/api/auth/me").json()["tiene_firma_guardada"] is True
    resp = cliente.get("/api/auth/me/signature")
    assert resp.status_code == 200
    assert resp.content == original
    assert resp.headers["content-type"] == "image/png"
    assert "private" in resp.headers["cache-control"]

    assert cliente.delete("/api/auth/me/signature").status_code == 200
    assert cliente.get("/api/auth/me").json()["tiene_firma_guardada"] is False
    assert cliente.get("/api/auth/me/signature").status_code == 404
    # Ya no hay nada que borrar.
    assert cliente.delete("/api/auth/me/signature").status_code == 404


def test_reemplazar_la_firma_borra_el_archivo_anterior(ana, db):
    cliente = logueado("ana.ruiz")
    _guardar(cliente, png_bytes(40, 30, (10, 10, 10)))
    ruta_vieja = Path(db.query(UserSignature).one().file_path)
    assert ruta_vieja.exists()

    _guardar(cliente, png_bytes(50, 30, (20, 20, 20)))
    db.expire_all()
    fila = db.query(UserSignature).one()  # sigue siendo UNA por usuario
    assert Path(fila.file_path).exists()
    assert not ruta_vieja.exists()


def test_un_archivo_invalido_no_pisa_la_firma_que_ya_tenia(ana):
    cliente = logueado("ana.ruiz")
    original = png_bytes()
    _guardar(cliente, original)

    resp = _guardar(cliente, b"esto no es una imagen")
    assert resp.status_code == 422
    assert cliente.get("/api/auth/me/signature").content == original


def test_una_firma_de_mas_de_250kb_se_rechaza(ana):
    resp = _guardar(logueado("ana.ruiz"), b"\x89PNG\r\n\x1a\n" + b"0" * (251 * 1024))
    assert resp.status_code == 413


def test_cada_quien_ve_solo_su_propia_firma(ana, melisa):
    _guardar(logueado("melisa"))
    assert logueado("ana.ruiz").get("/api/auth/me/signature").status_code == 404


def test_las_rutas_exigen_sesion(client):
    assert client.get("/api/auth/me/signature").status_code == 401
    assert client.delete("/api/auth/me/signature").status_code == 401


# ── Firmar un prestamo con la firma guardada ────────────────────────────────


def test_el_beneficiario_firma_con_su_firma_guardada(inventario, ana, db):
    cliente_ana = logueado("ana.ruiz")
    _guardar(cliente_ana)
    loan_id = _prestamo_de_ana(cliente_ana)

    resp = _firmar_con_guardada(cliente_ana, loan_id, "firma_responsable")
    assert resp.status_code == 201, resp.text

    cuerpo = cliente_ana.get(f"/api/loans/{loan_id}").json()
    assert cuerpo["firmas"]["firma_responsable"] == resp.json()["id"]
    # Misma mecanica que una firma dibujada: version nueva de la responsiva y evento.
    assert cuerpo["responsiva"]["version"] == 2
    assert [e["tipo"] for e in cuerpo["eventos"]].count("firma_completada") == 1

    fila = db.get(MediaAsset, resp.json()["id"])
    assert fila.created_by_user_id == ana.id
    assert fila.sha256 == db.query(UserSignature).one().sha256


def test_el_titular_firma_como_aprobador_con_su_firma_guardada(inventario, ana, melisa):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestamo_de_ana(cliente_ana)
    cliente_melisa = logueado("melisa")
    _guardar(cliente_melisa)

    resp = _firmar_con_guardada(cliente_melisa, loan_id, "firma_entrega")
    assert resp.status_code == 201, resp.text
    assert cliente_ana.get(f"/api/loans/{loan_id}").json()["firmas"]["firma_entrega"] == resp.json()["id"]


def test_tener_firma_guardada_no_abre_la_firma_del_aprobador(inventario, ana, melisa, db):
    """`firma_entrega` sigue siendo identidad del titular: ni otro
    APROBADOR_EQUIPO ni quien llena el formulario, aunque tengan firma guardada."""
    otra = usuario_con(db, username="otra.aprobadora", aditivos=("APROBADOR_EQUIPO",))
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestamo_de_ana(cliente_ana)

    for quien in ("ana.ruiz", "otra.aprobadora"):
        cliente = logueado(quien)
        _guardar(cliente)
        resp = _firmar_con_guardada(cliente, loan_id, "firma_entrega")
        assert resp.status_code == 403, quien
        assert resp.json()["codigo"] == "SIN_PERMISO"
    assert otra  # el usuario existe: el 403 es por no ser titular
    assert db.query(MediaAsset).filter(MediaAsset.kind == "firma_entrega").count() == 0


def test_la_firma_guardada_no_se_estampa_por_otro_beneficiario(inventario, ana, db):
    """Quien no es el beneficiario puede dibujar su firma (como hoy), pero no
    estampar la suya guardada en la parte del beneficiario."""
    otra = usuario_con(db, username="otra.aprobadora", aditivos=("APROBADOR_EQUIPO",))
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestamo_de_ana(cliente_ana)

    cliente_otra = logueado("otra.aprobadora")
    _guardar(cliente_otra)
    resp = _firmar_con_guardada(cliente_otra, loan_id, "firma_responsable")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"
    assert db.query(MediaAsset).filter(MediaAsset.kind == "firma_responsable").count() == 0

    # Dibujada si puede, igual que antes de esta funcion.
    assert subir(cliente_otra, loan_id, "firma_responsable").status_code == 201
    assert otra


def test_firmar_con_guardada_sin_tenerla_es_404(inventario, ana):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestamo_de_ana(cliente_ana)
    resp = _firmar_con_guardada(cliente_ana, loan_id, "firma_responsable")
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_la_firma_del_prestamo_es_una_copia_independiente_del_perfil(inventario, ana, db):
    """Cambiar o borrar la firma del perfil despues NO toca la evidencia de un
    prestamo ya firmado."""
    cliente_ana = logueado("ana.ruiz")
    _guardar(cliente_ana)
    loan_id = _prestamo_de_ana(cliente_ana)
    media_id = _firmar_con_guardada(cliente_ana, loan_id, "firma_responsable").json()["id"]

    ruta_perfil = Path(db.query(UserSignature).one().file_path)
    ruta_prestamo = Path(db.get(MediaAsset, media_id).file_path)
    assert ruta_perfil != ruta_prestamo

    cliente_ana.delete("/api/auth/me/signature")
    assert not ruta_perfil.exists()
    descarga = cliente_ana.get(f"/api/media/{media_id}")
    assert descarga.status_code == 200
    assert descarga.content


def test_no_se_puede_usar_la_firma_guardada_sobre_una_firma_ya_capturada(inventario, ana):
    cliente_ana = logueado("ana.ruiz")
    _guardar(cliente_ana)
    loan_id = _prestamo_de_ana(cliente_ana)
    assert _firmar_con_guardada(cliente_ana, loan_id, "firma_responsable").status_code == 201

    resp = _firmar_con_guardada(cliente_ana, loan_id, "firma_responsable")
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"


def test_no_se_firma_con_guardada_un_prestamo_en_borrador(inventario, ana):
    cliente_ana = logueado("ana.ruiz")
    _guardar(cliente_ana)
    loan_id = _borrador_listo(cliente_ana)
    resp = _firmar_con_guardada(cliente_ana, loan_id, "firma_responsable")
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"


def test_combinaciones_invalidas_de_parametros(inventario, ana):
    cliente_ana = logueado("ana.ruiz")
    _guardar(cliente_ana)
    loan_id = _prestamo_de_ana(cliente_ana)
    url = f"/api/loans/{loan_id}/media"

    # Archivo Y firma guardada a la vez.
    resp = cliente_ana.post(
        url,
        data={"kind": "firma_responsable", "usar_firma_guardada": "true"},
        files={"file": ("f.png", png_bytes(), "image/png")},
    )
    assert resp.status_code == 422
    # Ni archivo ni firma guardada.
    assert cliente_ana.post(url, data={"kind": "firma_responsable"}).status_code == 422
    # Firma guardada sobre una foto.
    resp = cliente_ana.post(url, data={"kind": "foto_entrega_frente", "usar_firma_guardada": "true"})
    assert resp.status_code == 422
    # Guardar como predeterminada algo que no es firma.
    resp = cliente_ana.post(
        url,
        data={"kind": "foto_entrega_frente", "loan_item_id": "1", "guardar_como_predeterminada": "true"},
        files={"file": ("f.png", png_bytes(), "image/png")},
    )
    assert resp.status_code == 422


# ── Guardar al dibujar ──────────────────────────────────────────────────────


def test_al_dibujar_se_puede_guardar_como_predeterminada(inventario, ana):
    cliente_ana = logueado("ana.ruiz")
    dibujada = png_bytes(70, 35, (5, 5, 5))
    loan_id = _prestamo_de_ana(cliente_ana)

    resp = cliente_ana.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "firma_responsable", "guardar_como_predeterminada": "true"},
        files={"file": ("f.png", dibujada, "image/png")},
    )
    assert resp.status_code == 201, resp.text
    assert cliente_ana.get("/api/auth/me/signature").content == dibujada


def test_dibujar_sin_marcar_la_casilla_no_guarda_nada(inventario, ana):
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestamo_de_ana(cliente_ana)
    assert subir(cliente_ana, loan_id, "firma_responsable").status_code == 201
    assert cliente_ana.get("/api/auth/me").json()["tiene_firma_guardada"] is False


def test_si_la_firma_se_rechaza_no_se_guarda_en_el_perfil(inventario, ana, melisa):
    """Ana no es la titular: su `firma_entrega` da 403 y la casilla no cuela la
    imagen en su perfil."""
    cliente_ana = logueado("ana.ruiz")
    loan_id = _prestamo_de_ana(cliente_ana)
    resp = cliente_ana.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "firma_entrega", "guardar_como_predeterminada": "true"},
        files={"file": ("f.png", png_bytes(), "image/png")},
    )
    assert resp.status_code == 403
    assert cliente_ana.get("/api/auth/me").json()["tiene_firma_guardada"] is False
