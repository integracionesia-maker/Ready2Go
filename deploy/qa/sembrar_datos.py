#!/usr/bin/env python3
"""Siembra el entorno QA de GOCreate con datos 100% ficticios.

Uso (SIEMPRE desde la carpeta backend/ de la release del QA, igual que uvicorn:
las rutas de la base y de uploads/ son relativas al directorio de trabajo):

    cd /opt/go/gocreate-qa/releases/<release>/backend
    python ../../../../deploy/qa/sembrar_datos.py --credenciales /ruta/credenciales_qa.txt

Lo normal es no llamarlo a mano: `reiniciar_datos.sh` lo hace despues de vaciar
la base.

Que hace
--------
1. Siembra el catalogo RBAC y crea marcas, creadores, rubros, razones sociales
   e inventario de equipos inventados.
2. Crea un usuario por cada rol base y por cada paquete aditivo, con contrasenas
   aleatorias (nunca fijas en el codigo). Las contrasenas se escriben SOLO en el
   archivo `--credenciales` (permisos 600); no se imprimen.
3. Genera ~6 meses de historial de tickets, gastos generales y gastos operativos,
   con comprobantes de imagen ficticios.
4. Recorre el ciclo de vida completo de Control de Equipos **por la API real**
   (TestClient en proceso), no insertando filas a mano: asi los folios, eventos,
   firmas y cartas responsivas PDF son exactamente los que produce el sistema.

Garantias de seguridad (QA-09, QA-10, QA-13)
--------------------------------------------
* Se niega a correr si `QA_MODE` no esta activo: es el freno contra sembrar por
  error la base de produccion.
* Se niega a correr si la base resuelve dentro de `/opt/go/gocreate/` (la ruta de
  produccion; `/opt/go/gocreate-qa/` NO coincide).
* Fuerza `NOTIF_ENABLED=false` antes de importar la app: sembrar no manda correo
  aunque el .env diga otra cosa.
* Si la base ya tiene usuarios, no hace nada (idempotente). Para empezar de cero
  use `reiniciar_datos.sh`.
"""

from __future__ import annotations

import argparse
import os
import random
import secrets
import sys
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

# ── Freno 1: entorno. Antes de importar nada de la app. ─────────────────────
sys.path.insert(0, str(Path.cwd()))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path.cwd() / ".env")

if os.getenv("QA_MODE", "").strip().lower() not in ("1", "true", "yes", "si", "on"):
    sys.exit(
        "ABORTADO: QA_MODE no esta activo en este entorno. Este script solo "
        "siembra el QA; jamas debe correr contra produccion."
    )
# El sembrado no manda correo, diga lo que diga el .env (el .env no se pisa si
# la variable ya existe, asi que se fija aqui, antes de importar la app).
os.environ["NOTIF_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app import crud, crud_rbac, models, security  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402  (registra todas las tablas y routers)
from app.models_equipos import (  # noqa: E402
    CondicionEquipo,
    Empresa,
    Equipment,
    EquipmentAudit,
    EstadoFisico,
    EstadoOperativo,
    Loan,
)
from app.models_operativos import OperationalExpense  # noqa: E402

# ── Freno 2: la base no puede ser la de produccion. ─────────────────────────
_RUTA_PROD = "/opt/go/gocreate/"
_db_real = str(Path(engine.url.database or "").resolve()).replace("\\", "/")
if _db_real.startswith(_RUTA_PROD):
    sys.exit(f"ABORTADO: la base resuelve a {_db_real}, que es la de produccion.")

random.seed(20261120)
HOY = date.today()
DIR_TICKETS = Path("./uploads/tickets")

# ─────────────────────────────────────────────────────────────────────────────
# Datos ficticios
# ─────────────────────────────────────────────────────────────────────────────

MARCAS = [
    ("Aurora", "alta"), ("Cobalto", "alta"), ("Delta Sport", "media"),
    ("Esmeralda", "media"), ("Fenix Labs", "alta"), ("Galata", "baja"),
    ("Horizonte", "media"), ("Icaro", "baja"),
]

CREADORES = [  # (nombre, presupuesto por ciclo, periodo)
    ("Creador QA Uno", 15000.0, "mensual"), ("Creador QA Dos", 12000.0, "mensual"),
    ("Creador QA Tres", 10000.0, "mensual"), ("Creador QA Cuatro", 8000.0, "semanal"),
    ("Creador QA Cinco", 20000.0, "mensual"), ("Creador QA Seis", 9000.0, "semanal"),
    ("Creador QA Siete", 11000.0, "mensual"), ("Creador QA Ocho", 7000.0, "semanal"),
]

RUBROS = ["E-commerce", "IA", "Aplicaciones", "Campañas", "Activaciones"]

EMPRESAS = [
    ("EMPRESA QA UNO SA DE CV", "Calle Ficticia 100", "Ciudad de Mexico", "QAU010101AA1"),
    ("EMPRESA QA DOS SA DE CV", "Avenida Inventada 200", "Guadalajara", "QAD020202BB2"),
    ("EMPRESA QA TRES SA DE CV", "Boulevard Demo 300", "Monterrey", "QAT030303CC3"),
]

EQUIPOS = [  # (nombre, categoria, marca, modelo, codigo, accesorios)
    ("Camara Demo A", "Camara", "Marca Demo", "CAM-A", "QA-CAM-001", ["Bateria", "Cargador", "Tarjeta SD"]),
    ("Camara Demo B", "Camara", "Marca Demo", "CAM-B", "QA-CAM-002", ["Bateria", "Cargador"]),
    ("Lente Demo 24-70", "Lente", "Marca Demo", "LEN-2470", "QA-LEN-001", ["Tapa", "Parasol"]),
    ("Microfono Inalambrico Demo", "Audio", "Marca Demo", "MIC-W2", "QA-MIC-001", ["Receptor", "Transmisor", "Cable"]),
    ("Estabilizador Demo", "Estabilizador", "Marca Demo", "EST-3", "QA-EST-001", ["Base", "Cargador"]),
    ("Celular Demo Pro", "Celular", "Marca Demo", "CEL-P1", "QA-CEL-001", ["Cargador", "Cable"]),
    ("Celular Demo Plus", "Celular", "Marca Demo", "CEL-P2", "QA-CEL-002", ["Cargador", "Cable"]),
    ("Luz LED Demo", "Iluminacion", "Marca Demo", "LUZ-1", "QA-LUZ-001", ["Fuente", "Difusor"]),
    ("Tripie Demo", "Accesorios", "Marca Demo", "TRI-1", "QA-TRI-001", []),
    ("Laptop Demo 16", "Computo", "Marca Demo", "LAP-16", "QA-LAP-001", ["Cargador"]),
    ("Gimbal Demo", "Estabilizador", "Marca Demo", "GIM-2", "QA-GIM-001", ["Estuche"]),
    ("Dron Demo", "Aereo", "Marca Demo", "DRO-1", "QA-DRO-001", ["Control", "Baterias x3"]),
]

# (username, nombre, rol base, aditivos, indice de creador, que representa)
USUARIOS = [
    ("qa.superadmin", "QA Superadmin", "superadmin", (), None, "acceso total"),
    ("qa.admin", "QA Admin Marketing", "admin", (), None, "presupuestos + equipos completos, sin usuarios"),
    ("qa.mkt.presupuestos", "QA Marketing Presupuestos", "marketing_presupuestos", (), None, "solo presupuestos"),
    ("qa.mkt.equipos", "QA Marketing Equipos", "marketing_equipos", (), None, "solo equipos"),
    ("qa.mkt.admin", "QA Marketing Admin", "marketing_admin", (), None, "presupuestos + equipos de marketing"),
    ("qa.mkt.basico", "QA Marketing Basico", "marketing_basico", (), None, "vista basica"),
    ("qa.colaborador", "QA Colaborador", "colaborador_mkt", (), None, "pide equipo y ve lo propio"),
    ("qa.usuario", "QA Usuario", "usuario", (), None, "solo inicio y perfil"),
    ("qa.creador.1", "Creador QA Uno", "creador", (), 0, "sube tickets; beneficiario de equipos"),
    ("qa.creador.2", "Creador QA Dos", "creador", (), 1, "sube tickets; beneficiario de equipos"),
    ("qa.creador.3", "Creador QA Tres", "creador", (), 2, "sube tickets; beneficiario de equipos"),
    ("qa.creador.4", "Creador QA Cuatro", "creador", (), 3, "sube tickets; beneficiario de equipos"),
    ("qa.aprobadora", "QA Aprobadora de Equipo", "colaborador_mkt",
     ("APROBADOR_EQUIPO", "TITULAR_FIRMA_EQUIPO"), None, "autoriza entregas, confirma devoluciones, firma de entrega"),
    ("qa.custodio", "QA Custodio de Equipo", "usuario", ("CUSTODIO_EQUIPO",), None, "inventario"),
    ("qa.auditor", "QA Auditor", "usuario", ("AUDITOR",), None, "solo lectura global"),
    ("qa.aprobador.presupuestos", "QA Aprobador de Presupuestos", "usuario",
     ("APROBADOR_PRESUPUESTOS",), None, "valida tickets sin ser admin"),
    ("qa.admin.usuarios", "QA Admin de Usuarios", "admin", ("ADMIN_USUARIOS",), None, "administra cuentas (delegado)"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────


def imagen(texto: str, *, size=(640, 420), fondo=(236, 235, 224), formato="JPEG") -> bytes:
    """Imagen ficticia con el texto escrito, para comprobantes y fotos."""
    img = Image.new("RGB", size, fondo)
    dib = ImageDraw.Draw(img)
    dib.rectangle([8, 8, size[0] - 9, size[1] - 9], outline=(251, 103, 11), width=4)
    y = 30
    for linea in ("QA — DATO FICTICIO", *texto.split("\n")):
        dib.text((28, y), linea, fill=(38, 38, 38))
        y += 26
    buf = BytesIO()
    img.save(buf, format=formato)
    return buf.getvalue()


def firma_png() -> bytes:
    """Trazo aleatorio sobre fondo blanco: una firma inventada."""
    img = Image.new("RGB", (400, 150), (255, 255, 255))
    dib = ImageDraw.Draw(img)
    x, y = 20, 80
    puntos = [(x, y)]
    for _ in range(14):
        x += random.randint(15, 30)
        y = max(20, min(130, y + random.randint(-45, 45)))
        puntos.append((x, y))
    dib.line(puntos, fill=(20, 20, 20), width=3)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def guardar_comprobante(texto: str) -> tuple[str, str, str]:
    """Escribe una imagen en uploads/tickets/ (como upload_manager) y devuelve
    (nombre, ruta absoluta, mime)."""
    DIR_TICKETS.mkdir(parents=True, exist_ok=True)
    nombre = f"{secrets.token_hex(16)}.jpg"
    destino = DIR_TICKETS / nombre
    destino.write_bytes(imagen(texto))
    return nombre, str(destino.resolve()), "image/jpeg"


def leer_credenciales(ruta: Path | None) -> dict[str, str]:
    """Reutiliza las contrasenas de una siembra anterior: reiniciar los datos no
    debe obligar a re-entregar credenciales a la auditora."""
    previas: dict[str, str] = {}
    if ruta and ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip() or linea.startswith("#"):
                continue
            partes = linea.split("\t")
            if len(partes) >= 3:
                previas[partes[0]] = partes[2]
    return previas


# ─────────────────────────────────────────────────────────────────────────────
# Presupuestos: catalogos, usuarios e historial (directo a la base)
# ─────────────────────────────────────────────────────────────────────────────


def sembrar_catalogos(db):
    marcas = []
    for nombre, prioridad in MARCAS:
        m = models.Brand(name=nombre, priority=prioridad, is_active=True)
        db.add(m)
        marcas.append(m)
    creadores = []
    for nombre, monto, periodo in CREADORES:
        c = models.Creator(
            name=nombre, initial_budget=monto * 3, spent_budget=0.0,
            remaining_budget=monto * 3, cycle_budget_amount=monto,
            cycle_period=periodo, is_active=True,
        )
        db.add(c)
        creadores.append(c)
    for nombre in RUBROS:
        db.add(models.ExpenseRubro(nombre=nombre, is_active=True))
    for razon, direccion, ciudad, rfc in EMPRESAS:
        db.add(Empresa(razon_social=razon, direccion=direccion, ciudad=ciudad, rfc=rfc, is_active=True))
    db.commit()
    return marcas, creadores


def sembrar_usuarios(db, creadores, previas: dict[str, str]):
    """Crea un usuario por rol base y por paquete aditivo. Devuelve
    {username: (usuario, contrasena, rol, nota)}."""
    resultado = {}
    for username, nombre, rol, aditivos, idx_creador, nota in USUARIOS:
        clave = previas.get(username) or secrets.token_urlsafe(9)
        usuario = models.User(
            username=username,
            email=f"{username}@qa.gocreate.example",
            password_hash=security.hash_password(clave),
            full_name=nombre,
            role=rol,
            creator_id=creadores[idx_creador].id if idx_creador is not None else None,
            is_active=True,
            must_change_password=False,
        )
        db.add(usuario)
        db.flush()
        for paquete in aditivos:
            crud_rbac.conceder(db, usuario.id, paquete, granted_by=None)
        resultado[username] = (usuario, clave, rol, aditivos, nota)
    db.commit()
    return resultado


def sembrar_historial(db, marcas, creadores, usuarios):
    """~6 meses de tickets, gastos generales y gastos operativos."""
    admin = usuarios["qa.admin"][0]
    por_creador_user = {u.creator_id: u for (u, *_r) in usuarios.values() if u.creator_id}
    notas = ["Campana de redes", "Sesion de fotos", "Activacion en tienda", "Reel de producto",
             "Cobertura de evento", "Material de apoyo", "Edicion de video", "Transmision en vivo"]
    n_tickets = 0
    for creador in creadores:
        subio = por_creador_user.get(creador.id, admin)
        for mes_atras in range(6, -1, -1):
            for _ in range(random.randint(1, 3)):
                dias = max(0, mes_atras * 30 - random.randint(0, 28))
                fecha = HOY - timedelta(days=dias)
                reciente = dias <= 35
                suerte = random.random()
                estado = "pendiente" if (reciente and suerte < 0.45) else ("rechazado" if suerte > 0.9 else "aprobado")
                monto = float(random.randrange(800, 5200, 100))
                marca = random.choice(marcas)
                ciclo = crud.get_or_create_cycle_for_date(db, creador, fecha)
                nombre, ruta, mime = guardar_comprobante(f"Comprobante\n{creador.name}\n{marca.name}\n${monto:,.2f}")
                t = models.Ticket(
                    creator_id=creador.id, brand_id=marca.id, budget_cycle_id=ciclo.id,
                    amount=monto, status=estado, uploaded_by_user_id=subio.id,
                    file_name=nombre, file_path=ruta, mime_type=mime,
                    upload_date=datetime.combine(fecha, datetime.min.time()) + timedelta(hours=random.randint(9, 18)),
                    notes=random.choice(notas),
                )
                t.media.append(models.TicketMedia(file_name=nombre, file_path=ruta, mime_type=mime))
                if estado == "aprobado":
                    t.reviewed_by_user_id = admin.id
                    t.reviewed_at = t.upload_date + timedelta(hours=3)
                    ciclo.spent += monto
                elif estado == "rechazado":
                    t.reviewed_by_user_id = admin.id
                    t.reviewed_at = t.upload_date + timedelta(hours=3)
                    t.rejection_reason = "Comprobante ilegible (dato ficticio de QA)."
                db.add(t)
                n_tickets += 1
    db.commit()

    descripciones = ["Licencia de software", "Fotografo externo", "Produccion de video", "Hosting y dominio",
                     "Pauta digital", "Material impreso", "Envios y logistica", "Evento de lanzamiento"]
    for i in range(24):
        fecha = HOY - timedelta(days=random.randint(1, 180))
        nombre, ruta, mime = guardar_comprobante(f"Gasto general\n#{i + 1}")
        db.add(models.GeneralExpense(
            brand_id=random.choice(marcas).id, amount=float(random.randrange(400, 4000, 50)),
            description=random.choice(descripciones), file_name=nombre, file_path=ruta, mime_type=mime,
            upload_date=datetime.combine(fecha, datetime.min.time()), created_by_user_id=admin.id,
        ))
    rubros = db.query(models.ExpenseRubro).all()
    for i in range(18):
        fecha = HOY - timedelta(days=random.randint(1, 180))
        nombre, ruta, mime = guardar_comprobante(f"Gasto operativo\n#{i + 1}")
        db.add(OperationalExpense(
            rubro_id=random.choice(rubros).id, amount=float(random.randrange(300, 3500, 50)),
            description=random.choice(descripciones), fecha_gasto=fecha,
            file_name=nombre, file_path=ruta, mime_type=mime, created_by_user_id=admin.id,
        ))
    db.commit()
    return n_tickets


def sembrar_inventario(db, usuarios):
    admin = usuarios["qa.admin"][0]
    ids = []
    for nombre, cat, marca, modelo, codigo, accesorios in EQUIPOS:
        import json

        e = Equipment(
            nombre=nombre, categoria=cat, marca=marca, modelo=modelo, codigo=codigo,
            numero_serie=f"SN-QA-{codigo[-3:]}-{random.randint(1000, 9999)}",
            estado_operativo=EstadoOperativo.ACTIVO.value,
            accesorios_tipicos=json.dumps(accesorios, ensure_ascii=False),
        )
        db.add(e)
        db.flush()
        db.add(EquipmentAudit(
            equipment_id=e.id, condicion=CondicionEquipo.BUENO.value,
            estado_fisico=EstadoFisico.NUEVO.value,
            comentario="Ingreso al inventario (dato ficticio de QA).",
            fecha=HOY - timedelta(days=200), actor_user_id=admin.id,
        ))
        ids.append(e.id)
    db.commit()
    return ids


# ─────────────────────────────────────────────────────────────────────────────
# Control de Equipos: ciclo de vida por la API real
# ─────────────────────────────────────────────────────────────────────────────


class ErrorSembrado(RuntimeError):
    pass


def _ok(resp, que: str):
    if resp.status_code >= 400:
        raise ErrorSembrado(f"{que}: HTTP {resp.status_code} {resp.text[:300]}")
    return resp


def sesion(username: str, clave: str) -> TestClient:
    # https: con ENV=production las cookies llevan `Secure` y el cliente no las
    # reenviaria sobre http.
    c = TestClient(app, base_url="https://testserver")
    _ok(c.post("/api/auth/login", json={"identificador": username, "password": clave}), f"login {username}")
    return c


def subir(c, loan_id, kind, item_id=None):
    datos = {"kind": kind}
    if item_id is not None:
        datos["loan_item_id"] = str(item_id)
    if kind.startswith("firma"):
        archivo = ("firma.png", firma_png(), "image/png")
    else:
        archivo = ("foto.jpg", imagen(f"Foto ficticia\n{kind}\nprestamo {loan_id}"), "image/jpeg")
    _ok(c.post(f"/api/loans/{loan_id}/media", data=datos, files={"file": archivo}), f"subir {kind}")


def crear_prestamo(c, equipos, *, motivo, regreso, empresa=None, responsable_user_id=None):
    cuerpo = {"motivo": motivo, "fecha_regreso_esperada": regreso.isoformat(), "area": "Marketing"}
    if empresa:
        cuerpo["empresa"] = empresa
    if responsable_user_id:
        cuerpo["responsable_user_id"] = responsable_user_id
    loan_id = _ok(c.post("/api/loans/", json=cuerpo), "crear prestamo").json()["id"]
    for eq in equipos:
        ficha = _ok(c.post(f"/api/loans/{loan_id}/items", json={"equipment_id": eq}), "agregar equipo").json()
        item = ficha["items"][-1]["id"]
        subir(c, loan_id, "foto_entrega_frente", item)
        subir(c, loan_id, "foto_entrega_atras", item)
    return loan_id


def confirmar(c, loan_id):
    _ok(c.post(f"/api/loans/{loan_id}/confirmar"), "confirmar prestamo")


def firmar_todo(titular, beneficiario, loan_id):
    subir(titular, loan_id, "firma_entrega")
    subir(beneficiario, loan_id, "firma_responsable")


def devolver(c, loan_id):
    items = _ok(c.get(f"/api/loans/{loan_id}"), "leer prestamo").json()["items"]
    for it in items:
        subir(c, loan_id, "foto_dev_frente", it["id"])
        subir(c, loan_id, "foto_dev_atras", it["id"])
    _ok(c.post(f"/api/loans/{loan_id}/devolucion",
               json={"items": [{"loan_item_id": it["id"]} for it in items]}), "registrar devolucion")
    return [it["id"] for it in items]


def mover_fechas(db, loan_id, *, entrega=None, esperada=None, real=None):
    """La API siempre fecha 'hoy'; se reubica el prestamo en el pasado para que
    el historial tenga forma de historial (los eventos conservan su hora real)."""
    p = db.get(Loan, loan_id)
    if entrega is not None:
        p.fecha_entrega = entrega
    if esperada is not None:
        p.fecha_regreso_esperada = esperada
    if real is not None:
        p.fecha_regreso_real = real
    db.commit()


def sembrar_prestamos(db, usuarios, equipo_ids):
    s = {u: sesion(u, usuarios[u][1]) for u in (
        "qa.colaborador", "qa.mkt.equipos", "qa.creador.1", "qa.creador.2", "qa.aprobadora")}
    apr = s["qa.aprobadora"]
    emp = EMPRESAS[0][0]
    futuro = HOY + timedelta(days=10)
    e = equipo_ids
    fallos: list[str] = []

    def escenario(nombre, fn):
        try:
            fn()
            print(f"  + {nombre}")
        except Exception as exc:  # un escenario roto no debe tirar el resto
            fallos.append(f"{nombre}: {exc}")
            print(f"  ! {nombre}: {exc}")

    def completado(cliente, quien, equipos, motivo, dias_atras):
        lid = crear_prestamo(cliente, equipos, motivo=motivo, regreso=futuro, empresa=emp)
        confirmar(cliente, lid)
        firmar_todo(apr, cliente, lid)
        _ok(apr.post(f"/api/loans/{lid}/autorizar-entrega"), "autorizar")
        items = devolver(cliente, lid)
        _ok(apr.post(f"/api/loans/{lid}/confirmar-devolucion",
                     json={"decisiones": [{"loan_item_id": i, "decision": "ok"} for i in items]}), "confirmar devolucion")
        mover_fechas(db, lid, entrega=HOY - timedelta(days=dias_atras),
                     esperada=HOY - timedelta(days=dias_atras - 7), real=HOY - timedelta(days=dias_atras - 6))

    escenario("completado (colaborador, 2 equipos, hace 45 dias)",
              lambda: completado(s["qa.colaborador"], "qa.colaborador", [e[0], e[1]], "Campana de producto (QA)", 45))
    escenario("completado (marketing equipos, hace 20 dias)",
              lambda: completado(s["qa.mkt.equipos"], "qa.mkt.equipos", [e[2]], "Cobertura de evento (QA)", 20))

    def activo():
        lid = crear_prestamo(s["qa.creador.1"], [e[3], e[4]], motivo="Grabacion de contenido (QA)", regreso=futuro, empresa=emp)
        confirmar(s["qa.creador.1"], lid)
        firmar_todo(apr, s["qa.creador.1"], lid)
        _ok(apr.post(f"/api/loans/{lid}/autorizar-entrega"), "autorizar")
        mover_fechas(db, lid, entrega=HOY - timedelta(days=3))

    escenario("prestado en plazo (creador 1, 2 equipos)", activo)

    def atrasado():
        c = s["qa.colaborador"]
        lid = crear_prestamo(c, [e[5]], motivo="Cobertura corporativa (QA)", regreso=futuro, empresa=emp)
        confirmar(c, lid)
        firmar_todo(apr, c, lid)
        _ok(apr.post(f"/api/loans/{lid}/autorizar-entrega"), "autorizar")
        mover_fechas(db, lid, entrega=HOY - timedelta(days=23), esperada=HOY - timedelta(days=9))

    escenario("prestado con atraso de 9 dias", atrasado)

    def sin_autorizar():
        c = s["qa.mkt.equipos"]
        lid = crear_prestamo(c, [e[6]], motivo="Sesion de fotos (QA)", regreso=futuro, empresa=emp)
        confirmar(c, lid)
        subir(apr, lid, "firma_entrega")  # falta la firma del beneficiario y la autorizacion

    escenario("confirmado: firma del beneficiario y autorizacion pendientes", sin_autorizar)

    def devuelto():
        c = s["qa.creador.2"]
        lid = crear_prestamo(c, [e[7]], motivo="Entrevistas (QA)", regreso=futuro, empresa=emp)
        confirmar(c, lid)
        firmar_todo(apr, c, lid)
        _ok(apr.post(f"/api/loans/{lid}/autorizar-entrega"), "autorizar")
        devolver(c, lid)
        mover_fechas(db, lid, entrega=HOY - timedelta(days=8))

    escenario("devuelto, pendiente de que la aprobadora confirme", devuelto)

    def con_incidencia():
        c = s["qa.colaborador"]
        lid = crear_prestamo(c, [e[8], e[9]], motivo="Edicion en locacion (QA)", regreso=futuro, empresa=emp)
        confirmar(c, lid)
        firmar_todo(apr, c, lid)
        _ok(apr.post(f"/api/loans/{lid}/autorizar-entrega"), "autorizar")
        items = devolver(c, lid)
        _ok(apr.post(f"/api/loans/{lid}/confirmar-devolucion", json={"decisiones": [
            {"loan_item_id": items[0], "decision": "ok"},
            {"loan_item_id": items[1], "decision": "danado", "nota": "Pantalla rayada (dato ficticio de QA)."},
        ]}), "confirmar devolucion con incidencia")
        mover_fechas(db, lid, entrega=HOY - timedelta(days=15), esperada=HOY - timedelta(days=5), real=HOY - timedelta(days=5))

    escenario("devolucion con incidencia (equipo danado en revision)", con_incidencia)

    escenario("borrador (colaborador)",
              lambda: crear_prestamo(s["qa.colaborador"], [e[10]], motivo="Borrador sin confirmar (QA)", regreso=futuro, empresa=emp))

    def cancelado():
        c = s["qa.mkt.equipos"]
        lid = crear_prestamo(c, [e[11]], motivo="Reserva cancelada (QA)", regreso=futuro, empresa=emp)
        _ok(c.post(f"/api/loans/{lid}/cancelar", json={"motivo": "Cambio de planes (dato ficticio de QA)."}), "cancelar")

    escenario("cancelado", cancelado)
    return fallos


# ─────────────────────────────────────────────────────────────────────────────


def escribir_credenciales(ruta: Path, usuarios):
    lineas = [
        "# Credenciales del entorno QA de GOCreate — SOLO datos ficticios.",
        "# Archivo generado por sembrar_datos.py. Permisos 600. NO subir al repo ni pegar en chats.",
        "# Entrega a la persona que audita por un canal privado.",
        "# usuario<TAB>rol base (+ paquetes)<TAB>contrasena<TAB>que representa",
    ]
    for username, (_u, clave, rol, aditivos, nota) in usuarios.items():
        rol_txt = rol + (" + " + ",".join(aditivos) if aditivos else "")
        lineas.append(f"{username}\t{rol_txt}\t{clave}\t{nota}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.chmod(ruta, 0o600)


def main() -> int:
    ap = argparse.ArgumentParser(description="Siembra el QA de GOCreate con datos ficticios.")
    ap.add_argument("--credenciales", type=Path, required=True,
                    help="Archivo (permisos 600) donde se escriben usuarios y contrasenas.")
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("La base ya tiene usuarios: no se siembra de nuevo. Use reiniciar_datos.sh para empezar de cero.")
            return 0

        print(f"Base: {_db_real}")
        print("== Catalogo RBAC")
        crud_rbac.sembrar_catalogo(db)
        print("== Marcas, creadores, rubros y razones sociales")
        marcas, creadores = sembrar_catalogos(db)
        print("== Usuarios por rol y paquete")
        usuarios = sembrar_usuarios(db, creadores, leer_credenciales(args.credenciales))
        print("== Historial de tickets y gastos")
        n = sembrar_historial(db, marcas, creadores, usuarios)
        print(f"   {n} tickets")
        print("== Inventario")
        equipo_ids = sembrar_inventario(db, usuarios)
        print("== Prestamos de equipo (por la API real)")
        fallos = sembrar_prestamos(db, usuarios, equipo_ids)

        escribir_credenciales(args.credenciales, usuarios)
        print(f"\nCredenciales escritas en {args.credenciales} (permisos 600). No se imprimen aqui.")
        print(f"Resumen: {db.query(models.User).count()} usuarios, {db.query(models.Ticket).count()} tickets, "
              f"{db.query(Equipment).count()} equipos, {db.query(Loan).count()} prestamos.")
        if fallos:
            print("\nSEMBRADO PARCIAL — escenarios que fallaron:")
            for f in fallos:
                print(f"  - {f}")
            return 2
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
