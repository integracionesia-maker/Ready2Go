"""Set efectivo de permisos, enumerado combinacion por combinacion.

Los conjuntos por paquete estan escritos a mano aqui a proposito. Derivarlos de
`rbac_catalog.py` haria la prueba tautologica: cualquier cambio al catalogo se
volveria automaticamente "correcto". Escritos a mano, cambiar el catalogo pone
esta prueba en rojo y obliga a decidir si el cambio era intencional.
"""

import itertools

import pytest

from app import rbac, rbac_catalog

from .conftest import usuario_con

# ── Verdad escrita a mano (espejo del contrato, NO derivada del codigo) ─────

PISO = {
    "inicio": {"ver"},
    "perfil": {"ver", "editar_propio"},
}

BASE = {
    "superadmin": "TODO",
    "admin": {
        "presupuestos": {
            "ver_global",
            "ver_propio",
            "subir_ticket",
            "validar_ticket",
            "borrar_ticket",
            "gestionar_ciclos",
            "gastos_generales",
            "exportar",
        },
        "equipos_inventario": {"ver"},
        "equipos_prestamos": {
            "solicitar",
            "ver_propios",
            "ver_global",
            "registrar_devolucion",
            "exportar",
        },
    },
    "creador": {
        "presupuestos": {"ver_propio", "subir_ticket"},
    },
    "colaborador_mkt": {
        "equipos_inventario": {"ver"},
        "equipos_prestamos": {"solicitar", "ver_propios", "registrar_devolucion"},
    },
}

ADITIVO = {
    "APROBADOR_EQUIPO": {
        "equipos_aprobacion": {"autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"},
        "equipos_prestamos": {"ver_global"},
    },
    "CUSTODIO_EQUIPO": {
        "equipos_inventario": {"crear", "editar", "auditar_condicion", "dar_de_baja"},
        "equipos_prestamos": {"ver_global"},
    },
    "AUDITOR": {
        "presupuestos": {"ver_global"},
        "equipos_inventario": {"ver"},
        "equipos_prestamos": {"ver_global"},
    },
}

TODO_EL_CATALOGO = {
    "inicio": {"ver"},
    "perfil": {"ver", "editar_propio"},
    "presupuestos": {
        "ver_global",
        "ver_propio",
        "subir_ticket",
        "validar_ticket",
        "borrar_ticket",
        "gestionar_ciclos",
        "gastos_generales",
        "exportar",
    },
    "equipos_inventario": {"ver", "crear", "editar", "auditar_condicion", "dar_de_baja"},
    "equipos_prestamos": {
        "solicitar",
        "ver_propios",
        "ver_global",
        "registrar_devolucion",
        "cancelar",
        "exportar",
    },
    "equipos_aprobacion": {"autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"},
    "usuarios": {"gestionar", "gestionar_roles"},
    "auditoria": {"ver"},
}


def esperado(role_base: str, aditivos: tuple[str, ...]) -> dict[str, set[str]]:
    if BASE[role_base] == "TODO":
        return {m: set(a) for m, a in TODO_EL_CATALOGO.items()}
    acumulado: dict[str, set[str]] = {}
    for parcial in (PISO, BASE[role_base], *[ADITIVO[n] for n in aditivos]):
        for modulo, acciones in parcial.items():
            acumulado.setdefault(modulo, set()).update(acciones)
    return acumulado


def subconjuntos_de_aditivos():
    nombres = ("APROBADOR_EQUIPO", "CUSTODIO_EQUIPO", "AUDITOR")
    for tamano in range(len(nombres) + 1):
        for combo in itertools.combinations(nombres, tamano):
            yield combo


COMBINACIONES = [
    (base, aditivos)
    for base in ("superadmin", "admin", "creador", "colaborador_mkt")
    for aditivos in subconjuntos_de_aditivos()
]


@pytest.mark.parametrize("role_base,aditivos", COMBINACIONES)
def test_set_efectivo_de_cada_combinacion(db, catalogo, role_base, aditivos):
    """4 roles base x 8 subconjuntos de aditivos = 32 combinaciones, una por una."""
    nombre = f"u.{role_base}." + ("-".join(a.lower() for a in aditivos) or "solo")
    user = usuario_con(db, username=nombre, role=role_base, aditivos=aditivos)

    obtenido = rbac.permisos_efectivos(db, user)

    assert obtenido == esperado(role_base, aditivos), (
        f"combinacion {role_base} + {aditivos or '()'}"
    )


def test_aprobador_no_abre_ni_un_permiso_de_presupuestos(db, catalogo):
    """Regla dura del plan §3.4. Afirmada por enumeracion, no por leer codigo."""
    base = rbac.permisos_efectivos(
        db, usuario_con(db, username="sin.aditivo", role="colaborador_mkt")
    )
    con_aprobador = rbac.permisos_efectivos(
        db,
        usuario_con(
            db, username="con.aditivo", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",)
        ),
    )

    assert "presupuestos" not in con_aprobador
    for accion in rbac_catalog.MODULOS["presupuestos"]:
        assert not rbac.tiene_permiso(con_aprobador, "presupuestos", accion), accion

    # Y lo unico que agrega respecto del rol base es lo que declara su paquete.
    agregado = {
        modulo: con_aprobador[modulo] - base.get(modulo, set())
        for modulo in con_aprobador
        if con_aprobador[modulo] - base.get(modulo, set())
    }
    assert agregado == ADITIVO["APROBADOR_EQUIPO"]


def test_aditivo_sobre_creador_no_toca_su_modulo_base(db, catalogo):
    """Un aditivo de equipos sobre un creador no le amplia presupuestos."""
    solo = rbac.permisos_efectivos(db, usuario_con(db, username="c1", role="creador"))
    con = rbac.permisos_efectivos(
        db, usuario_con(db, username="c2", role="creador", aditivos=("CUSTODIO_EQUIPO",))
    )
    assert solo["presupuestos"] == con["presupuestos"]


def test_deny_by_default_rol_desconocido_solo_recibe_el_piso(db, catalogo):
    """Un `users.role` con basura no abre nada: solo el piso. Sin excepcion, sin
    permiso heredado, sin log ruidoso."""
    user = usuario_con(db, username="raro", role="rol_que_no_existe")
    assert rbac.permisos_efectivos(db, user) == {m: set(a) for m, a in PISO.items()}


def test_superadmin_resuelve_sin_catalogo_sembrado(db):
    """Sin `catalogo`: tablas vacias. El superadmin tiene que entrar igual — es
    justo cuando hace falta que entre a arreglar la siembra."""
    user = usuario_con(db, username="root", role="superadmin")
    assert rbac.permisos_efectivos(db, user) == {
        m: set(a) for m, a in TODO_EL_CATALOGO.items()
    }


def test_paquete_desactivado_deja_de_conceder(db, catalogo):
    """Apagar `roles.is_active` revoca el paquete para todos sin ir usuario por
    usuario."""
    from app.models_rbac import Role

    user = usuario_con(
        db, username="mel", role="colaborador_mkt", aditivos=("APROBADOR_EQUIPO",)
    )
    assert "equipos_aprobacion" in rbac.permisos_efectivos(db, user)

    db.query(Role).filter(Role.name == "APROBADOR_EQUIPO").update({"is_active": False})
    db.commit()

    assert "equipos_aprobacion" not in rbac.permisos_efectivos(db, user)


def test_grant_aplica_al_siguiente_request_no_al_siguiente_reinicio(db, catalogo):
    """El cache es por request. Conceder y volver a resolver ve el cambio."""
    from app import crud_rbac

    user = usuario_con(db, username="tarde", role="colaborador_mkt")
    assert "equipos_aprobacion" not in rbac.permisos_efectivos(db, user)

    crud_rbac.conceder(db, user.id, "APROBADOR_EQUIPO", granted_by=None)
    assert "equipos_aprobacion" in rbac.permisos_efectivos(db, user)


def test_usuario_none_no_devuelve_dict_vacio(db, catalogo):
    from app.errores import PermisosNoDisponibles

    with pytest.raises(PermisosNoDisponibles):
        rbac.permisos_efectivos(db, None)
