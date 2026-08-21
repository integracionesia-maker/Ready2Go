"""Carta responsiva en PDF (S5 / WP5).

Criterio de cierre del reparto: la version 2 no pisa la 1, y un PDF generado con
datos reales para revision visual.
"""

from pathlib import Path

import pytest
from pypdf import PdfReader

import seed_equipos
from app import crud_loans
from app.models_equipos import Empresa, ResponsivaDoc
from app.pdf import plantilla, responsiva

from .conftest import logueado, subir, usuario_con


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


@pytest.fixture
def ana(inventario, db):
    return usuario_con(db, username="ana.ruiz")


def _confirmado(cliente, equipment_ids=(1,)):
    loan_id = cliente.post(
        "/api/loans/",
        json={
            "area": "Contenido",
            "empresa": "MERCASYSTEM SA DE CV",
            "motivo": "Live Plaza Madero",
            "fecha_entrega": "2026-07-25",
            "fecha_regreso_esperada": "2026-07-30",
        },
    ).json()["id"]
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
    cliente.post(f"/api/loans/{loan_id}/confirmar")
    return loan_id


def _texto(ruta: str) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(ruta).pages)


# ── Generacion ──────────────────────────────────────────────────────────────


def test_confirmar_genera_un_pdf_de_verdad(inventario, ana, db):
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()

    assert doc.version == 1
    assert Path(doc.file_path).exists()
    assert Path(doc.file_path).read_bytes().startswith(b"%PDF")
    assert len(doc.sha256) == 64


def test_el_sha256_guardado_es_el_del_archivo(inventario, ana, db):
    import hashlib

    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    assert doc.sha256 == hashlib.sha256(Path(doc.file_path).read_bytes()).hexdigest()


def test_el_nombre_del_archivo_lleva_folio_y_version(inventario, ana, db):
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    assert Path(doc.file_path).name == "CE-0001_v1.pdf"


def test_una_responsiva_de_un_equipo_cabe_en_una_hoja(inventario, ana, db):
    """Las firmas solas en la hoja 2 son la peor forma de imprimir una carta
    responsiva: nadie sabe si esa hoja pertenece a esta."""
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    assert len(PdfReader(doc.file_path).pages) == 1


# ── Contenido ───────────────────────────────────────────────────────────────


def test_el_pdf_dice_lo_que_la_carta_tiene_que_decir(inventario, ana, db):
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    texto = _texto(doc.file_path)

    assert "FOLIO: CE-0001" in texto
    assert "CARTA RESPONSIVA DE EQUIPO" in texto
    assert "Contenido" in texto                       # area
    assert "MERCASYSTEM SA DE CV" in texto            # empresa del colaborador
    assert "Live Plaza Madero" in texto               # motivo
    assert "iPhone 17 Pro" in texto                   # modelo del equipo
    assert "Cargador, Funda" in texto                 # accesorios del renglon
    assert "Se lo lleva el responsable" in texto      # cargador_con legible


def test_la_razon_social_emisora_sale_de_la_tabla(inventario, ana, db):
    """§10.21: la maqueta la tenia hardcodeada en el JavaScript. Cambiarla aqui
    tiene que cambiar el PDF sin tocar codigo."""
    db.query(Empresa).filter(Empresa.id == 3).update(
        {"razon_social": "OTRA RAZON SOCIAL SA DE CV", "rfc": "XAXX010101000"}
    )
    db.commit()

    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    texto = _texto(doc.file_path)

    assert "OTRA RAZON SOCIAL SA DE CV" in texto
    assert "XAXX010101000" in texto
    # Canario por RFC, no por nombre: el RFC de la emisora sembrada por defecto
    # (SCQ1212149P0) desaparece al cambiar la fila -> el bloque emisor sale de la
    # tabla. No se usa "QUANTUM DE OCCIDENTE" como canario porque desde
    # 2026-08-20 ese nombre es el empleador FIJO del cuerpo de la carta y aparece
    # siempre, sea cual sea la emisora.
    assert "SCQ1212149P0" not in texto


def test_sin_emisora_configurada_no_se_confirma(db, catalogo):
    """No se entrega equipo sin carta responsiva. Fallar es correcto; generar un
    encabezado a medias, no."""
    seed_equipos.sembrar_equipos(db, verbose=False)  # sin empresas a proposito
    usuario_con(db, username="ana.ruiz")
    cliente = logueado("ana.ruiz")

    with pytest.raises(responsiva.EmisoraNoConfigurada):
        _confirmado(cliente)


def test_el_texto_legal_es_literal(inventario, ana, db):
    """El plan §6 pide el texto "tal como esta redactado en la maqueta".
    Reescribir un parrafo de responsabilidad civil cambia lo que se firma."""
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    texto = " ".join(_texto(doc.file_path).split())

    assert "Situaciones extraordinarias" in texto
    for etiqueta, cuerpo in plantilla.SITUACIONES_EXTRAORDINARIAS:
        assert " ".join(cuerpo.split()) in texto, (etiqueta, cuerpo[:40])


def test_estan_los_cuatro_puntos_de_situaciones_extraordinarias():
    """Daño, robo, pérdida y la Nota de entrega. El quinto punto (opción de
    compra al término del contrato) se eliminó por decisión del área (2026-08-20)."""
    etiquetas = [e for e, _ in plantilla.SITUACIONES_EXTRAORDINARIAS]
    assert etiquetas == ["Daño:", "Robo:", "Pérdida:", "Nota:"]


def test_los_pies_de_firma_son_los_de_la_maqueta():
    assert plantilla.PIE_FIRMA_RESPONSABLE == "Nombre y firma del responsable"
    # Sin articulo y con Entrega en mayuscula: asi esta en la maqueta.
    assert plantilla.PIE_FIRMA_ENTREGA == "Nombre y firma Entrega"


def test_el_pdf_no_afirma_validez_legal(inventario, ana, db):
    """§6: una firma en canvas no es firma electronica avanzada. El documento no
    debe incluir leyendas que sugieran lo contrario."""
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    texto = _texto(doc.file_path).lower()

    for frase in ("firma electrónica avanzada", "validez legal", "valor probatorio pleno"):
        assert frase not in texto


def test_la_fecha_larga_es_la_de_la_maqueta():
    from datetime import date

    assert plantilla.fecha_larga(date(2026, 7, 25)) == "25 de julio de 2026"
    assert plantilla.fecha_larga(date(2026, 1, 5)) == "5 de enero de 2026"
    assert plantilla.fecha_larga(None) == plantilla.VACIO


def test_un_nombre_con_ampersand_no_rompe_el_documento(inventario, ana, db):
    """`Paragraph` interpreta un subconjunto de XML: un `&` sin escapar rompe el
    PDF entero."""
    from app.models_equipos import Equipment

    db.query(Equipment).filter(Equipment.id == 1).update(
        {"nombre": "Camara <A&B> \"especial\"", "marca": "R&D"}
    )
    db.commit()

    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    texto = _texto(doc.file_path)
    assert "A&B" in texto
    assert "R&D" in texto


def test_los_campos_vacios_salen_como_raya_no_como_none(inventario, ana, db):
    loan_id = _confirmado(logueado("ana.ruiz"))
    doc = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    texto = _texto(doc.file_path)
    assert "None" not in texto
    assert "null" not in texto
    assert plantilla.VACIO in texto  # el equipo 1 no tiene numero de serie


# ── Versionado ──────────────────────────────────────────────────────────────


def test_la_version_2_no_pisa_la_1(inventario, ana, db):
    """Criterio de cierre de S5. Un documento firmado es evidencia: sobrescribir
    destruye el rastro."""
    loan_id = _confirmado(logueado("ana.ruiz"))
    prestamo = crud_loans.obtener(db, loan_id)
    v1 = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()
    ruta_v1, sha_v1 = v1.file_path, v1.sha256
    bytes_v1 = Path(ruta_v1).read_bytes()

    crud_loans.generar_responsiva(db, prestamo, ana, motivo="Se corrigio el area")
    db.commit()

    docs = (
        db.query(ResponsivaDoc)
        .filter(ResponsivaDoc.loan_id == loan_id)
        .order_by(ResponsivaDoc.version)
        .all()
    )
    assert [d.version for d in docs] == [1, 2]
    assert docs[1].motivo_regeneracion == "Se corrigio el area"
    assert docs[1].file_path != ruta_v1

    # La v1 sigue existiendo, con su contenido y su hash intactos.
    assert Path(ruta_v1).exists()
    assert Path(ruta_v1).read_bytes() == bytes_v1
    assert docs[0].sha256 == sha_v1
    assert Path(docs[1].file_path).exists()


def test_no_se_puede_escribir_encima_de_un_archivo_existente(inventario, ana, db):
    loan_id = _confirmado(logueado("ana.ruiz"))
    prestamo = crud_loans.obtener(db, loan_id)
    v1 = db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == loan_id).one()

    with pytest.raises(responsiva.ArchivoYaExiste):
        responsiva.generar_a_disco(db, prestamo, Path(v1.file_path), version=1)


def test_la_base_impide_dos_filas_con_la_misma_version(inventario, ana, db):
    from sqlalchemy.exc import IntegrityError

    loan_id = _confirmado(logueado("ana.ruiz"))
    db.add(ResponsivaDoc(loan_id=loan_id, version=1, file_path="x.pdf"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_el_payload_reporta_la_version_mas_alta(inventario, ana, db):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    crud_loans.generar_responsiva(db, crud_loans.obtener(db, loan_id), ana, motivo="v2")
    db.commit()

    cuerpo = cliente.get(f"/api/loans/{loan_id}").json()
    assert cuerpo["responsiva"]["version"] == 2
    assert cuerpo["responsiva"]["url"] == f"/api/loans/{loan_id}/responsiva.pdf"


# ── Endpoint ────────────────────────────────────────────────────────────────


def test_el_participante_descarga_su_responsiva(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)

    resp = cliente.get(f"/api/loans/{loan_id}/responsiva.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert "inline" in resp.headers["content-disposition"]
    assert "CE-0001_v1.pdf" in resp.headers["content-disposition"]


def test_un_extrano_no_descarga_la_responsiva_ajena(inventario, ana, db):
    """Es el recurso mas sensible del modulo: trae nombre, area, numero de serie
    y las dos firmas."""
    loan_id = _confirmado(logueado("ana.ruiz"))
    usuario_con(db, username="curioso")

    resp = logueado("curioso").get(f"/api/loans/{loan_id}/responsiva.pdf")
    assert resp.status_code == 403
    assert resp.json()["codigo"] == "SIN_PERMISO"


def test_la_aprobadora_si_descarga_la_responsiva_ajena(inventario, ana, db):
    loan_id = _confirmado(logueado("ana.ruiz"))
    usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))
    assert logueado("melisa").get(f"/api/loans/{loan_id}/responsiva.pdf").status_code == 200


def test_sin_sesion_no_hay_responsiva(inventario, ana, client):
    loan_id = _confirmado(logueado("ana.ruiz"))
    assert client.get(f"/api/loans/{loan_id}/responsiva.pdf").status_code == 401


def test_un_borrador_no_tiene_responsiva(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = cliente.post("/api/loans/", json={}).json()["id"]

    resp = cliente.get(f"/api/loans/{loan_id}/responsiva.pdf")
    assert resp.status_code == 404
    assert resp.json()["codigo"] == "NO_ENCONTRADO"


def test_por_defecto_se_sirve_la_ultima_version(inventario, ana, db):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    crud_loans.generar_responsiva(db, crud_loans.obtener(db, loan_id), ana, motivo="v2")
    db.commit()

    resp = cliente.get(f"/api/loans/{loan_id}/responsiva.pdf")
    assert "CE-0001_v2.pdf" in resp.headers["content-disposition"]


def test_se_puede_pedir_una_version_historica(inventario, ana, db):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    crud_loans.generar_responsiva(db, crud_loans.obtener(db, loan_id), ana, motivo="v2")
    db.commit()

    resp = cliente.get(f"/api/loans/{loan_id}/responsiva.pdf", params={"version": 1})
    assert resp.status_code == 200
    assert "CE-0001_v1.pdf" in resp.headers["content-disposition"]


def test_una_version_inexistente_es_404(inventario, ana):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    assert cliente.get(f"/api/loans/{loan_id}/responsiva.pdf", params={"version": 9}).status_code == 404


def test_la_condicion_se_congela_contra_la_auditoria_de_la_entrega(inventario, ana, db):
    """Si se leyera la ultima auditoria del catalogo, la v2 de una carta ya
    firmada diria una condicion distinta de la v1 sobre los mismos hechos."""
    from datetime import date

    from app.models_equipos import EquipmentAudit

    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)  # fecha_entrega 2026-07-25

    # Auditoria POSTERIOR a la entrega: no debe aparecer en la responsiva.
    db.add(
        EquipmentAudit(
            equipment_id=1,
            condicion="danado",
            estado_fisico="usado",
            comentario="Pantalla estrellada tras el evento.",
            fecha=date(2026, 7, 27),
        )
    )
    db.commit()

    crud_loans.generar_responsiva(db, crud_loans.obtener(db, loan_id), ana, motivo="v2")
    db.commit()
    v2 = (
        db.query(ResponsivaDoc)
        .filter(ResponsivaDoc.loan_id == loan_id, ResponsivaDoc.version == 2)
        .one()
    )
    texto = _texto(v2.file_path)

    assert "Pantalla estrellada" not in texto
    assert "Sin rayones" in texto
