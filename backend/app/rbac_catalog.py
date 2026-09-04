"""Catalogo unico de modulos, acciones y paquetes de permisos.

Fuente de verdad del **contenido** de cada paquete. Las tablas `roles` y
`role_permissions` son la materializacion en base de datos de este archivo, no
al reves: `migrate_rbac_aditivo.py` las siembra desde aqui y las reconcilia en
cada corrida.

Por que el codigo manda y no la tabla: una base sin migrar o a medio sembrar
devolveria un conjunto de permisos vacio, y un dict vacio es un 403 masivo que
se lee como politica (leccion Bruckner, §10.6 del plan). Con el catalogo en
codigo, lo unico que se consulta en caliente es `user_role_grants` — dato por
usuario que si tiene que vivir en la base para que un cambio aplique al
siguiente request.

Espejo obligatorio: `docs/contratos/permisos_catalogo.json`. Ese archivo es
contrato congelado; hay una prueba que compara los dos y se pone roja si
divergen. Renombrar una accion aqui sin cambiarla alla hace que la interfaz
esconda botones en silencio, sin error visible.
"""

from __future__ import annotations

# ── Modulos y sus acciones ──────────────────────────────────────────────────

MODULOS: dict[str, tuple[str, ...]] = {
    "inicio": ("ver",),
    "perfil": ("ver", "editar_propio"),
    "presupuestos": (
        "ver_global",
        "ver_propio",
        "subir_ticket",
        "validar_ticket",
        "borrar_ticket",
        "gestionar_ciclos",
        "gastos_generales",
        "exportar",
    ),
    "equipos_inventario": ("ver", "crear", "editar", "auditar_condicion", "dar_de_baja"),
    "equipos_prestamos": (
        "solicitar",
        "ver_propios",
        "ver_global",
        "registrar_devolucion",
        "cancelar",
        "exportar",
    ),
    "equipos_aprobacion": ("autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"),
    "usuarios": ("gestionar", "gestionar_roles"),
    "auditoria": ("ver",),
}

# ── Paquetes ────────────────────────────────────────────────────────────────

PISO = "_PISO"
COMODIN_TODO = "*"

KIND_PISO = "piso"
KIND_BASE = "base"
KIND_ADITIVO = "aditivo"

# Paquete singleton (ver `es_singleton`): el nombre vive en una constante para
# que `crud_rbac.titular_firma_equipo()` y `pdf/responsiva.py` no repitan el
# literal.
TITULAR_FIRMA_EQUIPO = "TITULAR_FIRMA_EQUIPO"

PAQUETES: dict[str, dict] = {
    PISO: {
        "kind": KIND_PISO,
        "descripcion": "Piso de cualquier sesion autenticada. Se suma siempre.",
        "permisos": {
            "inicio": ("ver",),
            "perfil": ("ver", "editar_propio"),
        },
    },
    "superadmin": {
        "kind": KIND_BASE,
        "descripcion": "Acceso total. Inmutable por API.",
        "permisos": COMODIN_TODO,
    },
    "admin": {
        "kind": KIND_BASE,
        "descripcion": "Presupuestos completo + Equipos completo (incluye aprobacion). Sin gestion de usuarios (R4).",
        "permisos": {
            "presupuestos": (
                "ver_global",
                "ver_propio",
                "subir_ticket",
                "validar_ticket",
                "borrar_ticket",
                "gestionar_ciclos",
                "gastos_generales",
                "exportar",
            ),
            "equipos_inventario": ("ver", "crear", "editar", "auditar_condicion", "dar_de_baja"),
            "equipos_prestamos": (
                "solicitar",
                "ver_propios",
                "ver_global",
                "registrar_devolucion",
                "cancelar",
                "exportar",
            ),
            "equipos_aprobacion": ("autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"),
        },
    },
    "creador": {
        "kind": KIND_BASE,
        "descripcion": "Creador de contenido: sube sus tickets y ve lo suyo. Aislado del resto de Presupuestos.",
        "permisos": {
            "presupuestos": ("ver_propio", "subir_ticket"),
        },
    },
    "marketing_presupuestos": {
        "kind": KIND_BASE,
        "descripcion": "Marketing — Presupuestos completo. Cero acceso a Equipos.",
        "permisos": {
            "presupuestos": (
                "ver_global",
                "ver_propio",
                "subir_ticket",
                "validar_ticket",
                "borrar_ticket",
                "gestionar_ciclos",
                "gastos_generales",
                "exportar",
            ),
        },
    },
    "marketing_equipos": {
        "kind": KIND_BASE,
        "descripcion": "Marketing — Equipos completo (inventario, prestamos, devoluciones). "
        "Sin aprobacion: para autorizar entregas se necesita el paquete aditivo APROBADOR_EQUIPO.",
        "permisos": {
            "equipos_inventario": ("ver", "crear", "editar", "auditar_condicion", "dar_de_baja"),
            "equipos_prestamos": (
                "solicitar",
                "ver_propios",
                "ver_global",
                "registrar_devolucion",
                "cancelar",
                "exportar",
            ),
        },
    },
    "marketing_admin": {
        "kind": KIND_BASE,
        "descripcion": "Marketing — Administrador (organigrama de accesos, jul-2026). Presupuestos "
        "completo + Equipos completo, SIN aprobacion: esa sigue siendo exclusiva de 'admin'.",
        "permisos": {
            "presupuestos": (
                "ver_global",
                "ver_propio",
                "subir_ticket",
                "validar_ticket",
                "borrar_ticket",
                "gestionar_ciclos",
                "gastos_generales",
                "exportar",
            ),
            "equipos_inventario": ("ver", "crear", "editar", "auditar_condicion", "dar_de_baja"),
            "equipos_prestamos": (
                "solicitar",
                "ver_propios",
                "ver_global",
                "registrar_devolucion",
                "cancelar",
                "exportar",
            ),
        },
    },
    "marketing_basico": {
        "kind": KIND_BASE,
        "descripcion": "Marketing — acceso basico (organigrama de accesos, jul-2026). Solo subir "
        "tickets propios y solicitar prestamos de equipo; sin dashboards ni gestion.",
        "permisos": {
            "presupuestos": ("ver_propio", "subir_ticket"),
            "equipos_prestamos": ("solicitar", "ver_propios"),
        },
    },
    "colaborador_mkt": {
        "kind": KIND_BASE,
        "descripcion": "[Legacy] Migrado a marketing_equipos/marketing_basico. Se conserva para no "
        "romper usuarios existentes.",
        "permisos": {
            "equipos_inventario": ("ver",),
            "equipos_prestamos": ("solicitar", "ver_propios", "registrar_devolucion"),
        },
    },
    "usuario": {
        "kind": KIND_BASE,
        "descripcion": "Empleado general. Acceso minimo: solo inicio y perfil propio. "
        "Los permisos a modulos se conceden via paquetes aditivos.",
        "permisos": {
            # Solo piso -- sin acceso a presupuestos ni equipos por defecto.
            # Los modulos se abren con paquetes aditivos.
        },
    },
    "APROBADOR_EQUIPO": {
        "kind": KIND_ADITIVO,
        "descripcion": "Autoriza entregas y confirma devoluciones de equipo. "
        "Diseñado para agregarse a marketing_equipos. Cero permisos de presupuestos.",
        "permisos": {
            "equipos_aprobacion": ("autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"),
            "equipos_prestamos": ("ver_global",),
        },
    },
    "CUSTODIO_EQUIPO": {
        "kind": KIND_ADITIVO,
        "descripcion": "Administra el inventario de equipo. No aprueba prestamos. "
        "Útil para el rol usuario que solo necesita gestionar inventario.",
        "permisos": {
            "equipos_inventario": ("crear", "editar", "auditar_condicion", "dar_de_baja"),
            "equipos_prestamos": ("ver_global",),
        },
    },
    "AUDITOR": {
        "kind": KIND_ADITIVO,
        "descripcion": "Solo lecturas globales. Cero escritura.",
        "permisos": {
            "presupuestos": ("ver_global",),
            "equipos_inventario": ("ver",),
            "equipos_prestamos": ("ver_global",),
        },
    },
    "APROBADOR_PRESUPUESTOS": {
        "kind": KIND_ADITIVO,
        "descripcion": "Aprueba, rechaza y borra (logico) tickets de creadores sin ser "
        "admin/superadmin. Pensado para una excepcion puntual asignada por un admin "
        "(ej. alguien designado para cubrir la validacion), no para un rol base nuevo. "
        "El borrado FISICO/permanente sigue siendo exclusivo de admin/superadmin: "
        "ver nota en backend/app/routers/tickets.py.",
        "permisos": {
            "presupuestos": ("validar_ticket", "borrar_ticket"),
        },
    },
    "TITULAR_FIRMA_EQUIPO": {
        "kind": KIND_ADITIVO,
        "singleton": True,
        "descripcion": "Titular de la firma del aprobador en la carta responsiva de Equipos "
        "(ver docs/equipos/firma-pendiente-al-confirmar.md). SINGLETON: solo un usuario a la "
        "vez puede tenerlo — concederlo a alguien nuevo se lo revoca automaticamente al "
        "anterior (crud_rbac.conceder). Su nombre se imprime por default en el bloque de "
        "firma del aprobador mientras nadie haya firmado todavia; en cuanto exista una firma "
        "real (de este titular o de cualquier otra persona con APROBADOR_EQUIPO), esa firma "
        "real manda y nunca se pisa. No concede NINGUN permiso por si solo — es un tag puro, "
        "no un sustituto de APROBADOR_EQUIPO. Pensado para que el nombre impreso por default "
        "no dependa de quien haga clic primero (superadmin, un admin de prueba, etc.) ni quede "
        "hardcodeado a una persona: si Melisa se va, se reasigna aqui y ya.",
        "permisos": {},
    },
}


# ── Consultas sobre el catalogo ─────────────────────────────────────────────


def catalogo_completo() -> dict[str, set[str]]:
    """Todo (modulo, accion) que existe. Es lo que resuelve el comodin `*`."""
    return {modulo: set(acciones) for modulo, acciones in MODULOS.items()}


def es_permiso_valido(modulo: str, accion: str) -> bool:
    return accion in MODULOS.get(modulo, ())


def existe_paquete(nombre: str) -> bool:
    return nombre in PAQUETES


def kind_de(nombre: str) -> str | None:
    paquete = PAQUETES.get(nombre)
    return paquete["kind"] if paquete else None


def descripcion_de(nombre: str) -> str:
    paquete = PAQUETES.get(nombre)
    return paquete["descripcion"] if paquete else ""


def es_singleton(nombre: str) -> bool:
    """True si el paquete solo puede tenerlo un usuario a la vez.

    `crud_rbac.conceder()` lo usa para revocar del titular anterior antes de
    conceder al nuevo. Paquete inexistente = False (deny-by-default: nada
    especial pasa con un nombre basura).
    """
    paquete = PAQUETES.get(nombre)
    return bool(paquete and paquete.get("singleton", False))


def permisos_de_paquete(nombre: str) -> dict[str, set[str]]:
    """Permisos que abre un paquete. Paquete inexistente = {} (deny-by-default:
    un rol base con un valor basura no abre nada, ni siquiera error)."""
    paquete = PAQUETES.get(nombre)
    if paquete is None:
        return {}
    permisos = paquete["permisos"]
    if permisos == COMODIN_TODO:
        return catalogo_completo()
    return {modulo: set(acciones) for modulo, acciones in permisos.items()}


def nombres_por_kind(kind: str) -> list[str]:
    return [nombre for nombre, paquete in PAQUETES.items() if paquete["kind"] == kind]


def nombres_aditivos() -> list[str]:
    return nombres_por_kind(KIND_ADITIVO)


def paquetes_que_conceden(modulo: str, accion: str) -> set[str]:
    """Nombres de paquete que abren ese (modulo, accion). Lo usa
    `crud_rbac.usuarios_con_permiso()` para resolver destinatarios por rol."""
    return {
        nombre
        for nombre in PAQUETES
        if accion in permisos_de_paquete(nombre).get(modulo, set())
    }


def unir(*conjuntos: dict[str, set[str]]) -> dict[str, set[str]]:
    """Union de mapas {modulo: {accion}}. No muta sus argumentos."""
    resultado: dict[str, set[str]] = {}
    for conjunto in conjuntos:
        for modulo, acciones in conjunto.items():
            resultado.setdefault(modulo, set()).update(acciones)
    return resultado


def a_json(permisos: dict[str, set[str]]) -> dict[str, list[str]]:
    """Forma de transporte del contrato: listas ordenadas, no sets (JSON no
    tiene sets). Orden = el del catalogo, para que dos respuestas iguales sean
    byte-identicas y las pruebas de contrato no dependan del hash de Python."""
    salida: dict[str, list[str]] = {}
    for modulo in MODULOS:
        acciones = permisos.get(modulo)
        if not acciones:
            continue
        salida[modulo] = [a for a in MODULOS[modulo] if a in acciones]
    # Modulos fuera del catalogo no deberian existir; si aparecen, se muestran
    # ordenados en vez de desaparecer en silencio.
    for modulo in sorted(set(permisos) - set(MODULOS)):
        if permisos[modulo]:
            salida[modulo] = sorted(permisos[modulo])
    return salida


def validar_catalogo() -> list[str]:
    """Errores de consistencia interna. Lista vacia = catalogo sano.
    La llama la migracion antes de sembrar: sembrar un catalogo invalido deja
    filas huerfanas que nadie vuelve a mirar."""
    errores: list[str] = []
    for nombre, paquete in PAQUETES.items():
        if paquete["kind"] not in (KIND_PISO, KIND_BASE, KIND_ADITIVO):
            errores.append(f"{nombre}: kind desconocido '{paquete['kind']}'")
        permisos = paquete["permisos"]
        if permisos == COMODIN_TODO:
            continue
        for modulo, acciones in permisos.items():
            if modulo not in MODULOS:
                errores.append(f"{nombre}: modulo inexistente '{modulo}'")
                continue
            for accion in acciones:
                if not es_permiso_valido(modulo, accion):
                    errores.append(f"{nombre}: accion inexistente '{modulo}:{accion}'")
    return errores
