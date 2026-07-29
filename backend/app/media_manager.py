"""Fotos y firmas: validacion, guardado en disco y miniaturas.

**No importa `upload_manager.py`.** Aquel valida por extension y `Content-Type`,
que es justo el patron prohibido aqui, y ademas esta congelado. Son dos subidas
independientes que comparten cero codigo a proposito.

Por que magic bytes y no `Content-Type`: la cabecera del multipart la escribe el
cliente. Cualquiera manda `Content-Type: image/jpeg` con un `.php`, un `.svg` con
script adentro o un HTML. Lo unico que no se puede falsificar barato son los
primeros bytes del archivo, y son los que deciden. El `mime_type` que se guarda
se **deriva** de esos bytes; nunca se copia el que llego.

Por que el nombre en disco es un uuid: el nombre que manda el cliente es dato
hostil (`../../`, byte nulo, 300 caracteres, doble extension). Y embeber el folio
o el nombre de la persona haria las rutas enumerables y meteria datos personales
en el sistema de archivos.

Nunca hay mount estatico. Todo byte sale por `GET /api/media/{id}`, que valida
sesion y participacion. Un `StaticFiles` sirve por ruta de disco sin consultar la
fila: quien reciba o adivine la URL descarga la foto del prestamo de otro. Ya
paso en este repo con `tickets/file/{id}` y por eso se elimino el mount de
`/uploads`.
"""

from __future__ import annotations

import hashlib
import uuid
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from . import tz
from .errores import MediaInvalida, MediaMuyGrande
from .models_equipos import KindMedia, MediaAsset

__all__ = [
    "DIRECTORIO",
    "LIMITE_FOTO",
    "LIMITE_FIRMA",
    "LADO_MINIATURA",
    "MAXIMO_PIXELES",
    "KINDS_FIRMA",
    "KINDS_FOTO",
    "limite_de",
    "detectar_tipo",
    "validar",
    "guardar",
    "reemplazar",
    "miniatura",
    "borrar_archivo",
]

DIRECTORIO = Path("./uploads/equipos")

# Base 1024, igual que `upload_manager.MAX_FILE_SIZE`. El contrato dice "3 MB" y
# "250 KB" sin aclarar la base; se elige la misma que ya usa la casa para que un
# archivo de 3,05 MB no caiga de un lado en un modulo y del otro en el otro.
LIMITE_FOTO = 3 * 1024 * 1024
LIMITE_FIRMA = 250 * 1024

LADO_MINIATURA = 96

# Freno a la bomba de descompresion: un PNG de 200 KB puede declarar
# 40.000x40.000 px y reventar la memoria al abrirlo para la miniatura. El plan §5
# pedia "dimensiones maximas"; el contrato no lo recogio. Se aplica igual y se
# rechaza con MEDIA_INVALIDA, que si es un codigo del contrato.
MAXIMO_PIXELES = 50_000_000  # 50 Mpx: mas que cualquier camara de telefono

FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
FIRMA_JPEG = b"\xff\xd8\xff"

KINDS_FIRMA = (KindMedia.FIRMA_ENTREGA.value, KindMedia.FIRMA_RESPONSABLE.value)
KINDS_FOTO = (
    KindMedia.FOTO_ENTREGA_FRENTE.value,
    KindMedia.FOTO_ENTREGA_ATRAS.value,
    KindMedia.FOTO_DEV_FRENTE.value,
    KindMedia.FOTO_DEV_ATRAS.value,
)


def limite_de(kind: str) -> int:
    """3 MB para foto, 250 KB para firma. El contrato da dos limites y seis
    kinds; el prefijo es la unica particion posible."""
    return LIMITE_FIRMA if kind in KINDS_FIRMA else LIMITE_FOTO


def detectar_tipo(contenido: bytes) -> tuple[str, str]:
    """`(mime_type, extension)` deducidos de los primeros bytes.

    PNG son los 8 bytes de firma completos, no solo `\\x89PNG`. JPEG son los 3
    del marcador SOI (`FF D8 FF`); con solo `FF D8` la validacion es demasiado
    laxa y deja pasar basura.
    """
    if contenido.startswith(FIRMA_PNG):
        return "image/png", ".png"
    if contenido.startswith(FIRMA_JPEG):
        return "image/jpeg", ".jpg"
    raise MediaInvalida()


def _verificar_dimensiones(contenido: bytes) -> None:
    from PIL import Image

    try:
        with Image.open(BytesIO(contenido)) as imagen:
            ancho, alto = imagen.size
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de decodificacion es archivo invalido
        raise MediaInvalida() from exc

    if ancho * alto > MAXIMO_PIXELES:
        raise MediaInvalida(
            f"La imagen es demasiado grande ({ancho}x{alto} px). Maximo {MAXIMO_PIXELES // 1_000_000} Mpx."
        )


def validar(contenido: bytes, kind: str) -> tuple[str, str]:
    """Devuelve `(mime_type, extension)` o levanta.

    Orden a proposito: primero el tipo (422 `MEDIA_INVALIDA`), luego el tamano
    (413 `MEDIA_MUY_GRANDE`). Son dos errores que la persona arregla distinto:
    uno eligiendo otro archivo, el otro comprimiendo. Si se invirtiera, un PDF de
    5 MB diria "comprime" cuando el problema es que no es una imagen.
    """
    if not contenido:
        raise MediaInvalida("El archivo llego vacio.")

    mime, extension = detectar_tipo(contenido)

    limite = limite_de(kind)
    if len(contenido) > limite:
        if kind in KINDS_FIRMA:
            raise MediaMuyGrande("La firma excede 250 KB.")
        raise MediaMuyGrande("La foto excede 3 MB.")

    _verificar_dimensiones(contenido)
    return mime, extension


def guardar(
    db: Session,
    *,
    contenido: bytes,
    kind: str,
    loan_id: int,
    loan_item_id: int | None,
    actor_user_id: int | None,
) -> MediaAsset:
    """Valida, escribe el archivo y crea la fila. No hace commit: el llamador
    decide la transaccion."""
    mime, extension = validar(contenido, kind)

    DIRECTORIO.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}{extension}"
    destino = DIRECTORIO / nombre
    destino.write_bytes(contenido)

    fila = MediaAsset(
        loan_id=loan_id,
        loan_item_id=loan_item_id,
        kind=kind,
        file_name=nombre,
        file_path=str(destino.resolve()),
        mime_type=mime,
        size_bytes=len(contenido),
        # Hash de los bytes ORIGINALES, no de la miniatura: sirve para el
        # peritaje de la responsiva y para detectar duplicados.
        sha256=hashlib.sha256(contenido).hexdigest(),
        created_by_user_id=actor_user_id,
        created_at=tz.ahora_utc_naive(),
    )
    db.add(fila)
    db.flush()
    return fila


def reemplazar(
    db: Session,
    *,
    contenido: bytes,
    kind: str,
    loan_id: int,
    loan_item_id: int | None,
    actor_user_id: int | None,
) -> MediaAsset:
    """Sube y **reemplaza** la anterior del mismo `(prestamo, renglon, kind)`.

    El payload de `GET /api/loans/{id}` expone un solo id por kind
    (`media: {foto_entrega_frente: 41, ...}`), asi que dos filas del mismo kind
    no tienen representacion: habria que elegir una por orden, y el orden no esta
    en el contrato. Volver a tomar una foto es flujo normal —la maqueta tiene
    boton "Cambiar foto"—, no un caso raro.

    Se borra tambien el archivo viejo: si no, `uploads/equipos/` se llena de
    huerfanos que nadie sabe a quien pertenecen.
    """
    consulta = db.query(MediaAsset).filter(
        MediaAsset.loan_id == loan_id, MediaAsset.kind == kind
    )
    consulta = (
        consulta.filter(MediaAsset.loan_item_id == loan_item_id)
        if loan_item_id is not None
        else consulta.filter(MediaAsset.loan_item_id.is_(None))
    )

    for anterior in consulta.all():
        borrar_archivo(anterior.file_path)
        db.delete(anterior)
    db.flush()

    return guardar(
        db,
        contenido=contenido,
        kind=kind,
        loan_id=loan_id,
        loan_item_id=loan_item_id,
        actor_user_id=actor_user_id,
    )


def miniatura(ruta: str, mime_type: str) -> tuple[bytes, str]:
    """Miniatura de 96px en el lado mayor, conservando proporcion y formato.

    Se conserva el formato: pasar una firma PNG a JPEG le pone fondo negro
    —el canvas de firma es transparente— y el trazo se llena de artefactos.

    Se genera al vuelo. `media_asset` no tiene columna para la ruta de la
    miniatura, asi que cachearla en disco obligaria a una convencion de nombres
    fuera de la base y a acordarse de borrarla junto con el original. Sobre
    imagenes que el cliente ya comprimio a 900px, 96px cuesta poco.
    """
    from PIL import Image

    formato = "PNG" if mime_type == "image/png" else "JPEG"
    try:
        with Image.open(ruta) as imagen:
            imagen.thumbnail((LADO_MINIATURA, LADO_MINIATURA))
            if formato == "JPEG" and imagen.mode not in ("RGB", "L"):
                imagen = imagen.convert("RGB")
            buffer = BytesIO()
            imagen.save(buffer, format=formato)
    except FileNotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise MediaInvalida("No se pudo generar la miniatura.") from exc

    return buffer.getvalue(), mime_type


def borrar_archivo(ruta: str | None) -> None:
    """Best-effort. Que no exista no es un error: puede haberse borrado a mano o
    venir de un respaldo parcial. Lo que no puede pasar es que un fallo de disco
    tumbe la operacion de negocio."""
    if not ruta:
        return
    try:
        Path(ruta).unlink()
    except OSError:
        pass
