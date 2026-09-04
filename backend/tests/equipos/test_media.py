"""Media: magic bytes, limites, miniatura y autorizacion por participacion.

El criterio de cierre de S4 exige explicitamente la prueba de que un usuario no
descarga media de un prestamo ajeno (403). Es el IDOR que ya ocurrio una vez en
este repo con `tickets/file/{id}` (§10.3, CRITICO).
"""

import pytest

import seed_equipos
from app import media_manager
from app.models_equipos import MediaAsset

from .conftest import jpeg_bytes, logueado, png_bytes, subir, usuario_con


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    # Confirmar genera la responsiva, y su emisora sale de la tabla `empresa`.
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


@pytest.fixture
def borrador(inventario, db):
    """Un borrador de Ana con un equipo, listo para recibir media."""
    usuario_con(db, username="ana.ruiz")
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    ficha = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1}).json()
    return cliente, loan_id, ficha["items"][0]["id"]


@pytest.fixture
def confirmado(borrador):
    """Como `borrador`, pero ya confirmado (2 fotos + `POST /confirmar`) — las
    firmas ya NO se aceptan en `borrador` (§1b de loan_state.py), asi que
    cualquier prueba que necesite subir una firma de verdad parte de aqui."""
    cliente, loan_id, item_id = borrador
    subir(cliente, loan_id, "foto_entrega_frente", item_id)
    subir(cliente, loan_id, "foto_entrega_atras", item_id)
    cliente.post(f"/api/loans/{loan_id}/confirmar")
    return cliente, loan_id, item_id


# ── Validacion por magic bytes ──────────────────────────────────────────────


def test_detecta_png_por_los_ocho_bytes_de_firma():
    mime, ext = media_manager.detectar_tipo(png_bytes())
    assert (mime, ext) == ("image/png", ".png")


def test_detecta_jpeg_por_el_marcador_soi():
    mime, ext = media_manager.detectar_tipo(jpeg_bytes())
    assert (mime, ext) == ("image/jpeg", ".jpg")


def test_un_php_disfrazado_de_jpeg_no_pasa(borrador):
    """La cabecera Content-Type la escribe el cliente: es dato hostil. Lo unico
    que decide son los primeros bytes."""
    cliente, loan_id, item_id = borrador
    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_entrega_frente", "loan_item_id": str(item_id)},
        files={"file": ("inocente.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg")},
    )
    assert resp.status_code == 422
    assert resp.json()["codigo"] == "MEDIA_INVALIDA"
    assert resp.json()["detail"] == "El archivo no es una imagen JPEG o PNG valida."


def test_un_svg_con_script_no_pasa(borrador):
    cliente, loan_id, item_id = borrador
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_entrega_frente", "loan_item_id": str(item_id)},
        files={"file": ("firma.png", svg, "image/png")},
    )
    assert resp.status_code == 422


def test_los_dos_primeros_bytes_de_jpeg_no_bastan():
    """`FF D8` solo es demasiado laxo: deja pasar basura que empieza igual."""
    with pytest.raises(Exception):
        media_manager.detectar_tipo(b"\xff\xd8" + b"basura" * 10)


def test_un_png_truncado_en_la_firma_no_pasa():
    with pytest.raises(Exception):
        media_manager.detectar_tipo(b"\x89PNG")


def test_archivo_vacio_no_pasa(borrador):
    cliente, loan_id, item_id = borrador
    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_entrega_frente", "loan_item_id": str(item_id)},
        files={"file": ("vacio.png", b"", "image/png")},
    )
    assert resp.status_code == 422


# ── Limites de tamano ───────────────────────────────────────────────────────


def test_el_limite_depende_del_kind():
    assert media_manager.limite_de("foto_entrega_frente") == 3 * 1024 * 1024
    assert media_manager.limite_de("firma_entrega") == 250 * 1024
    assert media_manager.limite_de("firma_responsable") == 250 * 1024


def test_una_firma_de_mas_de_250kb_da_413(confirmado, monkeypatch):
    # `firma_responsable`, no `firma_entrega`: esta prueba es sobre el limite
    # de tamano (generico a cualquier firma), no sobre el permiso especial de
    # `firma_entrega` (ver test_api_prestamos.py para ese).
    cliente, loan_id, _ = confirmado
    monkeypatch.setattr(media_manager, "LIMITE_FIRMA", 100)

    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "firma_responsable"},
        files={"file": ("firma.png", png_bytes(200, 200), "image/png")},
    )
    assert resp.status_code == 413
    assert resp.json()["codigo"] == "MEDIA_MUY_GRANDE"
    assert resp.json()["detail"] == "La firma excede 250 KB."


def test_una_foto_de_mas_de_3mb_da_413(borrador, monkeypatch):
    cliente, loan_id, item_id = borrador
    monkeypatch.setattr(media_manager, "LIMITE_FOTO", 100)

    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_entrega_frente", "loan_item_id": str(item_id)},
        files={"file": ("foto.png", png_bytes(200, 200), "image/png")},
    )
    assert resp.status_code == 413
    assert resp.json()["detail"] == "La foto excede 3 MB."


def test_lo_que_no_es_imagen_da_422_antes_que_413(borrador, monkeypatch):
    """Dos errores que la persona arregla distinto: uno eligiendo otro archivo,
    el otro comprimiendo. Un PDF de 5 MB no debe decir "comprime"."""
    cliente, loan_id, item_id = borrador
    monkeypatch.setattr(media_manager, "LIMITE_FOTO", 10)

    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_entrega_frente", "loan_item_id": str(item_id)},
        files={"file": ("doc.pdf", b"%PDF-1.7" + b"x" * 500, "application/pdf")},
    )
    assert resp.status_code == 422


def test_una_bomba_de_descompresion_se_rechaza(monkeypatch):
    """Un PNG chico puede declarar 40.000x40.000 px y reventar la memoria al
    abrirlo para la miniatura. El plan pedia limite de dimensiones; el contrato
    no lo recogio. Se aplica igual."""
    monkeypatch.setattr(media_manager, "MAXIMO_PIXELES", 100)
    with pytest.raises(Exception):
        media_manager.validar(png_bytes(50, 50), "foto_entrega_frente")


# ── Forma de la respuesta ───────────────────────────────────────────────────


def test_la_respuesta_tiene_exactamente_tres_claves(borrador):
    """No se devuelve `file_path` ni `url`: no exponer la ruta de disco es parte
    de la mitigacion del IDOR."""
    cliente, loan_id, item_id = borrador
    cuerpo = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()
    assert set(cuerpo) == {"id", "kind", "sha256"}
    assert len(cuerpo["sha256"]) == 64


def test_el_sha256_es_el_de_los_bytes_originales(borrador, db):
    import hashlib

    cliente, loan_id, item_id = borrador
    contenido = png_bytes(60, 45)
    cuerpo = subir(cliente, loan_id, "foto_entrega_frente", item_id, contenido).json()
    assert cuerpo["sha256"] == hashlib.sha256(contenido).hexdigest()


def test_el_nombre_en_disco_no_es_adivinable(borrador, db):
    """El nombre que manda el cliente es dato hostil (`../../`, byte nulo, doble
    extension) y embeber el folio haria las rutas enumerables."""
    import re

    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]
    fila = db.get(MediaAsset, media_id)

    assert re.fullmatch(r"[0-9a-f]{32}\.png", fila.file_name), fila.file_name
    assert "foto" not in fila.file_name
    assert "CE-" not in fila.file_name


def test_el_mime_se_deriva_de_los_bytes_no_del_encabezado(borrador, db):
    cliente, loan_id, item_id = borrador
    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_entrega_frente", "loan_item_id": str(item_id)},
        files={"file": ("mentira.jpg", png_bytes(), "image/jpeg")},
    )
    assert db.get(MediaAsset, resp.json()["id"]).mime_type == "image/png"


# ── Reglas de kind y estado ─────────────────────────────────────────────────


def test_un_kind_inventado_es_422(borrador):
    cliente, loan_id, item_id = borrador
    resp = cliente.post(
        f"/api/loans/{loan_id}/media",
        data={"kind": "foto_lateral", "loan_item_id": str(item_id)},
        files={"file": ("foto.png", png_bytes(), "image/png")},
    )
    assert resp.status_code == 422
    assert resp.json()["codigo"] == "VALOR_INVALIDO"


def test_una_firma_no_lleva_loan_item_id(confirmado):
    cliente, loan_id, item_id = confirmado
    resp = subir(cliente, loan_id, "firma_responsable", item_id)
    assert resp.status_code == 422


def test_una_foto_sin_loan_item_id_es_422(borrador):
    cliente, loan_id, _ = borrador
    resp = subir(cliente, loan_id, "foto_entrega_frente")
    assert resp.status_code == 422


def test_no_se_sube_una_foto_de_entrega_a_un_prestamo_ya_confirmado(inventario, db):
    """Permitirlo dejaria reescribir la evidencia detras de una responsiva ya
    firmada."""
    usuario_con(db, username="ana.ruiz")
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]
    item_id = cliente.post(f"/api/loans/{loan_id}/items", json={"equipment_id": 1}).json()["items"][0]["id"]
    subir(cliente, loan_id, "foto_entrega_frente", item_id)
    subir(cliente, loan_id, "foto_entrega_atras", item_id)
    cliente.post(f"/api/loans/{loan_id}/confirmar")

    resp = subir(cliente, loan_id, "foto_entrega_frente", item_id)
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "TRANSICION_INVALIDA"


def test_no_se_sube_foto_de_devolucion_a_un_borrador(borrador):
    cliente, loan_id, item_id = borrador
    resp = subir(cliente, loan_id, "foto_dev_frente", item_id)
    assert resp.status_code == 409


def test_resubir_el_mismo_kind_reemplaza(borrador, db):
    """El payload expone un solo id por kind, asi que dos filas del mismo kind no
    tienen representacion. Volver a tomar una foto es flujo normal."""
    from pathlib import Path

    cliente, loan_id, item_id = borrador
    primero = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()
    fila_vieja = db.get(MediaAsset, primero["id"])
    ruta_vieja, sha_viejo = fila_vieja.file_path, fila_vieja.sha256

    segundo = subir(cliente, loan_id, "foto_entrega_frente", item_id, png_bytes(50, 50)).json()

    # Queda UNA sola fila de ese kind y el archivo viejo no sobrevive en disco.
    # (SQLite reusa el rowid tras borrar la ultima fila, asi que el id puede
    # repetirse; lo que no puede repetirse es el contenido.)
    assert segundo["sha256"] != sha_viejo
    assert not Path(ruta_vieja).exists(), "quedo un archivo huerfano en disco"
    assert (
        db.query(MediaAsset)
        .filter(MediaAsset.loan_item_id == item_id, MediaAsset.kind == "foto_entrega_frente")
        .count()
        == 1
    )

    ficha = cliente.get(f"/api/loans/{loan_id}").json()
    assert ficha["items"][0]["media"]["foto_entrega_frente"] == segundo["id"]


def test_las_firmas_cuelgan_del_prestamo_no_del_renglon(confirmado, db):
    cliente, loan_id, item_id = confirmado
    # `firma_entrega` es identidad, no permiso — solo la titular del paquete
    # singleton TITULAR_FIRMA_EQUIPO puede subirla (ver test_api_prestamos.py
    # para ese candado en detalle) — aqui solo importa que la firma cuelga del
    # prestamo, no del renglon, asi que se crea una titular de paso.
    usuario_con(db, username="aprobadora.media", aditivos=("APROBADOR_EQUIPO", "TITULAR_FIRMA_EQUIPO"))
    media_id = subir(logueado("aprobadora.media"), loan_id, "firma_entrega").json()["id"]

    assert db.get(MediaAsset, media_id).loan_item_id is None
    ficha = cliente.get(f"/api/loans/{loan_id}").json()
    assert ficha["firmas"]["firma_entrega"] == media_id
    assert ficha["firmas"]["firma_responsable"] is None


# ── Descarga y autorizacion ─────────────────────────────────────────────────


def test_el_participante_descarga_su_media(borrador):
    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]

    resp = cliente.get(f"/api/media/{media_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.headers["cache-control"].startswith("private")
    # Sin filename: se sirve inline para poder pintarlo en un <img>.
    assert "content-disposition" not in resp.headers


def test_un_extrano_no_descarga_media_de_un_prestamo_ajeno(borrador, db):
    """Criterio de cierre de S4."""
    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]

    usuario_con(db, username="curioso")
    resp = logueado("curioso").get(f"/api/media/{media_id}")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_la_aprobadora_si_descarga_media_ajena(borrador, db):
    """Necesita ver las fotos ANTES de autorizar, y en ese momento todavia no es
    participante: entra por `ver_global`, que le da su paquete aditivo."""
    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]

    usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))
    assert logueado("melisa").get(f"/api/media/{media_id}").status_code == 200


def test_sin_sesion_no_hay_media(borrador, client):
    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]
    assert client.get(f"/api/media/{media_id}").status_code == 401


def test_media_inexistente_es_404(borrador):
    cliente, _, _ = borrador
    resp = cliente.get("/api/media/99999")
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_no_hay_mount_estatico_de_uploads():
    """Un StaticFiles sirve por ruta de disco sin consultar la fila: quien
    reciba la URL descarga la foto del prestamo de otro."""
    from app.main import app

    rutas = [getattr(r, "path", "") for r in app.routes]
    assert not any(str(r).startswith("/uploads") for r in rutas)


# ── Miniatura ───────────────────────────────────────────────────────────────


def test_la_miniatura_mide_96px_en_el_lado_mayor(borrador):
    from io import BytesIO

    from PIL import Image

    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id, png_bytes(800, 400)).json()["id"]

    resp = cliente.get(f"/api/media/{media_id}", params={"tamano": "thumb"})
    assert resp.status_code == 200
    with Image.open(BytesIO(resp.content)) as imagen:
        assert max(imagen.size) == 96
        assert imagen.size == (96, 48)


def test_la_miniatura_pesa_mucho_menos_que_el_original(borrador):
    cliente, loan_id, item_id = borrador
    contenido = png_bytes(1200, 900, color=(12, 200, 90))
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id, contenido).json()["id"]

    original = cliente.get(f"/api/media/{media_id}")
    thumb = cliente.get(f"/api/media/{media_id}", params={"tamano": "thumb"})
    assert len(thumb.content) < len(original.content)


def test_la_miniatura_conserva_el_formato(confirmado):
    """Pasar una firma PNG a JPEG le pone fondo negro y llena el trazo de
    artefactos: el canvas de firma es transparente."""
    cliente, loan_id, _ = confirmado
    media_id = subir(cliente, loan_id, "firma_responsable").json()["id"]
    resp = cliente.get(f"/api/media/{media_id}", params={"tamano": "thumb"})
    assert resp.headers["content-type"].startswith("image/png")


def test_la_miniatura_exige_el_mismo_permiso_que_el_original(borrador, db):
    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]

    usuario_con(db, username="curioso")
    resp = logueado("curioso").get(f"/api/media/{media_id}", params={"tamano": "thumb"})
    assert resp.status_code == 403


def test_un_tamano_desconocido_es_422(borrador):
    """Ignorarlo en silencio haria que un typo del cliente baje 3 MB para pintar
    96 px y nadie se enteraria."""
    cliente, loan_id, item_id = borrador
    media_id = subir(cliente, loan_id, "foto_entrega_frente", item_id).json()["id"]

    resp = cliente.get(f"/api/media/{media_id}", params={"tamano": "grande"})
    assert resp.status_code == 422
    assert resp.json()["codigo"] == "VALOR_INVALIDO"
