"""Migracion idempotente, verificacion del indice parcial y seeds del inventario."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.models_equipos import (
    Empresa,
    Equipment,
    EquipmentAudit,
    FolioCounter,
    Loan,
    LoanEvent,
    MediaAsset,
    ResponsivaDoc,
)

import migrate_equipos
import seed_equipos


def test_crear_tablas_dos_veces_no_falla(db):
    migrate_equipos.crear_tablas()
    migrate_equipos.crear_tablas()
    nombres = migrate_equipos._nombres_de("table")
    for tabla in migrate_equipos.TABLAS:
        assert tabla.name in nombres


def test_el_indice_de_disponibilidad_existe_y_es_parcial(db):
    """Si el indice existiera sin `WHERE devuelto_at IS NULL` seria un unique
    total: un equipo no se podria prestar dos veces nunca. La migracion lo
    comprueba mirando el SQL, no solo el nombre."""
    migrate_equipos.crear_tablas()
    migrate_equipos.verificar_indice_parcial()  # no levanta = pasa


def test_la_verificacion_detecta_un_indice_no_parcial(db):
    """La comprobacion tiene que servir de algo: se rompe el indice a proposito."""
    from sqlalchemy import text

    from app.database import engine

    with engine.begin() as conn:
        conn.execute(text(f"DROP INDEX IF EXISTS {migrate_equipos.INDICE_ABIERTO}"))
        conn.execute(
            text(f"CREATE UNIQUE INDEX {migrate_equipos.INDICE_ABIERTO} ON loan_item(equipment_id)")
        )

    with pytest.raises(SystemExit, match="NO es parcial"):
        migrate_equipos.verificar_indice_parcial()


def test_la_verificacion_detecta_el_indice_ausente(db):
    from sqlalchemy import text

    from app.database import engine

    with engine.begin() as conn:
        conn.execute(text(f"DROP INDEX IF EXISTS {migrate_equipos.INDICE_ABIERTO}"))

    with pytest.raises(SystemExit, match="FALTA el indice"):
        migrate_equipos.verificar_indice_parcial()


def test_las_diez_tablas_del_plan_estan(db):
    esperadas = {
        "equipment",
        "equipment_audit",
        "loan",
        "loan_item",
        "media_asset",
        "responsiva_doc",
        "loan_event",
        "notification_log",
        "empresa",
        "folio_counter",
    }
    assert {t.name for t in migrate_equipos.TABLAS} == esperadas


def test_sembrar_contador_es_idempotente(db):
    migrate_equipos.sembrar_contador()
    migrate_equipos.sembrar_contador()
    assert db.query(FolioCounter).count() == 1


# ── Seed del inventario ─────────────────────────────────────────────────────


def test_seed_de_equipos_crea_los_ocho_de_la_auditoria(db):
    creados = seed_equipos.sembrar_equipos(db, verbose=False)
    assert creados == 8
    assert db.query(Equipment).count() == 8
    assert db.query(EquipmentAudit).count() == 8


def test_seed_de_equipos_es_idempotente(db):
    seed_equipos.sembrar_equipos(db, verbose=False)
    assert seed_equipos.sembrar_equipos(db, verbose=False) == 0
    assert db.query(Equipment).count() == 8
    assert db.query(EquipmentAudit).count() == 8


def test_los_equipos_sembrados_coinciden_con_el_fixture(db, fixture_equipos):
    """Nombre, categoria, modelo, espacio y accesorios, campo por campo contra
    `docs/contratos/fixtures/equipos.json`. Un acento o un guion largo distinto
    aqui se convierte en un mock del cliente que no cuadra con nada."""
    seed_equipos.sembrar_equipos(db, verbose=False)

    for esperado in fixture_equipos["items"]:
        equipo = db.get(Equipment, esperado["id"])
        assert equipo is not None, esperado["id"]
        assert equipo.nombre == esperado["nombre"]
        assert equipo.codigo == esperado["codigo"]
        assert equipo.categoria == esperado["categoria"]
        assert equipo.modelo == esperado["modelo"]
        assert equipo.espacio_disponible == esperado["espacio_disponible"]
        assert equipo.estado_operativo == esperado["estado_operativo"]
        assert json.loads(equipo.accesorios_tipicos) == esperado["accesorios_tipicos"]


def test_las_auditorias_sembradas_coinciden_con_el_fixture(db, fixture_equipos):
    from datetime import date

    seed_equipos.sembrar_equipos(db, verbose=False)

    for esperado in fixture_equipos["items"]:
        auditoria = (
            db.query(EquipmentAudit)
            .filter(EquipmentAudit.equipment_id == esperado["id"])
            .order_by(EquipmentAudit.id.desc())
            .first()
        )
        assert auditoria is not None, esperado["id"]
        assert auditoria.condicion == esperado["condicion"]
        assert auditoria.estado_fisico == esperado["estado_fisico"]
        assert auditoria.comentario == esperado["comentario_auditoria"]
        esperada_fecha = esperado["fecha_auditoria"]
        assert auditoria.fecha == (date.fromisoformat(esperada_fecha) if esperada_fecha else None)


def test_el_cable_fallado_de_los_rode_queda_en_atencion(db):
    """Dato real del area: el cable tipo C de los microfonos RODE falla. Si esa
    condicion se pierde, el equipo se presta como si estuviera perfecto."""
    seed_equipos.sembrar_equipos(db, verbose=False)
    auditoria = (
        db.query(EquipmentAudit).filter(EquipmentAudit.equipment_id == 2).first()
    )
    assert auditoria.condicion == "atencion"
    assert "cable tipo C" in auditoria.comentario


def test_los_dos_iphone_nuevos_no_tienen_fecha_de_auditoria(db):
    """Inventarles una fecha seria firmar una revision fisica que nadie hizo."""
    seed_equipos.sembrar_equipos(db, verbose=False)
    for equipment_id in (7, 8):
        auditoria = (
            db.query(EquipmentAudit)
            .filter(EquipmentAudit.equipment_id == equipment_id)
            .first()
        )
        assert auditoria.fecha is None


def test_seed_de_empresas_coincide_con_el_fixture(db, fixture_empresas):
    seed_equipos.sembrar_empresas(db, verbose=False)
    for esperada in fixture_empresas:
        empresa = db.get(Empresa, esperada["id"])
        assert empresa is not None
        assert empresa.razon_social == esperada["razon_social"]
        assert empresa.direccion == esperada["direccion"]
        assert empresa.ciudad == esperada["ciudad"]
        assert empresa.rfc == esperada["rfc"]
        assert empresa.is_active == esperada["is_active"]


def test_seed_de_empresas_es_idempotente(db):
    seed_equipos.sembrar_empresas(db, verbose=False)
    assert seed_equipos.sembrar_empresas(db, verbose=False) == 0
    assert db.query(Empresa).count() == 3


def test_la_emisora_de_la_responsiva_sale_de_la_tabla(db):
    """§10.21: nunca hardcode en el PDF."""
    from app import crud_empresas

    seed_equipos.sembrar_empresas(db, verbose=False)
    emisora = crud_empresas.emisora_por_defecto(db)
    assert emisora is not None
    assert emisora.rfc == "SCQ1212149P0"
    assert emisora.ciudad == "Morelia, Michoacan"


# ── Seed del prestamo demo ──────────────────────────────────────────────────


def test_seed_del_prestamo_demo_reproduce_los_ids_del_contrato(db, catalogo):
    import seed_prestamo_demo

    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    prestamo = seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)

    assert prestamo.id == 7
    assert prestamo.folio == "CE-0007"
    assert [item.id for item in prestamo.items] == [11]
    assert sorted(m.id for m in db.query(MediaAsset).all()) == [39, 40, 41, 42]
    assert [e.id for e in db.query(LoanEvent).all()] == [21]
    assert db.query(ResponsivaDoc).filter(ResponsivaDoc.loan_id == 7).count() == 1


def test_seed_del_prestamo_demo_es_idempotente(db, catalogo):
    import seed_prestamo_demo

    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)
    seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)

    assert db.query(Loan).count() == 1
    assert db.query(MediaAsset).count() == 4


def test_el_seed_demo_deja_el_contador_de_folio_en_siete(db, catalogo):
    import seed_prestamo_demo

    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)
    assert db.get(FolioCounter, "CE").last_value == 7


def test_el_seed_demo_escribe_archivos_de_media_de_verdad(db, catalogo):
    """Registros de media sin archivo detras hacen que `GET /api/media/{id}`
    devuelva 500 el dia que alguien lo abra."""
    from pathlib import Path

    import seed_prestamo_demo

    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)

    for media in db.query(MediaAsset).all():
        ruta = Path(media.file_path)
        assert ruta.exists(), media.file_path
        assert ruta.stat().st_size == media.size_bytes
        assert len(media.sha256) == 64


# ── Los scripts corriendo solos ─────────────────────────────────────────────

DIR_BACKEND = Path(__file__).resolve().parents[2]

# `seed_auth.py` no es de este carril, pero es la precondicion documentada del
# primer arranque (CLAUDE.md): crea el esquema base y el superadmin. Sin el no
# existe la tabla `users` que casi todo lo de Equipos referencia.
PRECONDICION = "seed_auth.py"

SECUENCIA_DESPLIEGUE = [
    "migrate_rbac_aditivo.py",
    "migrate_equipos.py",
    "seed_rbac.py",
    "seed_equipos.py",
    "seed_prestamo_demo.py",
]


def _correr(script: str, db_url: str, cwd: Path) -> subprocess.CompletedProcess:
    entorno = dict(os.environ)
    entorno["DATABASE_URL"] = db_url
    entorno["JWT_SECRET_KEY"] = "test-secret-key-0123456789abcdef"
    entorno["PYTHONIOENCODING"] = "utf-8"
    # El proceso de pytest ya cargo `backend/.env` (lo hace `app.main`), asi que
    # el hijo hereda las credenciales reales del entorno de desarrollo. Se pisan
    # con valores de prueba: la corrida no debe depender de que haya un .env ni
    # de lo que diga.
    entorno["SUPERADMIN_USERNAME"] = "superadmin"
    entorno["SUPERADMIN_EMAIL"] = "superadmin@test.local"
    entorno["SUPERADMIN_PASSWORD"] = "ClaveDeSeedPrueba123!"
    return subprocess.run(
        [sys.executable, str(DIR_BACKEND / script)],
        cwd=cwd,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


@pytest.mark.parametrize("script", SECUENCIA_DESPLIEGUE)
def test_cada_script_arranca_por_su_cuenta(script, tmp_path):
    """Cada script se ejecuta en un proceso propio, no importado por pytest.

    Es la unica forma de detectar un import faltante: dentro de la suite,
    `conftest` ya cargo `app.main` y con el todos los modelos, asi que un script
    al que le falte `import app.models` pasa las pruebas y revienta el dia del
    despliegue. Paso dos veces mientras escribia S2.
    """
    destino = tmp_path / "despliegue.db"
    url = f"sqlite:///{destino.as_posix()}"

    for paso in [PRECONDICION, *SECUENCIA_DESPLIEGUE]:
        resultado = _correr(paso, url, tmp_path)
        assert resultado.returncode == 0, (
            f"{paso} fallo con codigo {resultado.returncode}\n"
            f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"
        )
        if paso == script:
            break


def test_las_migraciones_avisan_si_falta_el_esquema_base(tmp_path):
    """SQLite crea sin chistar una tabla con FK a una tabla que no existe. El
    error saldria mucho despues, en el primer INSERT, sin decir que falto correr
    `seed_auth.py`. Las migraciones lo dicen antes."""
    url = f"sqlite:///{(tmp_path / 'vacia.db').as_posix()}"

    for script in ("migrate_rbac_aditivo.py", "migrate_equipos.py"):
        resultado = _correr(script, url, tmp_path)
        assert resultado.returncode != 0, script
        salida = resultado.stdout + resultado.stderr
        assert "seed_auth.py" in salida, salida


def test_la_secuencia_completa_corre_dos_veces_seguidas(tmp_path):
    """Idempotencia de punta a punta: migraciones y seeds, dos vueltas."""
    destino = tmp_path / "despliegue.db"
    url = f"sqlite:///{destino.as_posix()}"

    for vuelta in (1, 2):
        for paso in [PRECONDICION, *SECUENCIA_DESPLIEGUE]:
            resultado = _correr(paso, url, tmp_path)
            assert resultado.returncode == 0, (
                f"vuelta {vuelta}, {paso} fallo\n"
                f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"
            )

    from sqlalchemy import create_engine, text

    motor = create_engine(url)
    with motor.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM equipment")).scalar() == 8
        assert conn.execute(text("SELECT COUNT(*) FROM empresa")).scalar() == 3
        assert conn.execute(text("SELECT COUNT(*) FROM loan")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM media_asset")).scalar() == 4
        assert conn.execute(text("SELECT COUNT(*) FROM role_permissions")).scalar() == 62
    motor.dispose()


def test_el_seed_demo_no_pisa_un_usuario_ajeno(db, catalogo):
    """Cuadrar un id del fixture sobrescribiendo la cuenta de otra persona seria
    peor que no sembrar."""
    import seed_prestamo_demo
    from ..conftest import make_user

    make_user(db, username="alguien.mas", password="ClaveValida123!", role="admin")
    # El primer usuario creado toma id 1; se fuerza el choque con el id 4.
    otro = make_user(db, username="ocupa.el.4", password="ClaveValida123!", role="admin")
    otro.id = 4
    db.commit()

    seed_equipos.sembrar_equipos(db, verbose=False)
    with pytest.raises(seed_prestamo_demo.SeedDemoBloqueado, match="ya lo ocupa"):
        seed_prestamo_demo.sembrar_prestamo_demo(db, verbose=False)
