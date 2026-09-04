"""Matriz de permisos endpoint x rol: 401 sin token, 403 con rol incorrecto,
200/201 con el rol correcto. Incluye el filtrado por rol de creador (scoping)."""

from datetime import date

import pytest

from app import crud, models

from .conftest import make_ticket

NO_TOKEN_ENDPOINTS = [
    ("get", "/api/creators/"),
    ("get", "/api/creators/kpi"),
    ("get", "/api/creators/1"),
    ("post", "/api/creators/"),
    ("put", "/api/creators/1"),
    ("get", "/api/brands/"),
    ("get", "/api/brands/1"),
    ("post", "/api/brands/"),
    ("put", "/api/brands/1"),
    ("get", "/api/tickets/"),
    ("get", "/api/tickets/brand-spend"),
    ("get", "/api/tickets/file/1"),
    ("post", "/api/tickets/"),
    ("post", "/api/tickets/1/soft-delete"),
    ("delete", "/api/tickets/1/permanent"),
    ("get", "/api/dashboard/summary"),
    ("get", "/api/dashboard/monthly-spend"),
    ("get", "/api/dashboard/creator-usage"),
    ("get", "/api/dashboard/general-expenses-monthly"),
    ("get", "/api/general-expenses/"),
    ("post", "/api/general-expenses/"),
    ("get", "/api/general-expenses/export?months=2026-07"),
    ("get", "/api/general-expenses/1/file"),
    ("post", "/api/general-expenses/1/soft-delete"),
    ("delete", "/api/general-expenses/1/permanent"),
    ("get", "/api/users/"),
    ("post", "/api/users/"),
    ("get", "/api/users/1"),
    ("put", "/api/users/1"),
    ("post", "/api/users/1/reset-password"),
    ("post", "/api/users/1/reset-password-superadmin"),
    ("patch", "/api/users/1/estado"),
    ("get", "/api/auth/me"),
    ("put", "/api/auth/me"),
    ("post", "/api/auth/change-password"),
    ("post", "/api/auth/logout"),
]


@pytest.mark.parametrize("method,path", NO_TOKEN_ENDPOINTS)
def test_rejects_without_token(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code == 401


def test_health_is_public(client):
    assert client.get("/api/health").status_code == 200


def test_uploads_static_mount_removed(client):
    """El montaje estático de /uploads ya no existe: la ruta jamás sirve el
    archivo sin autenticación. Con el fallback SPA activo (frontend/dist
    presente) las rutas desconocidas devuelven el index del SPA (200
    text/html); sin él, 404. En ningún caso el contenido del upload."""
    resp = client.get("/uploads/tickets/algo.png")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert "text/html" in resp.headers.get("content-type", "")


def test_spa_fallback_does_not_serve_outside_dist(client, tmp_path, monkeypatch):
    """Regresión del path traversal del fallback SPA (hotfix 2026-08-18): una
    ruta con `..` nunca debe servir un archivo fuera de frontend/dist. Si el
    fallback no está registrado (sin frontend/dist en este entorno), no hay
    ruta que probar."""
    import app.main as main_module

    rutas = [r for r in main_module.app.routes if getattr(r, "path", "") == "/{full_path:path}"]
    if not rutas:
        pytest.skip("fallback SPA no registrado: frontend/dist no existe en este entorno")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_bytes(b"<html>SPA</html>")
    secreto = tmp_path / "secreto.txt"
    secreto.write_text("JWT_SECRET_KEY=supersecreto", encoding="utf-8")

    monkeypatch.setattr(main_module, "_frontend_dist", str(dist))
    monkeypatch.setattr(main_module, "_index_html", str(dist / "index.html"))

    for payload in ("/%2e%2e/secreto.txt", "/..%2fsecreto.txt", "/%2e%2e%2fsecreto.txt"):
        resp = client.get(payload)
        assert resp.status_code == 200
        assert b"supersecreto" not in resp.content
        assert b"SPA" in resp.content


class TestCreatorsPermissions:
    def test_creador_sees_only_own_creator_in_list(self, logged_in_creador, creator_a, creator_b):
        resp = logged_in_creador.get("/api/creators/")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert ids == [creator_a.id]

    def test_creador_cannot_see_other_creator_by_id(self, logged_in_creador, creator_b):
        assert logged_in_creador.get(f"/api/creators/{creator_b.id}").status_code == 403

    def test_creador_can_see_own_creator_by_id(self, logged_in_creador, creator_a):
        assert logged_in_creador.get(f"/api/creators/{creator_a.id}").status_code == 200

    def test_creador_cannot_see_kpi(self, logged_in_creador):
        assert logged_in_creador.get("/api/creators/kpi").status_code == 403

    def test_creador_cannot_create_creator(self, logged_in_creador):
        resp = logged_in_creador.post("/api/creators/", json={"name": "Nuevo", "initial_budget": 100})
        assert resp.status_code == 403

    def test_creador_cannot_update_creator(self, logged_in_creador, creator_a):
        resp = logged_in_creador.put(f"/api/creators/{creator_a.id}", json={"name": "Hackeado"})
        assert resp.status_code == 403

    def test_admin_can_list_all_creators(self, logged_in_admin, creator_a, creator_b):
        resp = logged_in_admin.get("/api/creators/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_admin_can_create_and_update_creator(self, logged_in_admin):
        # El schema exige username/email: cada creador recibe su cuenta de login
        # vinculada (feature "creador vinculado", agosto 2026).
        resp = logged_in_admin.post(
            "/api/creators/",
            json={
                "name": "Nuevo",
                "cycle_budget_amount": 500,
                "cycle_period": "mensual",
                "username": "nuevo_creador",
                "email": "nuevo@example.com",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["cycle_amount"] == 500
        cid = resp.json()["id"]
        assert logged_in_admin.put(f"/api/creators/{cid}", json={"is_active": False}).status_code == 200

    def test_admin_can_create_creator_without_cycle_config(self, logged_in_admin, db):
        # Creador nuevo sin monto ni periodicidad (persona recién ingresada):
        # la configuración queda NULL y se materializa un ciclo mensual de $0.
        resp = logged_in_admin.post(
            "/api/creators/",
            json={
                "name": "Sin Ciclo",
                "username": "sin_ciclo",
                "email": "sin_ciclo@example.com",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["cycle_amount"] == 0
        assert body["cycle_period"] == "mensual"
        assert body["temporary_password"]
        creator = db.query(models.Creator).filter(models.Creator.id == body["id"]).first()
        assert creator.cycle_budget_amount is None
        assert creator.cycle_period is None
        assert logged_in_admin.get(f"/api/creators/{creator.id}/ciclos").status_code == 200

    def test_admin_can_create_creator_with_explicit_null_cycle(self, logged_in_admin, db):
        resp = logged_in_admin.post(
            "/api/creators/",
            json={
                "name": "Null Explicito",
                "cycle_budget_amount": None,
                "cycle_period": None,
                "username": "null_ciclo",
                "email": "null_ciclo@example.com",
            },
        )
        assert resp.status_code == 201
        creator = db.query(models.Creator).filter(models.Creator.id == resp.json()["id"]).first()
        assert creator.cycle_budget_amount is None
        assert creator.cycle_period is None

    def test_creator_cycle_period_empty_string_rejected(self, logged_in_admin):
        resp = logged_in_admin.post(
            "/api/creators/",
            json={
                "name": "Period Vacio",
                "cycle_budget_amount": 500,
                "cycle_period": "",
                "username": "period_vacio",
                "email": "period_vacio@example.com",
            },
        )
        assert resp.status_code == 400

    def test_admin_can_clear_cycle_config(self, logged_in_admin, db):
        resp = logged_in_admin.post(
            "/api/creators/",
            json={
                "name": "Con Config",
                "cycle_budget_amount": 500,
                "cycle_period": "semanal",
                "username": "con_config",
                "email": "con_config@example.com",
            },
        )
        cid = resp.json()["id"]
        upd = logged_in_admin.put(
            f"/api/creators/{cid}",
            json={"cycle_budget_amount": None, "cycle_period": None},
        )
        assert upd.status_code == 200
        creator = db.query(models.Creator).filter(models.Creator.id == cid).first()
        assert creator.cycle_budget_amount is None
        assert creator.cycle_period is None

    def test_superadmin_can_see_kpi(self, logged_in_superadmin, creator_a):
        assert logged_in_superadmin.get("/api/creators/kpi").status_code == 200

    def test_creador_cannot_see_other_creators_cycles_idor(self, logged_in_creador, creator_b):
        assert logged_in_creador.get(f"/api/creators/{creator_b.id}/ciclos").status_code == 403

    def test_creador_can_see_own_cycles(self, logged_in_creador, creator_a):
        assert logged_in_creador.get(f"/api/creators/{creator_a.id}/ciclos").status_code == 200

    def test_admin_can_see_any_creator_cycles(self, logged_in_admin, creator_a):
        assert logged_in_admin.get(f"/api/creators/{creator_a.id}/ciclos").status_code == 200


class TestBrandsPermissions:
    def test_creador_can_read_brands(self, logged_in_creador, brand_a):
        assert logged_in_creador.get("/api/brands/").status_code == 200

    def test_creador_cannot_create_brand(self, logged_in_creador):
        assert logged_in_creador.post("/api/brands/", json={"name": "Nueva"}).status_code == 403

    def test_creador_cannot_update_brand(self, logged_in_creador, brand_a):
        resp = logged_in_creador.put(f"/api/brands/{brand_a.id}", json={"name": "Hackeada"})
        assert resp.status_code == 403

    def test_admin_can_create_brand(self, logged_in_admin):
        assert logged_in_admin.post("/api/brands/", json={"name": "Nueva"}).status_code == 201


class TestTicketsPermissionsAndIDOR:
    def test_creador_ticket_list_scoped_to_self(self, logged_in_creador, db, creator_a, creator_b, brand_a):
        make_ticket(db, creator=creator_a, brand=brand_a, amount=50)
        make_ticket(db, creator=creator_b, brand=brand_a, amount=75)

        resp = logged_in_creador.get("/api/tickets/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["creator_id"] == creator_a.id

    def test_creador_ticket_list_ignores_creator_name_filter_override(
        self, logged_in_creador, db, creator_a, creator_b, brand_a
    ):
        make_ticket(db, creator=creator_a, brand=brand_a, amount=50)
        make_ticket(db, creator=creator_b, brand=brand_a, amount=75)

        # Intenta usar el filtro para ver los tickets de otro creador; debe seguir viendo solo los propios.
        resp = logged_in_creador.get(f"/api/tickets/?creator_name={creator_b.name}")
        assert resp.status_code == 200
        assert all(t["creator_id"] == creator_a.id for t in resp.json())

    def test_creador_cannot_download_other_creators_file_idor(self, logged_in_creador, db, creator_b, brand_a):
        ticket = make_ticket(db, creator=creator_b, brand=brand_a, amount=75)
        resp = logged_in_creador.get(f"/api/tickets/file/{ticket.id}")
        assert resp.status_code == 403

    def test_creador_can_download_own_file(self, logged_in_creador, db, creator_a, brand_a):
        ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=75)
        resp = logged_in_creador.get(f"/api/tickets/file/{ticket.id}")
        assert resp.status_code == 200

    def test_admin_can_download_any_file(self, logged_in_admin, db, creator_a, brand_a):
        ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=75)
        resp = logged_in_admin.get(f"/api/tickets/file/{ticket.id}")
        assert resp.status_code == 200

    def test_download_nonexistent_ticket_is_404_not_403(self, logged_in_admin):
        assert logged_in_admin.get("/api/tickets/file/999999").status_code == 404

    def test_creador_cannot_create_ticket_for_other_creator_idor(self, logged_in_creador, creator_b, brand_a):
        resp = logged_in_creador.post(
            "/api/tickets/",
            data={"creator_id": str(creator_b.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 403

    def test_creador_can_create_ticket_for_self(self, logged_in_creador, creator_a, brand_a):
        resp = logged_in_creador.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201

    def test_admin_can_create_ticket_for_any_creator(self, logged_in_admin, creator_a, brand_a):
        resp = logged_in_admin.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201

    def test_creador_cannot_see_brand_spend(self, logged_in_creador):
        assert logged_in_creador.get("/api/tickets/brand-spend").status_code == 403

    def test_admin_can_see_brand_spend(self, logged_in_admin):
        assert logged_in_admin.get("/api/tickets/brand-spend").status_code == 200


class TestRolesSinAccesoPresupuestos:
    """usuario y colaborador_mkt no tienen permisos de presupuestos en el
    catálogo: no deben listar tickets y sus tickets deben nacer PENDIENTES —
    nunca auto-aprobados con descuento inmediato del ciclo (regresión de la
    auditoría de seguridad 2026-08-18)."""

    def test_usuario_no_puede_listar_tickets(self, logged_in_usuario, db, creator_a, brand_a):
        make_ticket(db, creator=creator_a, brand=brand_a, amount=75)
        assert logged_in_usuario.get("/api/tickets/").status_code == 403

    def test_colaborador_mkt_no_puede_listar_tickets(self, logged_in_colaborador_mkt, db, creator_a, brand_a):
        make_ticket(db, creator=creator_a, brand=brand_a, amount=75)
        assert logged_in_colaborador_mkt.get("/api/tickets/").status_code == 403

    def test_usuario_ticket_nace_pendiente_y_no_descuenta_ciclo(self, logged_in_usuario, db, creator_a, brand_a):
        resp = logged_in_usuario.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "500"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pendiente"
        # Un pendiente nunca descuenta: el ciclo del creador queda sin gasto.
        ciclo = crud.get_or_create_cycle_for_date(db, creator_a, date.today())
        assert ciclo.spent == 0

    def test_colaborador_mkt_ticket_nace_pendiente(self, logged_in_colaborador_mkt, creator_a, brand_a):
        resp = logged_in_colaborador_mkt.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "500"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pendiente"

    def test_admin_ticket_sigue_auto_aprobado(self, logged_in_admin, creator_a, brand_a):
        resp = logged_in_admin.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "aprobado"


class TestDashboardPermissions:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/dashboard/summary",
            "/api/dashboard/monthly-spend",
            "/api/dashboard/creator-usage",
            "/api/dashboard/general-expenses-monthly",
            "/api/dashboard/top-expenses",
        ],
    )
    def test_creador_forbidden(self, logged_in_creador, path):
        assert logged_in_creador.get(path).status_code == 403

    @pytest.mark.parametrize(
        "path",
        [
            "/api/dashboard/summary",
            "/api/dashboard/monthly-spend",
            "/api/dashboard/creator-usage",
            "/api/dashboard/general-expenses-monthly",
            "/api/dashboard/top-expenses",
        ],
    )
    def test_admin_allowed(self, logged_in_admin, path):
        assert logged_in_admin.get(path).status_code == 200

    @pytest.mark.parametrize(
        "path",
        [
            "/api/dashboard/summary",
            "/api/dashboard/monthly-spend",
            "/api/dashboard/creator-usage",
            "/api/dashboard/general-expenses-monthly",
            "/api/dashboard/top-expenses",
        ],
    )
    def test_marketing_presupuestos_allowed(self, logged_in_marketing_presupuestos, path):
        assert logged_in_marketing_presupuestos.get(path).status_code == 200


class TestMarketingPresupuestosPermissions:
    """`marketing_presupuestos` debe tener acceso completo a Presupuestos y
    cero acceso a Equipos/usuarios/auditoría (docs/asignaciones/prompt-rbac-redefinicion.md)."""

    def test_accede_a_todo_presupuestos(self, logged_in_marketing_presupuestos, creator_a, brand_a):
        client = logged_in_marketing_presupuestos
        assert client.get("/api/dashboard/summary").status_code == 200
        assert client.get("/api/dashboard/monthly-spend").status_code == 200
        assert client.get("/api/dashboard/creator-usage").status_code == 200
        assert client.get("/api/dashboard/general-expenses-monthly").status_code == 200
        assert client.get("/api/creators/kpi").status_code == 200
        assert client.get("/api/creators/").status_code == 200
        assert client.get("/api/brands/").status_code == 200
        assert client.get("/api/tickets/").status_code == 200
        assert client.get("/api/tickets/brand-spend").status_code == 200
        assert client.get("/api/general-expenses/").status_code == 200

    def test_puede_crear_ticket(self, logged_in_marketing_presupuestos, creator_a, brand_a):
        resp = logged_in_marketing_presupuestos.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201

    def test_puede_descargar_comprobante_de_cualquier_creador(
        self, logged_in_marketing_presupuestos, db, creator_a, brand_a
    ):
        ticket = make_ticket(db, creator=creator_a, brand=brand_a, amount=75)
        resp = logged_in_marketing_presupuestos.get(f"/api/tickets/file/{ticket.id}")
        assert resp.status_code == 200

    def test_cero_acceso_a_equipos(self, logged_in_marketing_presupuestos):
        client = logged_in_marketing_presupuestos
        assert client.get("/api/equipment/").status_code == 403
        assert client.get("/api/loans/").status_code == 403

    def test_cero_acceso_a_usuarios_y_auditoria(self, logged_in_marketing_presupuestos):
        client = logged_in_marketing_presupuestos
        assert client.get("/api/users/").status_code == 403
        assert client.get("/api/audit-logs/").status_code == 403


class TestMarketingAdminPermissions:
    """`marketing_admin` (organigrama de accesos jul-2026): Presupuestos completo
    + Equipos completo, SIN aprobacion (esa sigue siendo exclusiva de admin)."""

    def test_accede_a_todo_presupuestos(self, logged_in_marketing_admin):
        client = logged_in_marketing_admin
        assert client.get("/api/dashboard/summary").status_code == 200
        assert client.get("/api/creators/kpi").status_code == 200
        assert client.get("/api/tickets/brand-spend").status_code == 200
        assert client.get("/api/general-expenses/").status_code == 200

    def test_accede_a_inventario_y_prestamos_de_equipos(self, logged_in_marketing_admin):
        client = logged_in_marketing_admin
        assert client.get("/api/equipment/").status_code == 200
        resp = client.post(
            "/api/loans/", json={"motivo": "Prueba", "fecha_regreso_esperada": "2026-12-31"}
        )
        assert resp.status_code == 201

    def test_no_puede_autorizar_entregas(self, logged_in_marketing_admin):
        # Sin paquete APROBADOR_EQUIPO: no tiene equipos_aprobacion:*, aunque
        # el prestamo no exista el 403 de permiso debe ganarle al 404.
        resp = logged_in_marketing_admin.post("/api/loans/999999/autorizar-entrega")
        assert resp.status_code == 403

    def test_cero_acceso_a_usuarios_y_auditoria(self, logged_in_marketing_admin):
        client = logged_in_marketing_admin
        assert client.get("/api/users/").status_code == 403
        assert client.get("/api/audit-logs/").status_code == 403


class TestMarketingBasicoPermissions:
    """`marketing_basico` (organigrama de accesos jul-2026): solo subir tickets
    propios y solicitar prestamos de equipo; ve unicamente lo suyo."""

    def test_puede_crear_ticket_y_solicitar_prestamo(self, logged_in_marketing_basico, creator_a, brand_a):
        client = logged_in_marketing_basico
        resp = client.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 201

        resp = client.post(
            "/api/loans/", json={"motivo": "Prueba", "fecha_regreso_esperada": "2026-12-31"}
        )
        assert resp.status_code == 201

    def test_ve_solo_los_tickets_que_el_mismo_subio(
        self, logged_in_marketing_basico, logged_in_admin, creator_a, brand_a
    ):
        # El admin sube un ticket ajeno; marketing_basico sube el suyo.
        logged_in_admin.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "999"},
            files={"file": ("ajeno.pdf", b"%PDF-1.4", "application/pdf")},
        )
        propio = logged_in_marketing_basico.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("propio.pdf", b"%PDF-1.4", "application/pdf")},
        ).json()

        vistos = logged_in_marketing_basico.get("/api/tickets/").json()
        assert [t["id"] for t in vistos] == [propio["id"]]

    def test_no_puede_descargar_comprobante_ajeno(
        self, logged_in_marketing_basico, admin_user, db, creator_a, brand_a
    ):
        # actor_user_id explicito y distinto del propio: el default de
        # make_ticket (id=1) puede coincidir por accidente con el propio
        # usuario en una DB de prueba aislada, y el ticket dejaria de ser
        # "ajeno" de verdad.
        ticket_ajeno = make_ticket(db, creator=creator_a, brand=brand_a, amount=75, actor_user_id=admin_user.id)
        resp = logged_in_marketing_basico.get(f"/api/tickets/file/{ticket_ajeno.id}")
        assert resp.status_code == 403

    def test_sin_acceso_a_dashboards_ni_gestion(self, logged_in_marketing_basico):
        client = logged_in_marketing_basico
        assert client.get("/api/dashboard/summary").status_code == 403
        assert client.get("/api/creators/kpi").status_code == 403
        assert client.get("/api/tickets/brand-spend").status_code == 403
        assert client.get("/api/general-expenses/").status_code == 403
        assert client.post("/api/brands/", json={"name": "Nueva"}).status_code == 403

    def test_sin_acceso_a_inventario_de_equipos(self, logged_in_marketing_basico):
        # Tiene equipos_prestamos:solicitar,ver_propios pero NO equipos_inventario.
        assert logged_in_marketing_basico.get("/api/equipment/").status_code == 403


class TestTicketDeletePermissions:
    def test_creador_cannot_soft_delete(self, logged_in_admin, logged_in_creador, creator_a, brand_a):
        resp = logged_in_admin.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        ).json()
        assert logged_in_creador.post(f"/api/tickets/{resp['id']}/soft-delete").status_code == 403

    def test_admin_can_soft_and_hard_delete(self, logged_in_admin, creator_a, brand_a):
        resp = logged_in_admin.post(
            "/api/tickets/",
            data={"creator_id": str(creator_a.id), "brand_id": str(brand_a.id), "amount": "50"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        ).json()
        assert logged_in_admin.post(f"/api/tickets/{resp['id']}/soft-delete").status_code == 200
        assert logged_in_admin.delete(f"/api/tickets/{resp['id']}/permanent").status_code == 200


class TestGeneralExpensesPermissions:
    def test_creador_cannot_create(self, logged_in_creador):
        resp = logged_in_creador.post(
            "/api/general-expenses/",
            data={"brand_id": "1", "amount": "100", "description": "x"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 403

    def test_creador_cannot_list(self, logged_in_creador):
        assert logged_in_creador.get("/api/general-expenses/").status_code == 403

    def test_admin_can_create_and_list(self, logged_in_admin, brand_a):
        create_resp = logged_in_admin.post(
            "/api/general-expenses/",
            data={"brand_id": str(brand_a.id), "amount": "100", "description": "x"},
            files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert create_resp.status_code == 201
        assert logged_in_admin.get("/api/general-expenses/").status_code == 200
