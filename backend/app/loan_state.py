"""Maquina de estados del prestamo. Aislada y pura.

No importa la sesion de base de datos ni FastAPI: recibe valores, devuelve
valores y levanta su propia excepcion. Los routers traducen a
`errores.TransicionInvalida` (409 `TRANSICION_INVALIDA`). Asi la maquina se
prueba sin levantar la app y sin sembrar una base.

    borrador --confirmar--> prestado --devolucion--> pendiente_confirmacion
       |                                                      |
     cancelar                                        confirmar-devolucion
       v                                                      v
    cancelado                                     completado | incompleto
                                                                  |
                                                         cerrar-incidencia
                                                                  v
                                                             completado

Siete transiciones, ni una mas. **Cualquier par (accion, estado) que no este en
la tabla responde 409 TRANSICION_INVALIDA** — es regla de cierre explicita del
contrato §3, no interpretacion.

Tres reglas que se prestan a confusion y por eso viven aqui, no repartidas:

1. `entrega_autorizada` es **ortogonal** al estado: Melisa puede autorizar antes
   o despues de que el equipo vuelva. Pero **bloquea llegar a `completado`**, por
   los dos caminos (confirmar-devolucion con todo `ok`, y cerrar-incidencia). Con
   `entrega_autorizada=0` un prestamo puede recorrer el flujo entero sin que
   nadie autorice la responsiva: ese era el hueco de trazabilidad §10.11.
   La guarda se evalua contra el estado **destino**, no contra el actual: con
   alguna decision distinta de `ok` el destino es `incompleto` y la operacion
   procede aunque no haya autorizacion.

1b. `firmas_completas` (ambas firmas capturadas) sigue el MISMO patron que
   `entrega_autorizada`: `confirmar` **nunca** pide ninguna firma (decision
   explicita del usuario, revision 2 — quien llena el formulario no es
   necesariamente ni quien aprueba ni quien recibe el equipo), pero
   **bloquea llegar a `completado`**, por los mismos dos caminos. Sin esta
   guarda, un prestamo sin ninguna firma podria cerrarse del todo sin que
   nadie firmara jamas la responsiva. Las dos firmas se suben despues,
   siempre con el prestamo ya confirmado (`prestado`, `pendiente_confirmacion`
   o `incompleto` — nunca `borrador`, ver `acepta_media`); una vez capturada
   una firma no se puede volver a subir para ese `(prestamo, kind)` — es
   evidencia, la protege el router, no esta funcion.

   Las dos firmas ya NO son intercambiables: `firma_entrega` es de quien
   **aprueba** el prestamo (paquete `APROBADOR_EQUIPO` — Melisa u otra persona
   con el mismo paquete, nunca quien llena el formulario a menos que tambien
   tenga el paquete), y `firma_responsable` es del **beneficiario** (quien
   recibe el equipo — capturado como texto libre en `responsable_nombre`/
   `responsable_email`, puede ser distinto de quien crea el prestamo). El
   router exige el permiso de aprobacion especificamente para subir
   `firma_entrega`; el resto de los kinds de media siguen pidiendo
   `equipos_prestamos:solicitar`.

2. `devuelto_at` de un renglon se escribe en **exactamente dos** operaciones:
   `cancelar` y `confirmar-devolucion`. En ninguna otra. `devolucion` NO lo
   escribe: si lo hiciera, el equipo apareceria libre mientras el aprobador
   todavia no lo revisa, y un equipo marcado `no_devuelto` (perdido) volveria a
   ser prestable. Lo que mantiene fuera de circulacion a un equipo con incidencia
   es `estado_operativo='revision'`, no el renglon abierto.
"""

from __future__ import annotations

from .models_equipos import DecisionDevolucion, EstadoPrestamo

__all__ = [
    "Accion",
    "TransicionNoPermitida",
    "TRANSICIONES",
    "estado_destino",
    "destino_por_decisiones",
    "exige_autorizacion_de_entrega",
    "exige_firmas_completas",
    "escribe_devuelto_at",
    "acepta_items",
    "acepta_media",
    "acepta_autorizacion",
    "kinds_de_entrega",
    "kinds_de_firma",
    "kinds_de_devolucion",
]


class Accion(str):
    """Acciones del contrato §3 y §4. Cadenas simples para que la tabla de
    transiciones se lea igual que el diagrama."""

    CONFIRMAR = "confirmar"
    CANCELAR = "cancelar"
    DEVOLUCION = "devolucion"
    CONFIRMAR_DEVOLUCION = "confirmar-devolucion"
    CERRAR_INCIDENCIA = "cerrar-incidencia"


class TransicionNoPermitida(Exception):
    """La accion no aplica al estado actual. El router la traduce a 409."""

    def __init__(self, estado_actual: str, accion: str, detalle: str | None = None):
        self.estado_actual = estado_actual
        self.accion = accion
        self.detalle = detalle or (
            f"No se puede '{accion}' un prestamo en estado '{estado_actual}'."
        )
        super().__init__(self.detalle)


B = EstadoPrestamo.BORRADOR.value
P = EstadoPrestamo.PRESTADO.value
PC = EstadoPrestamo.PENDIENTE_CONFIRMACION.value
CO = EstadoPrestamo.COMPLETADO.value
IN = EstadoPrestamo.INCOMPLETO.value
CA = EstadoPrestamo.CANCELADO.value

# Tabla completa. `None` como destino = lo decide el contexto (las decisiones).
TRANSICIONES: dict[tuple[str, str], str | None] = {
    (B, Accion.CONFIRMAR): P,
    (B, Accion.CANCELAR): CA,
    (P, Accion.DEVOLUCION): PC,
    (PC, Accion.CONFIRMAR_DEVOLUCION): None,
    (IN, Accion.CERRAR_INCIDENCIA): CO,
}

# Estados en los que el prestamo sigue vivo para el negocio.
TERMINALES = frozenset({CO, CA})


def destino_por_decisiones(decisiones: list[str]) -> str:
    """Todas `ok` -> completado. Alguna distinta -> incompleto.

    Una lista vacia no puede pasar por aqui: un prestamo sin renglones no llega
    a `pendiente_confirmacion`. Si llegara, se trata como incompleto en vez de
    completar en silencio algo que nadie reviso.
    """
    if not decisiones:
        return IN
    return CO if all(d == DecisionDevolucion.OK.value for d in decisiones) else IN


def estado_destino(estado_actual: str, accion: str, decisiones: list[str] | None = None) -> str:
    """Estado al que lleva la accion. Levanta `TransicionNoPermitida` si el par
    no esta en la tabla."""
    if (estado_actual, accion) not in TRANSICIONES:
        raise TransicionNoPermitida(estado_actual, accion)

    destino = TRANSICIONES[(estado_actual, accion)]
    if destino is not None:
        return destino
    return destino_por_decisiones(decisiones or [])


def exige_autorizacion_de_entrega(destino: str) -> bool:
    """Solo llegar a `completado` exige la autorizacion. Se evalua contra el
    DESTINO: pasar a `incompleto` sin autorizacion es valido y necesario, porque
    si no un prestamo con incidencia y sin autorizar no tendria a donde ir."""
    return destino == CO


def exige_firmas_completas(destino: str) -> bool:
    """Mismo patron que `exige_autorizacion_de_entrega`, misma razon: solo
    `completado` exige que ambas firmas ya esten. Ver nota 1b del modulo."""
    return destino == CO


def escribe_devuelto_at(accion: str) -> bool:
    """Las dos unicas operaciones que cierran renglones.

    Si esta lista crece sin querer, un equipo queda libre antes de tiempo. Si
    encoge, queda bloqueado para siempre: el indice unico parcial no perdona.
    """
    return accion in (Accion.CANCELAR, Accion.CONFIRMAR_DEVOLUCION)


def acepta_items(estado: str) -> bool:
    """Agregar o quitar equipos solo tiene sentido en el borrador. Hacerlo
    despues cambiaria el contenido de una carta responsiva ya firmada."""
    return estado == B


def kinds_de_entrega() -> tuple[str, ...]:
    """Fotos de entrega. Las firmas NO estan aqui: tienen su propia ventana de
    estados (`kinds_de_firma`), mas amplia. Antes las cuatro vivian juntas; se
    separaron al permitir completar una firma pendiente en `prestado` sin abrir
    esa misma puerta para las fotos."""
    return ("foto_entrega_frente", "foto_entrega_atras")


def kinds_de_firma() -> tuple[str, ...]:
    return ("firma_entrega", "firma_responsable")


def kinds_de_devolucion() -> tuple[str, ...]:
    return ("foto_dev_frente", "foto_dev_atras")


def acepta_media(estado: str, kind: str) -> bool:
    """Fotos de entrega solo en `borrador`; fotos de devolucion solo en
    `prestado`; firmas en **`prestado`, `pendiente_confirmacion` o
    `incompleto`** (ver nota 1b del modulo) — nunca en `borrador`: desde que
    `confirmar` dejo de pedir ninguna firma, las dos se completan siempre
    despues, con el prestamo ya confirmado (folio real, responsiva v1 ya
    generada). Firmar un borrador que todavia puede perder o ganar equipos no
    tiene sentido.

    El contrato no lo escribe. Se aplica igual porque no hay flujo legitimo que
    suba una foto de entrega a un prestamo ya completado, y permitirlo deja
    reescribir la evidencia que respalda una responsiva firmada (§6: "un
    documento firmado es evidencia"). Reportado en docs/avances/servidor.md.

    Que una firma pase esta funcion NO significa que se pueda resubir una
    firma que ya existe para ese prestamo: esa proteccion depende de una
    consulta a `media_asset` y vive en el router, no aqui (esta funcion es
    pura, sin base de datos).
    """
    if kind in kinds_de_firma():
        return estado in (P, PC, IN)
    if kind in kinds_de_entrega():
        return estado == B
    if kind in kinds_de_devolucion():
        return estado == P
    return False


def acepta_autorizacion(estado: str) -> bool:
    """Desde que estados se acepta autorizar la entrega.

    El contrato solo dice que es ortogonal al estado; la lista concreta es
    derivada. `incompleto` es el caso menos obvio y el mas importante: sin el,
    un prestamo que llego a incompleto sin autorizacion **no se puede cerrar
    nunca**, porque `cerrar-incidencia` exige la autorizacion que ya no habria
    forma de dar.

    `borrador` queda fuera: todavia no hay folio ni responsiva que autorizar.
    `cancelado` y `completado` quedan fuera por terminales.
    """
    return estado in (P, PC, IN)
