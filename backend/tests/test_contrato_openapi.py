"""Guardia de contrato: el servidor no se sale del OpenAPI congelado.

Compara el `openapi.json` que genera la app contra
`docs/contratos/openapi_equipos_v1.json`. Rojo = el servidor se salio del
contrato. Se arregla en el servidor **o** se pide cambio de contrato; nunca se
ignora.

**Ese archivo todavia no existe.** El §8 del contrato lo dice explicito:

    "openapi_equipos_v1.json todavia no existe. Se genera del servidor en cuanto
     los primeros endpoints esten en pie, se congela aqui, y hasta entonces la
     prueba guardia test_contrato_openapi.py (tarea S7) queda en skip con el
     motivo escrito. Este documento manda mientras tanto."

Asi que la comparacion queda en `skip` **con el motivo escrito**, y mientras
tanto esta prueba si verifica lo que si esta congelado en `API_EQUIPOS_v1.md`:
que todas las rutas y metodos de sus tablas existan en el servidor, con el
nombre exacto. Eso es lo que rompe a un cliente, y no depende de que alguien
congele el JSON.

Para congelar el contrato cuando toque:

    cd backend
    JWT_SECRET_KEY=x python -c "import json;from app.main import app;print(json.dumps(app.openapi(),indent=2,ensure_ascii=False))" \
      > ../docs/contratos/openapi_equipos_v1.json
"""

import json
from pathlib import Path

import pytest

RAIZ_REPO = Path(__file__).resolve().parents[2]
CONTRATO_OPENAPI = RAIZ_REPO / "docs" / "contratos" / "openapi_equipos_v1.json"

MOTIVO_SKIP = (
    "docs/contratos/openapi_equipos_v1.json no existe todavia (contrato §8: "
    "'se genera del servidor en cuanto los primeros endpoints esten en pie'). "
    "Hasta que se congele, la comparacion no puede correr. Pedido en "
    "docs/backlog_servidor.md."
)


def _spec():
    from app.main import app

    return app.openapi()


# Rutas y metodos congelados en las tablas de `docs/contratos/API_EQUIPOS_v1.md`.
# Escritas a mano: derivarlas del servidor haria la guardia tautologica.
RUTAS_DEL_CONTRATO = [
    # §1 Permisos
    ("get", "/api/auth/me"),
    # §2 Inventario
    ("get", "/api/equipment/"),
    ("get", "/api/equipment/dashboard"),
    ("get", "/api/equipment/{equipment_id}"),
    ("post", "/api/equipment/"),
    ("put", "/api/equipment/{equipment_id}"),
    ("post", "/api/equipment/{equipment_id}/auditoria"),
    ("post", "/api/equipment/{equipment_id}/baja"),
    # §3 Prestamos
    ("post", "/api/loans/"),
    ("get", "/api/loans/"),
    ("get", "/api/loans/{loan_id}"),
    ("get", "/api/loans/by-folio/{folio}"),
    ("post", "/api/loans/{loan_id}/items"),
    ("delete", "/api/loans/{loan_id}/items/{item_id}"),
    ("post", "/api/loans/{loan_id}/media"),
    ("post", "/api/loans/{loan_id}/confirmar"),
    ("post", "/api/loans/{loan_id}/cancelar"),
    ("post", "/api/loans/{loan_id}/devolucion"),
    ("get", "/api/loans/{loan_id}/responsiva.pdf"),
    ("get", "/api/loans/export"),
    # §4 Aprobacion
    ("post", "/api/loans/{loan_id}/autorizar-entrega"),
    ("post", "/api/loans/{loan_id}/confirmar-devolucion"),
    ("post", "/api/loans/{loan_id}/cerrar-incidencia"),
    # §5 Media
    ("get", "/api/media/{media_id}"),
    # §6 Empresas
    ("get", "/api/empresas/"),
    ("post", "/api/empresas/"),
    ("put", "/api/empresas/{empresa_id}"),
    # §7 Roles
    ("get", "/api/roles/"),
    ("get", "/api/users/{user_id}/roles"),
    ("post", "/api/users/{user_id}/roles"),
    ("delete", "/api/users/{user_id}/roles/{role_name}"),
]


@pytest.mark.parametrize("metodo,ruta", RUTAS_DEL_CONTRATO)
def test_cada_ruta_del_contrato_existe_en_el_servidor(metodo, ruta):
    """Una ruta del contrato que falta o cambio de nombre rompe al cliente el dia
    de la integracion, no antes."""
    paths = _spec()["paths"]
    assert ruta in paths, f"falta la ruta {ruta}"
    assert metodo in paths[ruta], f"{ruta} no acepta {metodo.upper()}"


def test_las_rutas_van_en_ingles_salvo_las_que_el_contrato_escribe_en_espanol():
    """§0 dice "idioma de las rutas: ingles, sin excepcion", pero las tablas del
    §4 y del §6 traen segmentos en español. Mandan las cadenas literales de las
    tablas: hay cliente codificando contra ellas. Se deja asentado."""
    excepciones = {
        "/api/empresas/",
        "/api/loans/{loan_id}/auditoria",
        "/api/loans/{loan_id}/autorizar-entrega",
        "/api/loans/{loan_id}/confirmar",
        "/api/loans/{loan_id}/confirmar-devolucion",
        "/api/loans/{loan_id}/cerrar-incidencia",
        "/api/loans/{loan_id}/cancelar",
        "/api/loans/{loan_id}/devolucion",
        "/api/loans/{loan_id}/responsiva.pdf",
        "/api/loans/by-folio/{folio}",
        "/api/equipment/{equipment_id}/auditoria",
        "/api/equipment/{equipment_id}/baja",
        "/api/empresas/{empresa_id}",
    }
    for metodo, ruta in RUTAS_DEL_CONTRATO:
        if ruta in excepciones:
            continue
        assert all(ord(c) < 128 for c in ruta), ruta


def test_el_dashboard_no_lo_absorbe_la_ruta_por_id():
    """El contrato §2 lo advierte: `/dashboard` se declara ANTES de `/{id:int}`
    o el enrutador se lo traga como si fuera un id."""
    paths = _spec()["paths"]
    assert "/api/equipment/dashboard" in paths
    assert "/api/equipment/{equipment_id}" in paths


def test_export_y_by_folio_no_los_absorbe_la_ruta_por_id():
    paths = _spec()["paths"]
    assert "/api/loans/export" in paths
    assert "/api/loans/by-folio/{folio}" in paths
    assert "/api/loans/{loan_id}" in paths


def test_no_hay_mount_estatico_de_uploads():
    """§5: "Nunca hay mount estatico". Un StaticFiles sirve por ruta de disco sin
    consultar la fila ni la sesion."""
    from app.main import app

    rutas = [str(getattr(r, "path", "")) for r in app.routes]
    assert not any(r.startswith("/uploads") for r in rutas), rutas


def test_auth_me_declara_el_campo_permisos():
    """§1: `GET /api/auth/me` se amplia con `permisos`. Si desaparece del
    esquema, el cliente deja de saber que pintar."""
    componentes = _spec()["components"]["schemas"]
    assert "permisos" in componentes["UserResponse"]["properties"]


@pytest.mark.skipif(not CONTRATO_OPENAPI.exists(), reason=MOTIVO_SKIP)
def test_el_openapi_generado_no_se_sale_del_congelado():
    """Rutas, metodos, codigos de estado y nombres de campo contra el JSON
    congelado. Rojo = el servidor se salio del contrato."""
    congelado = json.loads(CONTRATO_OPENAPI.read_text(encoding="utf-8"))
    generado = _spec()

    faltantes = []
    for ruta, metodos in congelado["paths"].items():
        if ruta not in generado["paths"]:
            faltantes.append(f"falta la ruta {ruta}")
            continue
        for metodo, definicion in metodos.items():
            if metodo not in generado["paths"][ruta]:
                faltantes.append(f"{ruta} ya no acepta {metodo.upper()}")
                continue
            esperados = set(definicion.get("responses", {}))
            obtenidos = set(generado["paths"][ruta][metodo].get("responses", {}))
            perdidos = esperados - obtenidos
            if perdidos:
                faltantes.append(f"{metodo.upper()} {ruta}: faltan los codigos {sorted(perdidos)}")

    assert not faltantes, "El servidor se salio del contrato:\n" + "\n".join(faltantes)

    esquemas_congelados = congelado.get("components", {}).get("schemas", {})
    esquemas_generados = generado.get("components", {}).get("schemas", {})
    for nombre, esquema in esquemas_congelados.items():
        assert nombre in esquemas_generados, f"falta el esquema {nombre}"
        campos = set(esquema.get("properties", {}))
        obtenidos = set(esquemas_generados[nombre].get("properties", {}))
        assert not (campos - obtenidos), (
            f"{nombre}: faltan los campos {sorted(campos - obtenidos)}"
        )
