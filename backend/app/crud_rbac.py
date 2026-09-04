"""Acceso a datos del RBAC aditivo: catalogo materializado y concesiones.

`usuarios_con_permiso()` es la pieza que evita el hardcode de destinatarios:
§7 del plan exige que los correos de aprobacion salgan de la base por rol, no de
una constante con `melisa.avendano@grupo-ortiz.com` adentro. Si Melisa cambia de
puesto se revoca el aditivo y ya.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import rbac, rbac_catalog
from .models import User
from .models_rbac import Role, RolePermission, UserRoleGrant


# ── Catalogo materializado ──────────────────────────────────────────────────


def listar_roles(db: Session, *, solo_activos: bool = False) -> list[Role]:
    query = db.query(Role)
    if solo_activos:
        query = query.filter(Role.is_active.is_(True))
    return query.order_by(Role.kind, Role.name).all()


def obtener_rol(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).first()


def sembrar_catalogo(db: Session) -> dict[str, int]:
    """Materializa `rbac_catalog.py` en `roles` + `role_permissions`.

    Idempotente y **reconciliadora**: inserta lo que falta, actualiza kind y
    descripcion, y borra las filas de permiso que ya no estan en el catalogo. Sin
    el borrado, quitar una accion del catalogo dejaria la fila viva en la base y
    un dia alguien la leeria como permiso vigente.

    No toca `is_active` de un rol existente: apagar un paquete es una decision
    de operacion, no del codigo, y re-sembrar no debe revivirlo.
    No toca ninguna fila de `users` ni de `user_role_grants`.
    """
    errores = rbac_catalog.validar_catalogo()
    if errores:
        raise ValueError("Catalogo de permisos invalido: " + "; ".join(errores))

    conteo = {"roles_nuevos": 0, "roles_actualizados": 0, "permisos_nuevos": 0, "permisos_borrados": 0}

    existentes = {rol.name: rol for rol in db.query(Role).all()}

    for nombre in rbac_catalog.PAQUETES:
        kind = rbac_catalog.kind_de(nombre)
        descripcion = rbac_catalog.descripcion_de(nombre)
        rol = existentes.get(nombre)
        if rol is None:
            db.add(Role(name=nombre, kind=kind, descripcion=descripcion, is_active=True))
            conteo["roles_nuevos"] += 1
        elif rol.kind != kind or rol.descripcion != descripcion:
            rol.kind = kind
            rol.descripcion = descripcion
            conteo["roles_actualizados"] += 1

    db.flush()

    deseados: set[tuple[str, str, str]] = set()
    for nombre in rbac_catalog.PAQUETES:
        for modulo, acciones in rbac_catalog.permisos_de_paquete(nombre).items():
            for accion in acciones:
                deseados.add((nombre, modulo, accion))

    actuales = {
        (fila.role_name, fila.modulo, fila.accion) for fila in db.query(RolePermission).all()
    }

    for role_name, modulo, accion in sorted(deseados - actuales):
        db.add(RolePermission(role_name=role_name, modulo=modulo, accion=accion))
        conteo["permisos_nuevos"] += 1

    for role_name, modulo, accion in sorted(actuales - deseados):
        db.query(RolePermission).filter(
            RolePermission.role_name == role_name,
            RolePermission.modulo == modulo,
            RolePermission.accion == accion,
        ).delete(synchronize_session=False)
        conteo["permisos_borrados"] += 1

    db.commit()
    return conteo


def catalogo_en_db(db: Session) -> dict[str, dict[str, set[str]]]:
    """Lo que hay sembrado, en la misma forma que el catalogo en codigo. Lo usa
    la prueba que compara materializacion contra fuente de verdad."""
    salida: dict[str, dict[str, set[str]]] = {}
    for fila in db.query(RolePermission).all():
        salida.setdefault(fila.role_name, {}).setdefault(fila.modulo, set()).add(fila.accion)
    return salida


# ── Concesiones ─────────────────────────────────────────────────────────────


def listar_grants(db: Session, user_id: int) -> list[UserRoleGrant]:
    return (
        db.query(UserRoleGrant)
        .filter(UserRoleGrant.user_id == user_id)
        .order_by(UserRoleGrant.role_name)
        .all()
    )


def tiene_grant(db: Session, user_id: int, role_name: str) -> bool:
    return (
        db.query(UserRoleGrant)
        .filter(UserRoleGrant.user_id == user_id, UserRoleGrant.role_name == role_name)
        .first()
        is not None
    )


def conceder(db: Session, user_id: int, role_name: str, granted_by: int | None) -> UserRoleGrant:
    """Concede un aditivo. Idempotente: conceder dos veces no duplica ni falla.

    Si el paquete es singleton (`rbac_catalog.es_singleton`), se revoca de
    cualquier otro usuario que lo tuviera antes de conceder — un solo titular a
    la vez, sin dejar dos filas vivas para el mismo paquete singleton.
    """
    existente = (
        db.query(UserRoleGrant)
        .filter(UserRoleGrant.user_id == user_id, UserRoleGrant.role_name == role_name)
        .first()
    )
    if existente:
        return existente

    if rbac_catalog.es_singleton(role_name):
        db.query(UserRoleGrant).filter(
            UserRoleGrant.role_name == role_name, UserRoleGrant.user_id != user_id
        ).delete(synchronize_session=False)

    grant = UserRoleGrant(
        user_id=user_id,
        role_name=role_name,
        granted_by=granted_by,
        granted_at=datetime.now(timezone.utc),
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def titular_de(db: Session, role_name: str) -> User | None:
    """Quien tiene un paquete singleton ahora mismo, o None si nadie.

    No valida que `role_name` sea singleton: es una consulta generica de "quien
    tiene este paquete, si acaso uno solo" — `conceder()` es quien garantiza la
    unicidad al escribir.
    """
    grant = db.query(UserRoleGrant).filter(UserRoleGrant.role_name == role_name).first()
    if not grant:
        return None
    return db.get(User, grant.user_id)


def titular_firma_equipo(db: Session) -> User | None:
    """Quien tiene hoy el paquete `TITULAR_FIRMA_EQUIPO`, o None si nadie.

    Lo usa `pdf/responsiva.py` para rellenar el nombre por default del
    aprobador mientras nadie haya firmado todavia (ver docstring del paquete
    en `rbac_catalog.py`)."""
    return titular_de(db, rbac_catalog.TITULAR_FIRMA_EQUIPO)


def revocar(db: Session, user_id: int, role_name: str) -> bool:
    """True si habia algo que revocar. False = no tenia ese paquete."""
    borradas = (
        db.query(UserRoleGrant)
        .filter(UserRoleGrant.user_id == user_id, UserRoleGrant.role_name == role_name)
        .delete(synchronize_session=False)
    )
    db.commit()
    return borradas > 0


# ── Consulta inversa: quien puede hacer que ─────────────────────────────────


def usuarios_con_permiso(
    db: Session,
    modulo: str,
    accion: str,
    *,
    incluir_superadmin: bool = True,
    solo_activos: bool = True,
) -> list[User]:
    """Usuarios que tienen `(modulo, accion)` ahora mismo.

    `incluir_superadmin=False` para destinatarios de correo: el superadmin tiene
    todos los permisos por bypass, pero mandarle cada aviso de prestamo lo
    convierte en ruido. Para una pregunta de autorizacion ("quien puede hacer
    esto") el default correcto es incluirlo.
    """
    paquetes = rbac_catalog.paquetes_que_conceden(modulo, accion)

    if not incluir_superadmin:
        paquetes.discard(rbac.SUPERADMIN)

    query = db.query(User)
    if solo_activos:
        query = query.filter(User.is_active.is_(True))

    # El piso lo tiene cualquier sesion: no hace falta mirar roles.
    if rbac_catalog.PISO in paquetes:
        return query.order_by(User.id).all()

    bases = {n for n in paquetes if rbac_catalog.kind_de(n) == rbac_catalog.KIND_BASE}
    aditivos = {n for n in paquetes if rbac_catalog.kind_de(n) == rbac_catalog.KIND_ADITIVO}

    # En modo legacy las 3 tablas no se consultan, asi que los aditivos no
    # conceden nada y esta respuesta tiene que reflejar lo mismo que el motor.
    if rbac.modo_rbac() == rbac.MODO_LEGACY:
        aditivos = set()

    if not bases and not aditivos:
        return []

    condiciones = []
    if bases:
        condiciones.append(User.role.in_(sorted(bases)))
    if aditivos:
        con_grant = (
            db.query(UserRoleGrant.user_id)
            .join(Role, Role.name == UserRoleGrant.role_name)
            .filter(UserRoleGrant.role_name.in_(sorted(aditivos)))
            .filter(Role.is_active.is_(True))
        )
        condiciones.append(User.id.in_(con_grant))

    from sqlalchemy import or_

    return query.filter(or_(*condiciones)).order_by(User.id).all()
