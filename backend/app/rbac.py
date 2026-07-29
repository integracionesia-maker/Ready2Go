"""Motor de permisos aditivos (patron Bruckner).

Permisos efectivos = UNION de los paquetes de `[_PISO, users.role, *aditivos]`.

Tres reglas duras, en orden de importancia:

1. **Deny-by-default.** (modulo, accion) que no aparece en ningun paquete del
   usuario = sin permiso. No hay herencia, no hay comodines salvo `superadmin`.
2. **Un paquete aditivo solo abre lo que lista.** Jamas sustituye ni amplia el
   rol base en otro modulo. `APROBADOR_EQUIPO` no concede un solo permiso de
   presupuestos, y hay una prueba que lo afirma por enumeracion.
3. **Fallo al resolver = 503, nunca `{}`.** Un dict vacio produce 403 en todos
   lados y se lee como politica: el cliente desloguea a todo el mundo y el fallo
   real (la base) queda invisible.

De donde sale cada cosa:

- El **contenido** de los paquetes sale de `rbac_catalog.py` (codigo). Una base
  sin migrar no puede producir un conjunto vacio.
- Los **aditivos concedidos** salen de `user_role_grants` (base). Es dato por
  usuario y tiene que aplicar al siguiente request, no al siguiente despliegue.

Cache: por request, nunca por proceso. Un cambio de rol debe verse en el
siguiente request; un cache de proceso lo dejaria pegado hasta reiniciar.
"""

from __future__ import annotations

import os

from fastapi import Depends, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import rbac_catalog
from .database import get_db
from .dependencies import get_current_user
from .errores import PermisosNoDisponibles, SinPermiso
from .models_rbac import Role, UserRoleGrant

__all__ = [
    "PermisosNoDisponibles",
    "modo_rbac",
    "permisos_efectivos",
    "permisos_del_request",
    "tiene_permiso",
    "require_perm",
    "require_cualquiera",
    "MODO_ADITIVO",
    "MODO_LEGACY",
]

MODO_ADITIVO = "aditivo"
MODO_LEGACY = "legacy"

SUPERADMIN = "superadmin"


def modo_rbac() -> str:
    """Se lee en cada llamada, no al importar: `RBAC_MODO=legacy` es el rollback
    de §13 del plan y tiene que poder cambiarse sin reconstruir la imagen.

    En `legacy` las 3 tablas quedan pero **no se consultan**: los permisos salen
    solo de `_PISO` + rol base. Consecuencia que hay que tener presente antes de
    activarlo: los paquetes aditivos dejan de aplicar, asi que la aprobacion de
    equipos queda solo en manos de `superadmin`.
    """
    valor = os.getenv("RBAC_MODO", MODO_ADITIVO).strip().lower()
    return MODO_LEGACY if valor == MODO_LEGACY else MODO_ADITIVO


def _aditivos_concedidos(db: Session, user_id: int) -> list[str]:
    """Paquetes aditivos vigentes del usuario. Un paquete desactivado
    (`roles.is_active = 0`) no cuenta aunque la concesion siga en la tabla: es la
    forma de apagar un paquete sin ir a revocarlo usuario por usuario."""
    filas = (
        db.query(UserRoleGrant.role_name)
        .join(Role, Role.name == UserRoleGrant.role_name)
        .filter(UserRoleGrant.user_id == user_id)
        .filter(Role.is_active.is_(True))
        .all()
    )
    return [fila[0] for fila in filas]


def permisos_efectivos(db: Session, user) -> dict[str, set[str]]:
    """`{modulo: {accion, ...}}` del usuario. Nunca devuelve `{}` por fallo:
    o resuelve, o levanta `PermisosNoDisponibles` (503)."""
    if user is None:
        raise PermisosNoDisponibles("No hay sesion para la que resolver permisos.")

    # superadmin: bypass explicito, ademas de sus filas sembradas. Sigue
    # funcionando aunque la migracion no haya corrido — que es justo cuando hace
    # falta que el superadmin entre a arreglarlo.
    if user.role == SUPERADMIN:
        return rbac_catalog.catalogo_completo()

    piso = rbac_catalog.permisos_de_paquete(rbac_catalog.PISO)
    base = rbac_catalog.permisos_de_paquete(user.role)

    if modo_rbac() == MODO_LEGACY:
        return rbac_catalog.unir(piso, base)

    if db is None:
        raise PermisosNoDisponibles("Sin sesion de base para resolver permisos.")

    try:
        aditivos = _aditivos_concedidos(db, user.id)
    except SQLAlchemyError as exc:
        # Aqui es donde se decide 503 vs 403. Devolver {} seria un 403 masivo
        # que parece politica; el cliente desloguearia y nadie miraria la base.
        raise PermisosNoDisponibles() from exc

    conjuntos = [piso, base]
    for nombre in aditivos:
        conjuntos.append(rbac_catalog.permisos_de_paquete(nombre))

    return rbac_catalog.unir(*conjuntos)


def tiene_permiso(permisos: dict[str, set[str]], modulo: str, accion: str) -> bool:
    return accion in permisos.get(modulo, set())


_CACHE_ATTR = "_rbac_permisos"


def permisos_del_request(request: Request, db: Session, user) -> dict[str, set[str]]:
    """Resuelve una vez por request y reusa. Dos dependencias `require_perm` en
    el mismo endpoint no deben pegarle dos veces a la base."""
    if request is None:
        return permisos_efectivos(db, user)

    cacheado = getattr(request.state, _CACHE_ATTR, None)
    if cacheado is not None:
        usuario_cacheado, permisos = cacheado
        if usuario_cacheado == getattr(user, "id", None):
            return permisos

    permisos = permisos_efectivos(db, user)
    setattr(request.state, _CACHE_ATTR, (getattr(user, "id", None), permisos))
    return permisos


def require_perm(modulo: str, accion: str):
    """Dependencia FastAPI: 403 `SIN_PERMISO` si falta el permiso,
    503 `PERMISOS_NO_DISPONIBLES` si no se pudo resolver.

    Falla temprano en el import si `(modulo, accion)` no existe en el catalogo:
    un typo en el decorador de una ruta produciria un 403 permanente que nadie
    relaciona con el typo.
    """
    if not rbac_catalog.es_permiso_valido(modulo, accion):
        raise ValueError(f"Permiso fuera del catalogo: '{modulo}:{accion}'")

    def _dependencia(
        request: Request,
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        permisos = permisos_del_request(request, db, current_user)
        if not tiene_permiso(permisos, modulo, accion):
            raise SinPermiso()
        return current_user

    return _dependencia


def require_cualquiera(*pares: tuple[str, str]):
    """Igual que `require_perm` pero basta con uno de los pares.

    Lo pide el contrato en rutas como `GET /api/loans/`, donde `ver_propios` y
    `ver_global` abren la misma ruta con distinto alcance. El alcance real
    (filtrar por `responsable_user_id`) lo aplica el endpoint, no esta
    dependencia: aqui solo se decide si pasa o no.
    """
    if not pares:
        raise ValueError("require_cualquiera necesita al menos un par (modulo, accion)")
    for modulo, accion in pares:
        if not rbac_catalog.es_permiso_valido(modulo, accion):
            raise ValueError(f"Permiso fuera del catalogo: '{modulo}:{accion}'")

    def _dependencia(
        request: Request,
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        permisos = permisos_del_request(request, db, current_user)
        if not any(tiene_permiso(permisos, m, a) for m, a in pares):
            raise SinPermiso()
        return current_user

    return _dependencia
