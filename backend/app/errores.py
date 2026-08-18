"""Sobre de error unico del contrato de Control de Equipos.

El contrato (`docs/contratos/API_EQUIPOS_v1.md` §0) exige que todo error responda
con un cuerpo plano:

    { "detail": "texto legible", "codigo": "CODIGO_ESTABLE" }

`HTTPException` de FastAPI no sirve: su manejador envuelve el detalle en
`{"detail": <lo que sea>}`, asi que un dict adentro sale anidado y el cliente
no encuentra `codigo` en la raiz. Por eso una excepcion propia con su manejador
registrado en `main.py`.

Un `codigo` estable es lo que permite que el cliente distinga 403 por politica
de 503 por infraestructura. El texto de `detail` puede cambiar; el codigo no.

Nota de alcance: este archivo no estaba en la lista de rutas del reparto. Se
creo porque el sobre de error es un problema transversal (lo usan rbac, media,
prestamos y aprobacion) y meterlo en `rbac.py` lo dejaria en el modulo
equivocado. Es un archivo nuevo dentro de `backend/app/`: nadie mas lo toca, asi
que no hay riesgo de merge. Reportado en `docs/avances/servidor.md`.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

# Codigos estables del contrato §0.
SIN_PERMISO = "SIN_PERMISO"
PERMISOS_NO_DISPONIBLES = "PERMISOS_NO_DISPONIBLES"
EQUIPO_OCUPADO = "EQUIPO_OCUPADO"
TRANSICION_INVALIDA = "TRANSICION_INVALIDA"
MEDIA_INVALIDA = "MEDIA_INVALIDA"
MEDIA_MUY_GRANDE = "MEDIA_MUY_GRANDE"
NO_ENCONTRADO = "NO_ENCONTRADO"


class ErrorEquipos(Exception):
    """Error con sobre del contrato. Se levanta, no se devuelve."""

    def __init__(self, status_code: int, detail: str, codigo: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.codigo = codigo

    def cuerpo(self) -> dict[str, str]:
        return {"detail": self.detail, "codigo": self.codigo}


class PermisosNoDisponibles(ErrorEquipos):
    """No se pudieron resolver los permisos (fallo de base).

    **503, jamas 403 y jamas `{}`.** Un conjunto de permisos vacio produce un 403
    en todos lados que se lee como decision de politica: el cliente desloguea al
    usuario y nadie se entera de que lo que fallo fue la base
    (§10.6 del plan, leccion Bruckner CRITICO-2).
    """

    def __init__(self, detail: str = "No se pudieron resolver los permisos. Reintenta en un momento."):
        super().__init__(503, detail, PERMISOS_NO_DISPONIBLES)


class SinPermiso(ErrorEquipos):
    def __init__(self, detail: str = "No tienes permiso para esta accion."):
        super().__init__(403, detail, SIN_PERMISO)


class NoEncontrado(ErrorEquipos):
    """404. Incluye recursos con borrado logico: existir borrado y no existir se
    responden igual, para no filtrar la existencia del registro."""

    def __init__(self, detail: str = "No encontrado."):
        super().__init__(404, detail, NO_ENCONTRADO)


class EquipoOcupado(ErrorEquipos):
    def __init__(self, detail: str = "El equipo ya esta en un prestamo abierto."):
        super().__init__(409, detail, EQUIPO_OCUPADO)


class TransicionInvalida(ErrorEquipos):
    def __init__(self, detail: str = "La operacion no aplica al estado actual del prestamo."):
        super().__init__(409, detail, TRANSICION_INVALIDA)


class MediaInvalida(ErrorEquipos):
    def __init__(self, detail: str = "El archivo no es una imagen JPEG o PNG valida."):
        super().__init__(422, detail, MEDIA_INVALIDA)


class MediaMuyGrande(ErrorEquipos):
    def __init__(self, detail: str = "El archivo excede el tamaño permitido."):
        super().__init__(413, detail, MEDIA_MUY_GRANDE)


async def manejador_error_equipos(request: Request, exc: ErrorEquipos) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.cuerpo())


def registrar_manejadores(app) -> None:
    """Lo llama `main.py`. Una sola linea de cableado, sin logica en main."""
    app.add_exception_handler(ErrorEquipos, manejador_error_equipos)
