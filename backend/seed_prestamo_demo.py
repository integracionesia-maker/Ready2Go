"""Prestamo de demostracion: el que retrata
`docs/contratos/fixtures/prestamo_demo.json`.

Ejecutar desde backend/:

    python seed_prestamo_demo.py

Ese fixture es **el criterio de aceptacion del payload** de
`GET /api/loans/{id}` (tarea S7). Por eso este seed fija ids explicitos —
prestamo 7, renglon 11, media 39/40/41/42, evento 21 — en vez de dejarlos al
autoincrement: el cliente alimenta sus mocks con la copia literal del fixture y
una guardia de cada lado compara contra el mismo archivo. Con ids distintos, las
dos guardias comparan cosas distintas y ninguna sirve.

Genera archivos de imagen de verdad (2 fotos + 2 firmas) con su sha256, no
registros huerfanos: `GET /api/media/{id}` tiene que poder servirlos.

Idempotente: si el prestamo 7 ya existe, no lo toca.
"""

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app import folio as folio_mod
from app import models, security
from app.models_equipos import (
    EstadoPrestamo,
    KindMedia,
    Loan,
    LoanEvent,
    LoanItem,
    MediaAsset,
    ResponsivaDoc,
    TipoEvento,
)

import seed_equipos

DIRECTORIO_MEDIA = Path("./uploads/equipos")
DIRECTORIO_RESPONSIVAS = Path("./uploads/responsivas")

LOAN_ID = 7
FOLIO = "CE-0007"
ITEM_ID = 11
EVENTO_ID = 21
EQUIPO_ID = 1

# 2026-07-25 10:14 CDMX = 16:14 UTC. Mexico no aplica horario de verano desde
# 2022, asi que America/Mexico_City es UTC-6 todo el año.
CREADO_UTC = datetime(2026, 7, 25, 16, 14, 0)
FECHA_ENTREGA = date(2026, 7, 25)
FECHA_REGRESO_ESPERADA = date(2026, 7, 30)

MEDIA_IDS = {
    KindMedia.FIRMA_ENTREGA.value: 39,
    KindMedia.FIRMA_RESPONSABLE.value: 40,
    KindMedia.FOTO_ENTREGA_FRENTE.value: 41,
    KindMedia.FOTO_ENTREGA_ATRAS.value: 42,
}

USUARIOS_DEMO = [
    {
        "id": 4,
        "username": "melisa",
        "email": "melisa.avendano@grupo-ortiz.com",
        "full_name": "Melisa Avendano",
        "role": "colaborador_mkt",
        "aditivos": ["APROBADOR_EQUIPO"],
    },
    {
        "id": 12,
        "username": "ana.ruiz",
        "email": "ana.ruiz@grupo-ortiz.com",
        "full_name": "Ana Ruiz",
        "role": "colaborador_mkt",
        "aditivos": [],
    },
]


class SeedDemoBloqueado(RuntimeError):
    """El estado de la base impide reproducir el fixture. Se avisa, no se pisa
    nada: sobrescribir usuarios ajenos para cuadrar un id es peor que no sembrar."""


# ── Archivos de media ───────────────────────────────────────────────────────


def _png(ancho: int, alto: int, color: tuple[int, int, int], trazo: bool = False) -> bytes:
    from io import BytesIO

    from PIL import Image, ImageDraw

    imagen = Image.new("RGB", (ancho, alto), color)
    if trazo:
        # Una firma en blanco no prueba nada: se dibuja un trazo para que el PDF
        # y la miniatura tengan algo real que mostrar.
        dibujo = ImageDraw.Draw(imagen)
        dibujo.line(
            [(20, alto - 30), (ancho // 3, 25), (2 * ancho // 3, alto - 25), (ancho - 20, 35)],
            fill=(20, 20, 20),
            width=4,
            joint="curve",
        )
    buffer = BytesIO()
    imagen.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _escribir_media(nombre: str, contenido: bytes) -> tuple[str, str, int, str]:
    DIRECTORIO_MEDIA.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_MEDIA / nombre
    destino.write_bytes(contenido)
    return (
        nombre,
        str(destino.resolve()),
        len(contenido),
        hashlib.sha256(contenido).hexdigest(),
    )


ARCHIVOS_DEMO = {
    KindMedia.FIRMA_ENTREGA.value: ("demo_CE-0007_firma_entrega.png", (300, 120), True),
    KindMedia.FIRMA_RESPONSABLE.value: ("demo_CE-0007_firma_responsable.png", (300, 120), True),
    KindMedia.FOTO_ENTREGA_FRENTE.value: ("demo_CE-0007_frente.png", (640, 480), False),
    KindMedia.FOTO_ENTREGA_ATRAS.value: ("demo_CE-0007_atras.png", (640, 480), False),
}

COLORES = {
    KindMedia.FIRMA_ENTREGA.value: (255, 255, 255),
    KindMedia.FIRMA_RESPONSABLE.value: (255, 255, 255),
    KindMedia.FOTO_ENTREGA_FRENTE.value: (188, 190, 194),
    KindMedia.FOTO_ENTREGA_ATRAS.value: (120, 122, 126),
}


# ── Usuarios ────────────────────────────────────────────────────────────────


def _asegurar_usuarios(db, verbose: bool = True) -> dict[str, models.User]:
    resultado: dict[str, models.User] = {}
    for datos in USUARIOS_DEMO:
        por_id = db.get(models.User, datos["id"])
        por_username = (
            db.query(models.User).filter(models.User.username == datos["username"]).first()
        )

        if por_id is not None and por_id.username != datos["username"]:
            raise SeedDemoBloqueado(
                f"El id {datos['id']} ya lo ocupa '{por_id.username}', y el fixture del "
                f"contrato lo asigna a '{datos['username']}'. No se sobrescribe nada. "
                "Corre este seed en una base limpia o pide cambio del fixture."
            )

        if por_username is not None and por_username.id != datos["id"]:
            raise SeedDemoBloqueado(
                f"'{datos['username']}' ya existe con id {por_username.id}, y el fixture "
                f"del contrato espera id {datos['id']}. No se reasignan ids de usuario. "
                "Corre este seed en una base limpia."
            )

        if por_id is not None:
            resultado[datos["username"]] = por_id
            if verbose:
                print(f"  = usuario [{datos['id']}] {datos['username']}")
            continue

        temporal = security.generate_temp_password()
        usuario = models.User(
            id=datos["id"],
            username=datos["username"],
            email=datos["email"],
            password_hash=security.hash_password(temporal),
            full_name=datos["full_name"],
            role=datos["role"],
            is_active=True,
            must_change_password=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        resultado[datos["username"]] = usuario
        if verbose:
            print(f"  + usuario [{usuario.id}] {usuario.username} — clave temporal {temporal}")

    return resultado


def _conceder_aditivos(db, usuarios: dict[str, models.User], verbose: bool = True) -> None:
    from app import crud_rbac
    from app.models_rbac import Role

    for datos in USUARIOS_DEMO:
        for paquete in datos["aditivos"]:
            if db.get(Role, paquete) is None:
                if verbose:
                    print(f"  ! paquete '{paquete}' no sembrado; corre migrate_rbac_aditivo.py")
                continue
            crud_rbac.conceder(db, usuarios[datos["username"]].id, paquete, granted_by=None)
            if verbose:
                print(f"  = {paquete} para {datos['username']}")


# ── Prestamo ────────────────────────────────────────────────────────────────


def sembrar_prestamo_demo(db, verbose: bool = True) -> Loan:
    existente = db.get(Loan, LOAN_ID)
    if existente is not None:
        if verbose:
            print(f"  = prestamo [{LOAN_ID}] {existente.folio} ya existia")
        return existente

    usuarios = _asegurar_usuarios(db, verbose)
    _conceder_aditivos(db, usuarios, verbose)

    equipo = db.get(models.Equipment, EQUIPO_ID)
    if equipo is None:
        raise SeedDemoBloqueado(
            f"No existe el equipo {EQUIPO_ID}. Corre primero: python seed_equipos.py"
        )

    ana = usuarios["ana.ruiz"]
    melisa = usuarios["melisa"]

    prestamo = Loan(
        id=LOAN_ID,
        folio=FOLIO,
        responsable_user_id=ana.id,
        responsable_nombre=ana.full_name,
        responsable_email=ana.email,
        area="Contenido",
        empresa="MERCASYSTEM SA DE CV",
        motivo="Live Plaza Madero",
        notas_responsiva=None,
        entregado_por_user_id=melisa.id,
        fecha_entrega=FECHA_ENTREGA,
        fecha_regreso_esperada=FECHA_REGRESO_ESPERADA,
        fecha_regreso_real=None,
        estado=EstadoPrestamo.PRESTADO.value,
        # Sin autorizar a proposito: el fixture retrata un prestamo entregado que
        # todavia espera el visto bueno de la aprobadora. `entrega_autorizada` es
        # ortogonal al estado, y esa es justo la parte que se presta a confusion.
        entrega_autorizada=False,
        created_by_user_id=ana.id,
        created_at=CREADO_UTC,
        updated_at=CREADO_UTC,
    )
    db.add(prestamo)
    db.flush()

    item = LoanItem(
        id=ITEM_ID,
        loan_id=prestamo.id,
        equipment_id=equipo.id,
        accesorios_seleccionados=json.dumps(["Cargador", "Funda"], ensure_ascii=False),
        accesorios_otros=None,
        cargador_con="responsable",
        devuelto_at=None,
        no_devuelto=False,
    )
    db.add(item)
    db.flush()

    for kind, media_id in MEDIA_IDS.items():
        nombre, tamano, trazo = ARCHIVOS_DEMO[kind]
        contenido = _png(tamano[0], tamano[1], COLORES[kind], trazo=trazo)
        file_name, file_path, size_bytes, sha = _escribir_media(nombre, contenido)
        es_firma = kind in (
            KindMedia.FIRMA_ENTREGA.value,
            KindMedia.FIRMA_RESPONSABLE.value,
        )
        db.add(
            MediaAsset(
                id=media_id,
                loan_id=prestamo.id,
                # Las firmas cuelgan del prestamo, no de un renglon: son de las
                # personas, no de un equipo.
                loan_item_id=None if es_firma else item.id,
                kind=kind,
                file_name=file_name,
                file_path=file_path,
                mime_type="image/png",
                size_bytes=size_bytes,
                sha256=sha,
                created_by_user_id=ana.id,
                created_at=CREADO_UTC,
            )
        )

    db.add(
        LoanEvent(
            id=EVENTO_ID,
            loan_id=prestamo.id,
            actor_user_id=ana.id,
            actor_nombre=ana.full_name,
            tipo=TipoEvento.CREADO.value,
            detalle="Prestamo confirmado. Carta responsiva firmada por ambas partes.",
            created_at=CREADO_UTC,
        )
    )

    _registrar_responsiva(db, prestamo, ana, verbose)

    folio_mod.sincronizar_contador(db)
    db.commit()

    if verbose:
        print(f"  + prestamo [{prestamo.id}] {prestamo.folio} — {equipo.nombre}")
    return prestamo


def _registrar_responsiva(db, prestamo: Loan, actor, verbose: bool) -> None:
    """Registra la version 1 de la carta responsiva.

    Genera el PDF si el modulo de S5 ya existe; si no, deja el registro con la
    ruta prevista y lo dice. El payload de `GET /api/loans/{id}` solo necesita
    `version` y la url, asi que el fixture cuadra en los dos casos.
    """
    DIRECTORIO_RESPONSIVAS.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_RESPONSIVAS / f"{prestamo.folio}_v1.pdf"
    sha = None

    try:
        from app.pdf import responsiva as generador
    except ImportError:
        generador = None

    if generador is not None:
        sha = generador.generar_a_disco(db, prestamo, destino)
        if verbose:
            print(f"  + responsiva v1 generada en {destino}")
    elif verbose:
        print(f"  = responsiva v1 registrada sin archivo (S5 la genera): {destino}")

    db.add(
        ResponsivaDoc(
            loan_id=prestamo.id,
            version=1,
            file_path=str(destino),
            sha256=sha,
            generated_by_user_id=actor.id,
            generated_at=CREADO_UTC,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed del prestamo de demostracion.")
    parser.add_argument("--silencioso", action="store_true")
    args = parser.parse_args()
    verbose = not args.silencioso

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("=== Inventario ===")
        seed_equipos.sembrar_equipos(db, verbose)
        seed_equipos.sembrar_empresas(db, verbose)
        print("=== Prestamo demo ===")
        prestamo = sembrar_prestamo_demo(db, verbose)
        print(f"Listo: {prestamo.folio} (id {prestamo.id}).")
    except SeedDemoBloqueado as exc:
        raise SystemExit(f"Seed detenido: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
