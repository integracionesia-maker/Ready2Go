"""Correo y recordatorios (S6 / WP6).

Criterios de cierre del reparto: idempotencia (reintentar no duplica correos) y
que un SMTP caido **no** tumbe el registro del prestamo.
"""

import smtplib
from datetime import date

import pytest

import seed_equipos
from app import mailer, notificaciones
from app import plantillas_correo as pl
from app.models_equipos import EstadoNotificacion, EstadoPrestamo, NotificationLog

from .conftest import crear_prestamo, logueado, subir, usuario_con
from ..conftest import PASSWORD_SUPERADMIN


@pytest.fixture
def inventario(db, catalogo):
    seed_equipos.sembrar_equipos(db, verbose=False)
    seed_equipos.sembrar_empresas(db, verbose=False)
    return db


@pytest.fixture
def smtp_configurado(monkeypatch):
    """Notificaciones encendidas y apuntando a un servidor de mentira."""
    monkeypatch.setenv("NOTIF_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.pruebas.local")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "gocreate@grupo-ortiz.com")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://gocreate.grupo-ortiz.com")
    return True


@pytest.fixture
def smtp_falso(monkeypatch, smtp_configurado):
    """Captura los correos en vez de mandarlos."""
    enviados: list[dict] = []

    class _Servidor:
        def __init__(self, host, port, timeout=None):
            self.host, self.port = host, port

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self, context=None):
            pass

        def login(self, user, password):
            pass

        def send_message(self, mensaje):
            enviados.append(
                {
                    "to": mensaje["To"],
                    "from": mensaje["From"],
                    "subject": mensaje["Subject"],
                    "body": mensaje.get_body(("plain",)).get_content(),
                    "adjuntos": [p.get_filename() for p in mensaje.iter_attachments()],
                }
            )

    monkeypatch.setattr(smtplib, "SMTP", _Servidor)
    return enviados


@pytest.fixture
def ana(inventario, db):
    return usuario_con(db, username="ana.ruiz")


@pytest.fixture
def melisa(inventario, db):
    return usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))


def _confirmado(cliente, equipment_ids=(1,)):
    loan_id = cliente.post(
        "/api/loans/",
        json={
            "area": "Contenido",
            "empresa": "MERCASYSTEM SA DE CV",
            "motivo": "Live Plaza Madero",
            "fecha_entrega": "2026-07-25",
            "fecha_regreso_esperada": "2026-07-30",
        },
    ).json()["id"]
    for equipment_id in equipment_ids:
        ficha = cliente.post(
            f"/api/loans/{loan_id}/items", json={"equipment_id": equipment_id}
        ).json()
        item_id = ficha["items"][-1]["id"]
        subir(cliente, loan_id, "foto_entrega_frente", item_id)
        subir(cliente, loan_id, "foto_entrega_atras", item_id)
    subir(cliente, loan_id, "firma_entrega")
    subir(cliente, loan_id, "firma_responsable")
    cliente.post(f"/api/loans/{loan_id}/confirmar")
    return loan_id


# ── Corta-circuito ──────────────────────────────────────────────────────────


def test_apagado_no_abre_socket(monkeypatch):
    """`NOTIF_ENABLED=false` es un corta-circuito real, no un log condicional."""
    monkeypatch.setenv("NOTIF_ENABLED", "false")
    monkeypatch.setenv("SMTP_HOST", "smtp.pruebas.local")
    monkeypatch.setenv("SMTP_FROM", "x@y.com")

    def _explota(*_a, **_k):
        raise AssertionError("no deberia haberse abierto una conexion")

    monkeypatch.setattr(smtplib, "SMTP", _explota)

    resultado = mailer.enviar("alguien@grupo-ortiz.com", "Asunto", "Cuerpo")
    assert resultado.enviado is False
    assert resultado.omitido is True


def test_apagado_por_defecto(monkeypatch):
    """Un entorno nuevo no manda correo a nadie del area por arrancar."""
    monkeypatch.delenv("NOTIF_ENABLED", raising=False)
    assert mailer.config().habilitado is False


def test_sin_smtp_host_se_omite(monkeypatch):
    monkeypatch.setenv("NOTIF_ENABLED", "true")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert mailer.enviar("a@b.com", "x", "y").omitido is True


def test_el_mailer_nunca_levanta(monkeypatch, smtp_configurado):
    def _explota(*_a, **_k):
        raise smtplib.SMTPServerDisconnected("servidor caido")

    monkeypatch.setattr(smtplib, "SMTP", _explota)

    resultado = mailer.enviar("a@grupo-ortiz.com", "Asunto", "Cuerpo")
    assert resultado.enviado is False
    assert resultado.omitido is False
    assert "SMTPServerDisconnected" in resultado.motivo


# ── Un SMTP caido no tumba el prestamo ──────────────────────────────────────


def test_smtp_caido_no_tumba_el_registro_del_prestamo(inventario, ana, melisa, monkeypatch, smtp_configurado, db):
    """Criterio de cierre de S6. El equipo ya salio por la puerta: que el correo
    falle no puede deshacer eso."""
    def _explota(*_a, **_k):
        raise smtplib.SMTPConnectError(421, "servidor caido")

    monkeypatch.setattr(smtplib, "SMTP", _explota)

    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)

    ficha = cliente.get(f"/api/loans/{loan_id}").json()
    assert ficha["estado"] == EstadoPrestamo.PRESTADO.value
    assert ficha["folio"] == "CE-0001"
    assert ficha["responsiva"]["version"] == 1

    # Y queda registro de que el correo se intento y fallo.
    filas = db.query(NotificationLog).filter(NotificationLog.loan_id == loan_id).all()
    assert filas, "no quedo registro del intento"
    assert all(f.estado == EstadoNotificacion.FALLIDO.value for f in filas)
    assert all("SMTPConnectError" in (f.error or "") for f in filas)


# ── Idempotencia ────────────────────────────────────────────────────────────


def test_encolar_dos_veces_no_duplica(inventario, ana, melisa, db):
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0050")
    notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)
    notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)

    assert db.query(NotificationLog).count() == 1


def test_lo_ya_enviado_no_se_vuelve_a_encolar(inventario, ana, melisa, db):
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0051")
    fila = notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)[0]
    fila.estado = EstadoNotificacion.ENVIADO.value
    db.commit()

    assert notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None) == []
    assert db.query(NotificationLog).count() == 1


def test_la_base_impide_dos_avisos_iguales(inventario, ana, db):
    from sqlalchemy.exc import IntegrityError

    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0052")
    for _ in range(2):
        db.add(
            NotificationLog(
                loan_id=prestamo.id,
                destinatario="mel@grupo-ortiz.com",
                tipo=pl.TIPO_CONFIRMADO_APROBADOR,
                canal="email",
            )
        )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_confirmar_dos_veces_no_manda_el_correo_dos_veces(
    inventario, ana, melisa, smtp_falso, db
):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    cuantos = len(smtp_falso)

    cliente.post(f"/api/loans/{loan_id}/confirmar")  # 409, no reenvía
    assert len(smtp_falso) == cuantos


# ── Destinatarios por rol ───────────────────────────────────────────────────


def test_los_aprobadores_salen_de_la_base_no_de_una_constante(inventario, db):
    """§10.20: la maqueta tenia el correo de Melisa escrito en el JavaScript."""
    mel = usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))
    usuario_con(db, username="emily")  # sin el aditivo

    correos = [u.email for u in notificaciones.aprobadores(db)]
    assert correos == [mel.email]


def test_revocar_el_aditivo_saca_a_la_persona_de_los_destinatarios(inventario, db):
    from app import crud_rbac

    mel = usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))
    assert notificaciones.aprobadores(db)

    crud_rbac.revocar(db, mel.id, "APROBADOR_EQUIPO")
    assert notificaciones.aprobadores(db) == []


def test_el_superadmin_no_recibe_el_ruido(inventario, db, superadmin_user):
    usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))
    correos = [u.username for u in notificaciones.aprobadores(db)]
    assert "superadmin" not in correos


def test_sin_aprobadores_lo_dice_en_el_log(inventario, db, caplog):
    """Que se vea. Escribir un correo de respaldo en el codigo seria volver al
    hardcode que el plan prohibe."""
    import logging

    with caplog.at_level(logging.WARNING):
        assert notificaciones.aprobadores(db) == []
    assert any("autorizar_entrega" in r.message for r in caplog.records)


def test_en_modo_legacy_no_hay_aprobadores(inventario, db, monkeypatch, caplog):
    """Consecuencia operativa del rollback de §13: los aditivos no aplican, asi
    que `equipos_aprobacion` no lo tiene nadie y ningun aviso sale."""
    import logging

    usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))
    assert notificaciones.aprobadores(db)

    monkeypatch.setenv("RBAC_MODO", "legacy")
    with caplog.at_level(logging.WARNING):
        assert notificaciones.aprobadores(db) == []
    # `getMessage()` aplica los argumentos; `record.message` solo existe si algo
    # ya formateo el registro.
    assert any("RBAC_MODO=legacy" in r.getMessage() for r in caplog.records)


# ── Contenido de los correos ────────────────────────────────────────────────


def test_hay_cinco_plantillas():
    assert len(pl.PLANTILLAS) == 5


def test_ninguna_plantilla_lleva_emojis(inventario, ana, db):
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0060")
    datos = notificaciones.datos_de_prestamo(db, prestamo)

    for tipo in pl.PLANTILLAS:
        asunto, cuerpo = pl.construir(tipo, datos)
        for texto in (asunto, cuerpo):
            assert all(ord(c) < 0x2190 for c in texto), f"{tipo}: hay un emoji"


def test_el_aviso_de_confirmacion_lleva_lo_que_pide_el_plan(inventario, ana, melisa, smtp_falso):
    cliente = logueado("ana.ruiz")
    _confirmado(cliente)

    aprobador = next(c for c in smtp_falso if c["to"] == melisa.email)
    assert "CE-0001" in aprobador["subject"]
    for dato in ("ana.ruiz", "Contenido", "Live Plaza Madero", "2026-07-25", "iPhone 17 Pro"):
        assert dato in aprobador["body"], dato
    assert "/equipos/aprobaciones" in aprobador["body"]
    # PDF adjunto (§7): el aprobador tiene que poder leer la carta sin entrar.
    assert aprobador["adjuntos"] == ["CE-0001_v1.pdf"]


def test_el_responsable_recibe_su_copia_del_pdf(inventario, ana, melisa, smtp_falso):
    cliente = logueado("ana.ruiz")
    _confirmado(cliente)

    copia = next(c for c in smtp_falso if c["to"] == ana.email)
    assert "CE-0001" in copia["subject"]
    assert copia["adjuntos"] == ["CE-0001_v1.pdf"]


def test_el_remitente_lleva_nombre_visible(inventario, ana, melisa, smtp_falso):
    logueado("ana.ruiz")
    _confirmado(logueado("ana.ruiz"))
    assert smtp_falso[0]["from"].startswith("GOCreate")


def test_la_devolucion_avisa_a_los_aprobadores(inventario, ana, melisa, smtp_falso):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]
    subir(cliente, loan_id, "foto_dev_frente", item_id)
    subir(cliente, loan_id, "foto_dev_atras", item_id)
    smtp_falso.clear()

    cliente.post(f"/api/loans/{loan_id}/devolucion", json={"items": [{"loan_item_id": item_id}]})

    assert [c["to"] for c in smtp_falso] == [melisa.email]
    assert "Devolucion registrada" in smtp_falso[0]["subject"]


def test_la_confirmacion_avisa_al_responsable_con_el_resultado(
    inventario, ana, melisa, smtp_falso
):
    cliente = logueado("ana.ruiz")
    loan_id = _confirmado(cliente)
    item_id = cliente.get(f"/api/loans/{loan_id}").json()["items"][0]["id"]
    subir(cliente, loan_id, "foto_dev_frente", item_id)
    subir(cliente, loan_id, "foto_dev_atras", item_id)
    cliente.post(f"/api/loans/{loan_id}/devolucion", json={"items": [{"loan_item_id": item_id}]})
    smtp_falso.clear()

    cliente_mel = logueado("melisa")
    cliente_mel.post(
        f"/api/loans/{loan_id}/confirmar-devolucion",
        json={"decisiones": [{"loan_item_id": item_id, "decision": "danado", "nota": "Lente rayado"}]},
    )

    aviso = next(c for c in smtp_falso if c["to"] == ana.email)
    assert "incidencias" in aviso["subject"]
    assert "Lente rayado" in aviso["body"]


# ── Recordatorio de vencimiento ─────────────────────────────────────────────


def test_el_tipo_de_vencimiento_lleva_el_dia(inventario):
    assert notificaciones.tipo_vencimiento(date(2026, 7, 30)) == "vencimiento:2026-07-30"


def test_el_dia_del_recordatorio_sale_de_cdmx(inventario):
    """Con UTC, despues de las 18:00 CDMX el dia ya es el siguiente y saldrian
    dos avisos para el mismo dia civil."""
    from freezegun import freeze_time

    with freeze_time("2026-07-31 03:00:00"):  # 2026-07-30 21:00 en CDMX
        assert notificaciones.tipo_vencimiento() == "vencimiento:2026-07-30"


def _prestamo_vencido(db, ana, folio="CE-0070"):
    return crear_prestamo(
        db,
        responsable=ana,
        folio=folio,
        estado=EstadoPrestamo.PRESTADO.value,
        fecha_regreso_esperada=date(2026, 7, 20),
    )


def test_el_recordatorio_encuentra_los_atrasados(inventario, ana, melisa, db):
    from scripts import recordatorios_vencimiento as recordatorios

    _prestamo_vencido(db, ana)
    crear_prestamo(
        db,
        responsable=ana,
        folio="CE-0071",
        estado=EstadoPrestamo.PRESTADO.value,
        fecha_regreso_esperada=date(2026, 12, 31),
    )

    atrasados = recordatorios.prestamos_atrasados(db, date(2026, 7, 28))
    assert [p.folio for p in atrasados] == ["CE-0070"]


def test_un_prestamo_ya_devuelto_no_recibe_recordatorio(inventario, ana, db):
    """Ya volvio fisicamente; lo que falta es el visto bueno del aprobador.
    Mandarle "devuelve el equipo" seria confundir a la persona."""
    from scripts import recordatorios_vencimiento as recordatorios

    crear_prestamo(
        db,
        responsable=ana,
        folio="CE-0072",
        estado=EstadoPrestamo.PENDIENTE_CONFIRMACION.value,
        fecha_regreso_esperada=date(2026, 7, 20),
    )
    assert recordatorios.prestamos_atrasados(db, date(2026, 7, 28)) == []


def test_dos_corridas_el_mismo_dia_no_duplican(inventario, ana, melisa, db):
    from scripts import recordatorios_vencimiento as recordatorios

    _prestamo_vencido(db, ana)
    recordatorios.correr(db, simular=True, referencia=date(2026, 7, 28))
    recordatorios.correr(db, simular=True, referencia=date(2026, 7, 28))

    filas = db.query(NotificationLog).all()
    assert len(filas) == 2  # responsable + aprobadora, una vez cada uno


def test_al_dia_siguiente_si_manda_otro(inventario, ana, melisa, db):
    """Es un recordatorio DIARIO. Con un tipo constante, el UNIQUE lo mandaria
    una sola vez en la vida del prestamo y nadie se enteraria."""
    from scripts import recordatorios_vencimiento as recordatorios

    _prestamo_vencido(db, ana)
    recordatorios.correr(db, simular=True, referencia=date(2026, 7, 28))
    recordatorios.correr(db, simular=True, referencia=date(2026, 7, 29))

    tipos = {f.tipo for f in db.query(NotificationLog).all()}
    assert tipos == {"vencimiento:2026-07-28", "vencimiento:2026-07-29"}


def test_el_recordatorio_va_al_responsable_y_a_los_aprobadores(inventario, ana, melisa, db):
    from scripts import recordatorios_vencimiento as recordatorios

    prestamo = _prestamo_vencido(db, ana)
    correos = recordatorios.destinatarios_de(db, prestamo)
    assert set(correos) == {ana.email, melisa.email}


def test_el_recordatorio_dice_cuantos_dias(inventario, ana, melisa, db):
    from freezegun import freeze_time

    prestamo = _prestamo_vencido(db, ana)
    with freeze_time("2026-07-28 18:00:00"):
        datos = notificaciones.datos_de_prestamo(db, prestamo)
        asunto, cuerpo = pl.construir(notificaciones.tipo_vencimiento(), datos)

    assert "8 dias de atraso" in asunto
    assert "CE-0070" in asunto


# ── Reintentos ──────────────────────────────────────────────────────────────


def test_reintentar_reusa_la_misma_fila(inventario, ana, melisa, db, monkeypatch, smtp_configurado):
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0080")
    fila = notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)[0]

    def _explota(*_a, **_k):
        raise smtplib.SMTPServerDisconnected("caido")

    monkeypatch.setattr(smtplib, "SMTP", _explota)
    notificaciones.reintentar_fallidos(db)
    db.refresh(fila)

    assert db.query(NotificationLog).count() == 1
    assert fila.intentos == 1
    assert fila.estado == EstadoNotificacion.FALLIDO.value


def test_no_se_reintenta_indefinidamente(inventario, ana, melisa, db, monkeypatch, smtp_configurado):
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0081")
    fila = notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)[0]

    def _explota(*_a, **_k):
        raise smtplib.SMTPServerDisconnected("caido")

    monkeypatch.setattr(smtplib, "SMTP", _explota)
    for _ in range(notificaciones.MAX_INTENTOS + 2):
        notificaciones.reintentar_fallidos(db)

    db.refresh(fila)
    assert fila.intentos == notificaciones.MAX_INTENTOS


def test_apagado_no_gasta_intentos(inventario, ana, melisa, db, monkeypatch):
    """Estar apagado no es un fallo: la fila espera a que haya cuenta SMTP."""
    monkeypatch.setenv("NOTIF_ENABLED", "false")
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0082")
    fila = notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)[0]

    notificaciones.reintentar_fallidos(db)
    db.refresh(fila)
    assert fila.intentos == 0
    assert fila.estado == EstadoNotificacion.PENDIENTE.value


# ── Diagnostico ─────────────────────────────────────────────────────────────


def test_el_diagnostico_es_solo_del_superadmin(inventario, ana, melisa):
    assert logueado("ana.ruiz").get("/api/notifications/").status_code == 403
    assert logueado("melisa").get("/api/notifications/").status_code == 403


def test_la_config_no_expone_la_contrasena(inventario, db, superadmin_user, monkeypatch, smtp_configurado):
    monkeypatch.setenv("SMTP_PASSWORD", "secreto-de-verdad")
    usuario_con(db, username="melisa", aditivos=("APROBADOR_EQUIPO",))

    cuerpo = logueado("superadmin", PASSWORD_SUPERADMIN).get("/api/notifications/config").json()

    assert cuerpo["smtp_password_configurada"] is True
    assert "secreto-de-verdad" not in str(cuerpo)
    assert cuerpo["notif_enabled"] is True
    assert cuerpo["smtp_host"] == "smtp.pruebas.local"
    # El dato que mas cuesta descubrir cuando "no llegan los correos".
    assert cuerpo["aprobadores_resueltos"] == 1


def test_el_listado_de_diagnostico_filtra(inventario, ana, melisa, db, superadmin_user):
    prestamo = crear_prestamo(db, responsable=ana, folio="CE-0090")
    notificaciones.encolar(db, pl.TIPO_CONFIRMADO_APROBADOR, prestamo, None)

    cliente = logueado("superadmin", PASSWORD_SUPERADMIN)
    todas = cliente.get("/api/notifications/").json()
    assert todas["total"] == 1
    assert todas["items"][0]["tipo"] == pl.TIPO_CONFIRMADO_APROBADOR

    assert cliente.get("/api/notifications/", params={"estado": "enviado"}).json()["total"] == 0
    assert cliente.get(
        "/api/notifications/", params={"loan_id": prestamo.id}
    ).json()["total"] == 1
