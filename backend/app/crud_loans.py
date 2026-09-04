"""Acceso a datos y reglas de negocio de prestamos.

La maquina de estados vive en `loan_state.py` (pura, sin base). Aqui va lo que
necesita la sesion: leer, serializar y aplicar las transiciones.

Invariante que atraviesa todo el archivo: **la ocupacion de un equipo se decide
solo por `loan_item.devuelto_at IS NULL`**, que es exactamente la condicion del
indice unico parcial. Cualquier operacion que libere un equipo tiene que escribir
`devuelto_at`; si no, el indice bloquea lo que la formula de disponibilidad
muestra libre y el usuario ve disponible algo que da 409 al pedirlo.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import crud_equipment, folio as folio_mod, loan_state, tz
from .models import User
from .models_equipos import (
    DecisionDevolucion,
    Equipment,
    EstadoOperativo,
    EstadoPrestamo,
    KindMedia,
    Loan,
    LoanEvent,
    LoanItem,
    MediaAsset,
    ResponsivaDoc,
    TipoEvento,
)

__all__ = [
    "LIMITE_DEFAULT",
    "LIMITE_MAXIMO",
    "DIRECTORIO_RESPONSIVAS",
    "CAMPOS_PARTICIPACION",
    "obtener",
    "obtener_por_folio",
    "es_participante",
    "puede_ver",
    "calcular_atraso",
    "serializar_detalle",
    "listar",
    "crear",
    "actualizar",
    "agregar_item",
    "quitar_item",
    "confirmar",
    "cancelar",
    "registrar_devolucion",
    "autorizar_entrega",
    "confirmar_devolucion",
    "cerrar_incidencia",
    "registrar_evento",
    "generar_responsiva",
    "faltantes_para_confirmar",
    "faltantes_para_devolucion",
    "firmas_completas",
    "completar_firma_faltante",
    "COLUMNAS_CSV",
    "filas_csv",
]

LIMITE_DEFAULT = 50
LIMITE_MAXIMO = 200

DIRECTORIO_RESPONSIVAS = Path("./uploads/responsivas")

# "Participante" no esta definido en el contrato (§3 y §5 lo usan cuatro veces).
# Esta es la definicion que se adopta, reportada en docs/avances/servidor.md:
# cualquiera cuyo id aparezca en una de estas columnas del prestamo. Es un
# conjunto que CRECE con el tiempo — quien autoriza entra al autorizar.
CAMPOS_PARTICIPACION = (
    "responsable_user_id",
    "entregado_por_user_id",
    "created_by_user_id",
    "entrega_autorizada_por_user_id",
    "confirmada_por_user_id",
)

KINDS_ITEM = (
    KindMedia.FOTO_ENTREGA_FRENTE.value,
    KindMedia.FOTO_ENTREGA_ATRAS.value,
    KindMedia.FOTO_DEV_FRENTE.value,
    KindMedia.FOTO_DEV_ATRAS.value,
)
KINDS_FIRMA = (KindMedia.FIRMA_ENTREGA.value, KindMedia.FIRMA_RESPONSABLE.value)


# ── Lectura ─────────────────────────────────────────────────────────────────


def obtener(db: Session, loan_id: int) -> Loan | None:
    prestamo = db.get(Loan, loan_id)
    if prestamo is None or prestamo.is_deleted:
        return None
    return prestamo


def obtener_por_folio(db: Session, folio: str) -> Loan | None:
    return (
        db.query(Loan)
        .filter(Loan.folio == folio)
        .filter(Loan.is_deleted.is_(False))
        .first()
    )


def es_participante(prestamo: Loan, user_id: int | None) -> bool:
    if user_id is None:
        return False
    return any(getattr(prestamo, campo) == user_id for campo in CAMPOS_PARTICIPACION)


def puede_ver(prestamo: Loan, user_id: int | None, tiene_ver_global: bool) -> bool:
    return tiene_ver_global or es_participante(prestamo, user_id)


def calcular_atraso(prestamo: Loan, referencia: date | None = None) -> tuple[bool, int]:
    """Atraso en dias, calculado en servidor con fecha de CDMX.

    Tres casos, y los dos ultimos no estan en el contrato (reportados):
    - Prestamo vivo: se compara la fecha esperada contra hoy.
    - Prestamo ya devuelto: se compara contra `fecha_regreso_real`. Si no, un
      prestamo cerrado hace tres meses diria "atrasado 90 dias" para siempre.
    - Prestamo terminal sin fecha real: no hay atraso que reportar.
    """
    esperada = prestamo.fecha_regreso_esperada
    if esperada is None:
        return False, 0

    if prestamo.fecha_regreso_real is not None:
        dias = tz.dias_de_atraso(esperada, prestamo.fecha_regreso_real)
        return dias > 0, dias

    if prestamo.estado in loan_state.TERMINALES:
        return False, 0

    dias = tz.dias_de_atraso(esperada, referencia or tz.hoy())
    return dias > 0, dias


def _accesorios(item: LoanItem) -> list[str]:
    if not item.accesorios_seleccionados:
        return []
    try:
        valor = json.loads(item.accesorios_seleccionados)
    except (TypeError, ValueError):
        return []
    return [str(x) for x in valor] if isinstance(valor, list) else []


def _mapa_media(db: Session, loan_id: int) -> tuple[dict[int, dict[str, int]], dict[str, int]]:
    """`({loan_item_id: {kind: media_id}}, {kind: media_id})` en una consulta.

    Se queda con el id mas alto por (renglon, kind) por si quedaran duplicados de
    una version anterior: `media_manager.reemplazar` deja uno solo, pero el
    payload expone un unico id y no puede depender de que la base este limpia.
    """
    por_item: dict[int, dict[str, int]] = {}
    firmas: dict[str, int] = {}

    filas = (
        db.query(MediaAsset.id, MediaAsset.loan_item_id, MediaAsset.kind)
        .filter(MediaAsset.loan_id == loan_id)
        .order_by(MediaAsset.id)
        .all()
    )
    for media_id, loan_item_id, kind in filas:
        if kind in KINDS_FIRMA:
            firmas[kind] = media_id
        elif loan_item_id is not None:
            por_item.setdefault(loan_item_id, {})[kind] = media_id

    return por_item, firmas


def _persona(db: Session, user_id: int | None) -> dict | None:
    if user_id is None:
        return None
    usuario = db.get(User, user_id)
    return {"user_id": user_id, "nombre": usuario.full_name if usuario else None}


def serializar_detalle(db: Session, prestamo: Loan, referencia: date | None = None) -> dict:
    """El payload congelado en `fixtures/prestamo_demo.json`. Ni un campo mas."""
    atrasado, dias = calcular_atraso(prestamo, referencia)
    por_item, firmas = _mapa_media(db, prestamo.id)

    nombres_equipo = dict(
        db.query(LoanItem.id, Equipment.nombre)
        .join(Equipment, Equipment.id == LoanItem.equipment_id)
        .filter(LoanItem.loan_id == prestamo.id)
        .all()
    )

    ultima_responsiva = (
        db.query(ResponsivaDoc)
        .filter(ResponsivaDoc.loan_id == prestamo.id)
        .order_by(ResponsivaDoc.version.desc())
        .first()
    )

    return {
        "id": prestamo.id,
        "folio": prestamo.folio,
        "estado": prestamo.estado,
        "responsable": {
            "user_id": prestamo.responsable_user_id,
            "nombre": prestamo.responsable_nombre,
            "email": prestamo.responsable_email,
        },
        "area": prestamo.area,
        "empresa": prestamo.empresa,
        "motivo": prestamo.motivo,
        "notas_responsiva": prestamo.notas_responsiva,
        "entregado_por": _persona(db, prestamo.entregado_por_user_id),
        "fecha_entrega": prestamo.fecha_entrega,
        "fecha_regreso_esperada": prestamo.fecha_regreso_esperada,
        "fecha_regreso_real": prestamo.fecha_regreso_real,
        "atrasado": atrasado,
        "dias_atraso": dias,
        "entrega_autorizada": bool(prestamo.entrega_autorizada),
        "entrega_autorizada_por": _persona(db, prestamo.entrega_autorizada_por_user_id),
        "fecha_autorizacion_entrega": tz.iso_cdmx(prestamo.fecha_autorizacion_entrega),
        "confirmada_por": _persona(db, prestamo.confirmada_por_user_id),
        "fecha_confirmacion": tz.iso_cdmx(prestamo.fecha_confirmacion),
        "items": [
            {
                "id": item.id,
                "equipment_id": item.equipment_id,
                "equipo_nombre": nombres_equipo.get(item.id),
                "accesorios_seleccionados": _accesorios(item),
                "accesorios_otros": item.accesorios_otros,
                "cargador_con": item.cargador_con,
                "devuelto_at": tz.iso_cdmx(item.devuelto_at),
                "no_devuelto": bool(item.no_devuelto),
                "nota_devolucion": item.nota_devolucion,
                "decision": item.decision,
                "nota_decision": item.nota_decision,
                "media": {
                    kind: por_item.get(item.id, {}).get(kind) for kind in KINDS_ITEM
                },
            }
            for item in prestamo.items
        ],
        "firmas": {kind: firmas.get(kind) for kind in KINDS_FIRMA},
        "responsiva": (
            {
                "version": ultima_responsiva.version,
                "url": f"/api/loans/{prestamo.id}/responsiva.pdf",
            }
            if ultima_responsiva
            else None
        ),
        "eventos": [
            {
                "id": evento.id,
                "tipo": evento.tipo,
                "actor": evento.actor_nombre,
                "detalle": evento.detalle,
                "created_at": tz.iso_cdmx(evento.created_at),
            }
            for evento in prestamo.eventos
        ],
    }


def _equipos_por_prestamo(db: Session, loan_ids: list[int]) -> dict[int, list[str]]:
    if not loan_ids:
        return {}
    salida: dict[int, list[str]] = {}
    for loan_id, nombre in (
        db.query(LoanItem.loan_id, Equipment.nombre)
        .join(Equipment, Equipment.id == LoanItem.equipment_id)
        .filter(LoanItem.loan_id.in_(loan_ids))
        .order_by(LoanItem.id)
        .all()
    ):
        salida.setdefault(loan_id, []).append(nombre)
    return salida


def serializar_fila(
    prestamo: Loan,
    equipos: list[str],
    referencia: date | None = None,
    *,
    firmas_faltantes: frozenset[str] = frozenset(),
) -> dict:
    atrasado, dias = calcular_atraso(prestamo, referencia)
    return {
        "id": prestamo.id,
        "folio": prestamo.folio,
        "estado": prestamo.estado,
        "responsable": {
            "user_id": prestamo.responsable_user_id,
            "nombre": prestamo.responsable_nombre,
            "email": prestamo.responsable_email,
        },
        "area": prestamo.area,
        "empresa": prestamo.empresa,
        "motivo": prestamo.motivo,
        "fecha_entrega": prestamo.fecha_entrega,
        "fecha_regreso_esperada": prestamo.fecha_regreso_esperada,
        "fecha_regreso_real": prestamo.fecha_regreso_real,
        "atrasado": atrasado,
        "dias_atraso": dias,
        "entrega_autorizada": bool(prestamo.entrega_autorizada),
        "firma_entrega_pendiente": KindMedia.FIRMA_ENTREGA.value in firmas_faltantes,
        "firma_responsable_pendiente": KindMedia.FIRMA_RESPONSABLE.value in firmas_faltantes,
        "total_equipos": len(equipos),
        "equipos": equipos,
    }


def listar(
    db: Session,
    *,
    solo_de_user_id: int | None = None,
    estado: str | None = None,
    q: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = LIMITE_DEFAULT,
    offset: int = 0,
) -> tuple[list[Loan], int]:
    """`solo_de_user_id` es el scoping server-side. Se aplica aqui y no en el
    router para que el listado y el CSV no puedan divergir."""
    consulta = db.query(Loan).filter(Loan.is_deleted.is_(False))

    if solo_de_user_id is not None:
        consulta = consulta.filter(Loan.responsable_user_id == solo_de_user_id)
    if estado:
        consulta = consulta.filter(Loan.estado == estado)
    if desde:
        consulta = consulta.filter(Loan.fecha_entrega >= desde)
    if hasta:
        consulta = consulta.filter(Loan.fecha_entrega <= hasta)
    if q:
        patron = f"%{q.strip()}%"
        con_equipo = (
            db.query(LoanItem.loan_id)
            .join(Equipment, Equipment.id == LoanItem.equipment_id)
            .filter(Equipment.nombre.ilike(patron))
        )
        consulta = consulta.filter(
            or_(
                Loan.folio.ilike(patron),
                Loan.responsable_nombre.ilike(patron),
                Loan.motivo.ilike(patron),
                Loan.area.ilike(patron),
                Loan.id.in_(con_equipo),
            )
        )

    total = consulta.with_entities(func.count(Loan.id)).scalar() or 0
    limite = max(1, min(limit, LIMITE_MAXIMO))
    filas = (
        consulta.order_by(Loan.id.desc()).offset(max(0, offset)).limit(limite).all()
    )
    return filas, int(total)


# ── Bitacora ────────────────────────────────────────────────────────────────


def registrar_evento(
    db: Session, prestamo: Loan, tipo: str, detalle: str | None, actor: User | None
) -> LoanEvent:
    """El nombre del actor se copia ademas del id: la bitacora tiene que seguir
    legible si la persona se da de baja (la FK es SET NULL)."""
    evento = LoanEvent(
        loan_id=prestamo.id,
        actor_user_id=actor.id if actor else None,
        actor_nombre=actor.full_name if actor else None,
        tipo=tipo,
        detalle=detalle,
        created_at=tz.ahora_utc_naive(),
    )
    db.add(evento)
    return evento


# ── Alta y edicion del borrador ─────────────────────────────────────────────


def crear(db: Session, datos: dict, actor: User) -> Loan:
    prestamo = Loan(
        estado=EstadoPrestamo.BORRADOR.value,
        folio=None,
        responsable_user_id=datos.get("responsable_user_id") or actor.id,
        responsable_nombre=datos.get("responsable_nombre") or actor.full_name,
        responsable_email=datos.get("responsable_email") or actor.email,
        area=datos.get("area"),
        empresa=datos.get("empresa"),
        motivo=datos.get("motivo"),
        notas_responsiva=datos.get("notas_responsiva"),
        fecha_entrega=datos.get("fecha_entrega"),
        fecha_regreso_esperada=datos.get("fecha_regreso_esperada"),
        created_by_user_id=actor.id,
        entrega_autorizada=False,
    )
    db.add(prestamo)
    db.flush()
    registrar_evento(db, prestamo, TipoEvento.CREADO.value, "Borrador creado.", actor)
    db.commit()
    db.refresh(prestamo)
    return prestamo


def actualizar(db: Session, prestamo: Loan, cambios: dict) -> Loan:
    for campo, valor in cambios.items():
        setattr(prestamo, campo, valor)
    db.commit()
    db.refresh(prestamo)
    return prestamo


def agregar_item(db: Session, prestamo: Loan, datos: dict, actor: User, equipo: Equipment) -> LoanItem:
    item = LoanItem(
        loan_id=prestamo.id,
        equipment_id=equipo.id,
        accesorios_seleccionados=crud_equipment.serializar_accesorios(
            datos.get("accesorios_seleccionados") or []
        ),
        accesorios_otros=datos.get("accesorios_otros"),
        cargador_con=datos.get("cargador_con"),
    )
    db.add(item)
    db.flush()
    registrar_evento(
        db, prestamo, TipoEvento.ITEM_AGREGADO.value, f"Equipo agregado: {equipo.nombre}", actor
    )
    return item


def quitar_item(db: Session, prestamo: Loan, item: LoanItem, actor: User) -> None:
    """Borrado fisico de la fila: el equipo queda libre de inmediato porque
    desaparece el renglon que el indice unico mira."""
    nombre = item.equipo.nombre if item.equipo else str(item.equipment_id)
    for media in list(item.media):
        from . import media_manager

        media_manager.borrar_archivo(media.file_path)
        db.delete(media)
    db.delete(item)
    registrar_evento(
        db, prestamo, TipoEvento.ITEM_QUITADO.value, f"Equipo quitado: {nombre}", actor
    )
    db.commit()


# ── Validaciones de completitud ─────────────────────────────────────────────


def faltantes_para_confirmar(db: Session, prestamo: Loan) -> list[str]:
    """Que le falta al borrador para poder confirmarse.

    Se cuentan **kinds distintos**, no filas: con un `COUNT(*) = 2` un renglon
    con dos `foto_entrega_frente` y cero `foto_entrega_atras` pasaria la
    validacion. El indice de media no es unico, asi que la base lo permite.
    """
    faltas: list[str] = []

    if not prestamo.items:
        faltas.append("Selecciona al menos un equipo.")
        return faltas

    por_item, _ = _mapa_media(db, prestamo.id)

    sin_frente = 0
    sin_atras = 0
    for item in prestamo.items:
        presentes = por_item.get(item.id, {})
        if KindMedia.FOTO_ENTREGA_FRENTE.value not in presentes:
            sin_frente += 1
        if KindMedia.FOTO_ENTREGA_ATRAS.value not in presentes:
            sin_atras += 1

    if sin_frente:
        faltas.append(f"Faltan las fotos de frente de {sin_frente} equipo.")
    if sin_atras:
        faltas.append(f"Faltan las fotos de atras de {sin_atras} equipo.")

    # `confirmar` NUNCA exige ninguna firma (decision explicita del usuario,
    # revision 2): quien llena el formulario no es necesariamente ni quien
    # aprueba (Melisa/APROBADOR_EQUIPO) ni el beneficiario (quien recibe el
    # equipo). Las dos se completan despues, cada una por su lado, con el
    # prestamo ya confirmado (ver `acepta_media`, `completar_firma_faltante`
    # y la guarda `firmas_completas` que bloquea llegar a `completado`).

    return faltas


def firmas_completas(db: Session, loan_id: int) -> bool:
    """Ambas firmas presentes — la de quien entrega y la del responsable.

    Se deriva de `media_asset`, igual que el resto del modulo deriva la
    disponibilidad de equipo de `loan_item`: no hay una columna
    `loan.firmas_completas` que pueda desincronizarse de la fila real.
    """
    _, firmas = _mapa_media(db, loan_id)
    return all(kind in firmas for kind in KINDS_FIRMA)


def _firmas_faltantes_por_prestamo(db: Session, loan_ids: list[int]) -> dict[int, set[str]]:
    """Version por lote de `firmas_completas`, para el listado — evita una
    consulta por fila (mismo patron que `_equipos_por_prestamo`).

    Devuelve, por prestamo, el conjunto de *kinds* de firma que TODAVIA
    faltan (nunca los presentes) — granular a proposito: el listado necesita
    distinguir "falta la del aprobador" de "falta la del beneficiario" para
    la cola de Aprobaciones y para el badge de cada fila.
    """
    if not loan_ids:
        return {}
    presentes: dict[int, set[str]] = {}
    for loan_id, kind in (
        db.query(MediaAsset.loan_id, MediaAsset.kind)
        .filter(MediaAsset.loan_id.in_(loan_ids), MediaAsset.kind.in_(KINDS_FIRMA))
        .distinct()
        .all()
    ):
        presentes.setdefault(loan_id, set()).add(kind)
    todas = set(KINDS_FIRMA)
    return {loan_id: todas - presentes.get(loan_id, set()) for loan_id in loan_ids}


def faltantes_para_devolucion(
    db: Session, prestamo: Loan, por_item: dict[int, dict], declarados: dict[int, dict]
) -> list[str]:
    """Por cada equipo: dos fotos de devolucion, **o** `no_devuelto` con nota."""
    faltas: list[str] = []
    nombres = dict(
        db.query(LoanItem.id, Equipment.nombre)
        .join(Equipment, Equipment.id == LoanItem.equipment_id)
        .filter(LoanItem.loan_id == prestamo.id)
        .all()
    )

    for item in prestamo.items:
        declarado = declarados.get(item.id, {})
        nombre = nombres.get(item.id, str(item.equipment_id))

        if declarado.get("no_devuelto"):
            if not (declarado.get("nota_devolucion") or "").strip():
                faltas.append(f"Agrega una nota para el equipo no devuelto: {nombre}")
            continue

        presentes = por_item.get(item.id, {})
        if (
            KindMedia.FOTO_DEV_FRENTE.value not in presentes
            or KindMedia.FOTO_DEV_ATRAS.value not in presentes
        ):
            faltas.append(f"Faltan fotos de devolucion (frente y atras) de: {nombre}")

    return faltas


# ── Transiciones ────────────────────────────────────────────────────────────


def generar_responsiva(
    db: Session, prestamo: Loan, actor: User | None, motivo: str | None = None
) -> ResponsivaDoc:
    """Crea la siguiente version de la carta responsiva. **Nunca sobrescribe.**

    El generador de PDF llega en S5. Mientras no exista, se registra la version
    con su ruta prevista y sin archivo: el payload de `GET /api/loans/{id}` solo
    expone `version` y `url`, asi que el contrato se cumple igual y la version 2
    sigue sin poder pisar a la 1.
    """
    ultima = (
        db.query(func.max(ResponsivaDoc.version))
        .filter(ResponsivaDoc.loan_id == prestamo.id)
        .scalar()
    )
    version = (ultima or 0) + 1

    DIRECTORIO_RESPONSIVAS.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_RESPONSIVAS / f"{prestamo.folio or f'BORRADOR-{prestamo.id}'}_v{version}.pdf"

    sha = None
    try:
        from .pdf import responsiva as generador
    except ImportError:
        generador = None
    if generador is not None:
        sha = generador.generar_a_disco(db, prestamo, destino)

    documento = ResponsivaDoc(
        loan_id=prestamo.id,
        version=version,
        file_path=str(destino),
        sha256=sha,
        generated_by_user_id=actor.id if actor else None,
        generated_at=tz.ahora_utc_naive(),
        motivo_regeneracion=motivo,
    )
    db.add(documento)
    db.flush()
    registrar_evento(
        db,
        prestamo,
        TipoEvento.RESPONSIVA_GENERADA.value,
        f"Carta responsiva version {version} generada.",
        actor,
    )
    return documento


def completar_firma_faltante(db: Session, prestamo: Loan, actor: User) -> ResponsivaDoc:
    """Se llama cuando la segunda de las dos firmas (aprobador + beneficiario)
    por fin se sube, con el prestamo ya confirmado (`prestado`,
    `pendiente_confirmacion` o `incompleto`). La v1 de la responsiva quedo con
    ambas firmas en blanco — nunca se piden al confirmar, ver §1b de
    loan_state.py — y esta genera la siguiente version, ya completa. Nunca pisa
    la v1: es la misma regla de `generar_responsiva`, "un documento firmado es
    evidencia".

    El router es quien decide CUANDO llamar a esto (justo despues de subir una
    firma que deja `firmas_completas` en True) y quien encola el correo de
    aviso — aqui solo se muta el prestamo.
    """
    registrar_evento(
        db,
        prestamo,
        TipoEvento.FIRMA_COMPLETADA.value,
        "Firma pendiente completada. Carta responsiva actualizada.",
        actor,
    )
    documento = generar_responsiva(db, prestamo, actor, motivo="Firma pendiente completada.")
    db.commit()
    db.refresh(prestamo)
    return documento


def confirmar(db: Session, prestamo: Loan, actor: User) -> Loan:
    """`borrador -> prestado`. Asigna folio y genera la responsiva v1.

    No escribe `devuelto_at`: los renglones quedan abiertos, y eso es justo lo
    que mantiene los equipos reservados.
    """
    prestamo.estado = EstadoPrestamo.PRESTADO.value
    if prestamo.fecha_entrega is None:
        prestamo.fecha_entrega = tz.hoy()
    folio_mod.asignar_folio(db, prestamo)

    registrar_evento(
        db,
        prestamo,
        TipoEvento.CONFIRMADO.value,
        "Prestamo confirmado. Pendiente la firma del aprobador y la del beneficiario.",
        actor,
    )
    generar_responsiva(db, prestamo, actor)

    db.commit()
    db.refresh(prestamo)
    return prestamo


def cancelar(db: Session, prestamo: Loan, actor: User, motivo: str | None) -> Loan:
    """`borrador -> cancelado`. **Libera los equipos escribiendo `devuelto_at`.**

    Sin esa escritura el indice unico parcial seguiria bloqueando cada equipo del
    borrador cancelado mientras la formula de disponibilidad los muestra libres.
    """
    prestamo.estado = EstadoPrestamo.CANCELADO.value
    ahora = tz.ahora_utc_naive()
    for item in prestamo.items:
        if item.devuelto_at is None:
            item.devuelto_at = ahora

    registrar_evento(
        db,
        prestamo,
        TipoEvento.CANCELADO.value,
        f"Prestamo cancelado.{f' Motivo: {motivo}' if motivo else ''}",
        actor,
    )
    db.commit()
    db.refresh(prestamo)
    return prestamo


def registrar_devolucion(
    db: Session, prestamo: Loan, declarados: dict[int, dict], fecha_real: date | None, actor: User
) -> Loan:
    """`prestado -> pendiente_confirmacion`.

    **No escribe `devuelto_at`.** El equipo sigue ocupado hasta que el aprobador
    lo revise: si se liberara aqui, se ofreceria como disponible antes de que
    nadie mirara las fotos, y un equipo marcado `no_devuelto` (perdido) volveria
    a ser prestable.
    """
    prestamo.estado = EstadoPrestamo.PENDIENTE_CONFIRMACION.value
    prestamo.fecha_regreso_real = fecha_real or tz.hoy()

    for item in prestamo.items:
        declarado = declarados.get(item.id, {})
        item.no_devuelto = bool(declarado.get("no_devuelto"))
        item.nota_devolucion = declarado.get("nota_devolucion")

    registrar_evento(
        db,
        prestamo,
        TipoEvento.DEVOLUCION_REGISTRADA.value,
        f"Devolucion registrada por {actor.full_name}. En espera de confirmacion.",
        actor,
    )
    db.commit()
    db.refresh(prestamo)
    return prestamo


def autorizar_entrega(db: Session, prestamo: Loan, actor: User) -> Loan:
    """Ortogonal al estado: no lo cambia. Idempotente: autorizar dos veces no
    reescribe quien autorizo ni cuando, ni duplica el evento en la bitacora."""
    if prestamo.entrega_autorizada:
        return prestamo

    prestamo.entrega_autorizada = True
    prestamo.entrega_autorizada_por_user_id = actor.id
    prestamo.fecha_autorizacion_entrega = tz.ahora_utc_naive()

    registrar_evento(
        db,
        prestamo,
        TipoEvento.ENTREGA_AUTORIZADA.value,
        f"Carta responsiva autorizada por {actor.full_name}. Entrega cerrada.",
        actor,
    )
    db.commit()
    db.refresh(prestamo)
    return prestamo


def confirmar_devolucion(
    db: Session, prestamo: Loan, decisiones: dict[int, dict], destino: str, actor: User
) -> Loan:
    """`pendiente_confirmacion -> completado | incompleto`.

    Escribe `devuelto_at` en **todos** los renglones, incluidos los danados y los
    faltantes: el renglon del prestamo se cierra. Lo que mantiene fuera de
    circulacion a un equipo con incidencia es `estado_operativo='revision'`, no el
    renglon abierto. Si se dejara abierto, `cerrar-incidencia` devolveria el
    equipo a `activo` mientras el indice lo sigue bloqueando.
    """
    ahora = tz.ahora_utc_naive()
    con_incidencia = 0

    for item in prestamo.items:
        decidido = decisiones.get(item.id, {})
        item.decision = decidido.get("decision")
        item.nota_decision = decidido.get("nota")
        if item.devuelto_at is None:
            item.devuelto_at = ahora

        if item.decision != DecisionDevolucion.OK.value:
            con_incidencia += 1
            if item.equipo is not None:
                item.equipo.estado_operativo = EstadoOperativo.REVISION.value

    prestamo.estado = destino
    prestamo.confirmada_por_user_id = actor.id
    prestamo.fecha_confirmacion = ahora

    resultado = "incidencias reportadas" if con_incidencia else "todo en buen estado"
    registrar_evento(
        db,
        prestamo,
        TipoEvento.DEVOLUCION_CONFIRMADA.value,
        f"Entrega confirmada por {actor.full_name}. Resultado: {resultado}.",
        actor,
    )
    db.commit()
    db.refresh(prestamo)
    return prestamo


def cerrar_incidencia(db: Session, prestamo: Loan, nota: str, actor: User) -> Loan:
    """`incompleto -> completado`. Devuelve a `activo` los equipos de ESTE
    prestamo que quedaron con incidencia.

    Solo los de este prestamo: hacerlo por equipo podria sacar de `revision` uno
    que quedo asi por otro prestamo o por una auditoria de condicion.
    """
    devueltos: list[str] = []
    for item in prestamo.items:
        if item.decision and item.decision != DecisionDevolucion.OK.value and item.equipo:
            item.equipo.estado_operativo = EstadoOperativo.ACTIVO.value
            devueltos.append(item.equipo.nombre)

    prestamo.estado = EstadoPrestamo.COMPLETADO.value

    detalle = f"Incidencia cerrada por {actor.full_name}. {nota}"
    if devueltos:
        detalle += f" Equipos devueltos a servicio: {', '.join(devueltos)}."
    registrar_evento(db, prestamo, TipoEvento.INCIDENCIA_CERRADA.value, detalle, actor)

    db.commit()
    db.refresh(prestamo)
    return prestamo


# ── Exportacion ─────────────────────────────────────────────────────────────

# El contrato no define columnas del CSV (§3 solo dice "CSV"). Estas salen del
# export de la maqueta, ampliadas con lo que el modelo si tiene. Reportado.
COLUMNAS_CSV = [
    "folio",
    "estado",
    "responsable",
    "correo_responsable",
    "area",
    "empresa",
    "motivo",
    "equipos",
    "fecha_entrega",
    "fecha_regreso_esperada",
    "fecha_regreso_real",
    "atrasado",
    "dias_atraso",
    "entrega_autorizada",
    "autorizada_por",
    "confirmada_por",
    "fecha_confirmacion",
    "notas_incidencias",
]


def filas_csv(db: Session, prestamos: list[Loan]) -> list[list[str]]:
    equipos = _equipos_por_prestamo(db, [p.id for p in prestamos])
    filas: list[list[str]] = []

    for prestamo in prestamos:
        atrasado, dias = calcular_atraso(prestamo)
        autorizada_por = _persona(db, prestamo.entrega_autorizada_por_user_id)
        confirmada_por = _persona(db, prestamo.confirmada_por_user_id)
        incidencias = [
            item.nota_decision
            for item in prestamo.items
            if item.decision and item.decision != DecisionDevolucion.OK.value and item.nota_decision
        ]
        filas.append(
            [
                prestamo.folio or "",
                prestamo.estado,
                prestamo.responsable_nombre or "",
                prestamo.responsable_email or "",
                prestamo.area or "",
                prestamo.empresa or "",
                prestamo.motivo or "",
                " | ".join(equipos.get(prestamo.id, [])),
                tz.iso_fecha(prestamo.fecha_entrega) or "",
                tz.iso_fecha(prestamo.fecha_regreso_esperada) or "",
                tz.iso_fecha(prestamo.fecha_regreso_real) or "",
                "si" if atrasado else "no",
                str(dias),
                "si" if prestamo.entrega_autorizada else "no",
                (autorizada_por or {}).get("nombre") or "",
                (confirmada_por or {}).get("nombre") or "",
                tz.iso_cdmx(prestamo.fecha_confirmacion) or "",
                " | ".join(incidencias),
            ]
        )
    return filas
