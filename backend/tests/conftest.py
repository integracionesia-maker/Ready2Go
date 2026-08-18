"""Configuración compartida de pytest: DB de pruebas aislada (nunca la real),
fixtures de usuarios por rol y helpers de login.
"""

import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).parent / "test_auth.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-0123456789abcdef")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("ENV", "development")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient

from app import audit_queue, models, security
from app.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def _clean_state():
    """Cada test arranca con tablas vacías y sin historial de rate limiting."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    security._login_attempts_by_ip.clear()
    # La cola de auditoria es estado a nivel modulo — descartar eventos
    # de tests anteriores cuyos usuarios ya no existen en la DB nueva.
    audit_queue.limpiar_cola()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def make_user(
    db,
    *,
    username,
    password,
    role,
    email=None,
    full_name=None,
    creator_id=None,
    must_change_password=False,
    is_active=True,
):
    user = models.User(
        username=username,
        email=email or f"{username}@test.com",
        password_hash=security.hash_password(password),
        full_name=full_name or username,
        role=role,
        creator_id=creator_id,
        must_change_password=must_change_password,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_creator(
    db, *, name="Creador Test", initial_budget=10_000.0, cycle_budget_amount=None, cycle_period="mensual"
):
    creator = models.Creator(
        name=name,
        initial_budget=initial_budget,
        remaining_budget=initial_budget,
        cycle_budget_amount=cycle_budget_amount if cycle_budget_amount is not None else initial_budget,
        cycle_period=cycle_period,
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return creator


def make_brand(db, *, name="Marca Test", priority="media"):
    brand = models.Brand(name=name, priority=priority)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def make_ticket(db, *, creator, brand, amount=100.0, status="aprobado", actor_user_id=1):
    from app import crud

    return crud.create_ticket(
        db=db,
        creator=creator,
        brand=brand,
        amount=amount,
        file_name="comprobante.pdf",
        file_path=str(Path(__file__).parent / "fixtures_dummy.pdf"),
        mime_type="application/pdf",
        notes=None,
        status=status,
        actor_user_id=actor_user_id,
    )


def login(client, identificador, password):
    return client.post("/api/auth/login", json={"identificador": identificador, "password": password})


PASSWORD_SUPERADMIN = "SuperClaveTest123!"
PASSWORD_ADMIN = "AdminClaveTest123!"
PASSWORD_CREADOR = "CreadorClaveTest123!"
PASSWORD_MARKETING_PRESUPUESTOS = "MktPresuClaveTest123!"
PASSWORD_MARKETING_ADMIN = "MktAdminClaveTest123!"
PASSWORD_MARKETING_BASICO = "MktBasicoClaveTest123!"
PASSWORD_USUARIO = "UsuarioClaveTest123!"
PASSWORD_COLABORADOR_MKT = "ColaboradorClaveTest123!"


@pytest.fixture
def creator_a(db):
    return make_creator(db, name="Creador A", initial_budget=10_000.0)


@pytest.fixture
def creator_b(db):
    return make_creator(db, name="Creador B", initial_budget=20_000.0)


@pytest.fixture
def brand_a(db):
    return make_brand(db, name="Marca A")


@pytest.fixture
def superadmin_user(db):
    return make_user(db, username="superadmin", password=PASSWORD_SUPERADMIN, role="superadmin")


@pytest.fixture
def admin_user(db):
    return make_user(db, username="admin1", password=PASSWORD_ADMIN, role="admin")


@pytest.fixture
def marketing_presupuestos_user(db):
    return make_user(
        db, username="mkt.presu", password=PASSWORD_MARKETING_PRESUPUESTOS, role="marketing_presupuestos"
    )


@pytest.fixture
def marketing_admin_user(db):
    return make_user(db, username="mkt.admin", password=PASSWORD_MARKETING_ADMIN, role="marketing_admin")


@pytest.fixture
def marketing_basico_user(db):
    return make_user(db, username="mkt.basico", password=PASSWORD_MARKETING_BASICO, role="marketing_basico")


@pytest.fixture
def usuario_user(db):
    return make_user(db, username="usuario.generico", password=PASSWORD_USUARIO, role="usuario")


@pytest.fixture
def colaborador_mkt_user(db):
    return make_user(
        db, username="colab.mkt", password=PASSWORD_COLABORADOR_MKT, role="colaborador_mkt"
    )


@pytest.fixture
def creador_user(db, creator_a):
    return make_user(db, username="creador.a", password=PASSWORD_CREADOR, role="creador", creator_id=creator_a.id)


@pytest.fixture
def creador_user_b(db, creator_b):
    return make_user(db, username="creador.b", password=PASSWORD_CREADOR, role="creador", creator_id=creator_b.id)


def _independent_client(username, password):
    """Cliente propio (no el de la fixture `client`): usar dos fixtures
    logged_in_* distintas en el mismo test requiere sesiones independientes,
    de lo contrario comparten cookie jar y una pisa la sesión de la otra."""
    c = TestClient(app)
    login(c, username, password)
    return c


@pytest.fixture
def logged_in_superadmin(superadmin_user):
    return _independent_client("superadmin", PASSWORD_SUPERADMIN)


@pytest.fixture
def logged_in_admin(admin_user):
    return _independent_client("admin1", PASSWORD_ADMIN)


@pytest.fixture
def logged_in_marketing_presupuestos(marketing_presupuestos_user):
    return _independent_client("mkt.presu", PASSWORD_MARKETING_PRESUPUESTOS)


@pytest.fixture
def logged_in_marketing_admin(marketing_admin_user):
    return _independent_client("mkt.admin", PASSWORD_MARKETING_ADMIN)


@pytest.fixture
def logged_in_marketing_basico(marketing_basico_user):
    return _independent_client("mkt.basico", PASSWORD_MARKETING_BASICO)


@pytest.fixture
def logged_in_usuario(usuario_user):
    return _independent_client("usuario.generico", PASSWORD_USUARIO)


@pytest.fixture
def logged_in_colaborador_mkt(colaborador_mkt_user):
    return _independent_client("colab.mkt", PASSWORD_COLABORADOR_MKT)


@pytest.fixture
def logged_in_creador(creador_user):
    return _independent_client("creador.a", PASSWORD_CREADOR)


@pytest.fixture
def logged_in_creador_b(creador_user_b):
    return _independent_client("creador.b", PASSWORD_CREADOR)
