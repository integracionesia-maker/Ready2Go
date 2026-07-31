"""Seeder de datos demo exhaustivos para pruebas de roles, permisos y frontend.

Llena cada rincón del sistema con datos variados a lo largo de 6+ meses:
creadores, marcas, tickets en todos los estados, ciclos de presupuesto,
gastos generales, equipos extra, préstamos en distintos estados, y auditorías.

Idempotente: si ya hay datos, agrega más sin duplicar (salta por nombre/código).
Los tickets siempre se crean aunque el seeder se corra varias veces.

Ejecutar desde backend/:
    python seed_demo_completo.py
"""

import json
import random
import struct
import uuid
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from app.database import Base, SessionLocal, engine
from app import crud, models, security, tz

# ── Equipos ─────────────────────────────────────────────────────────────
from app.models_equipos import (
    CondicionEquipo,
    Empresa,
    Equipment,
    EquipmentAudit,
    EstadoFisico,
    EstadoOperativo,
    EstadoPrestamo,
    Loan,
    LoanItem,
)
from app import crud_equipment, crud_loans, disponibilidad

Base.metadata.create_all(bind=engine)

random.seed(20260731)
TODAY = date.today()
UPLOAD_DIR = Path("./uploads/tickets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GE_UPLOAD_DIR = Path("./uploads/general_expenses")
GE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ─────────────────────────────────────────────────────────────

def _mini_png(label: str = "comprobante") -> bytes:
    """PNG 1x1 válido como placeholder de comprobante."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\xc8")
    text = chunk(b"tEXt", b"Comment\x00" + label.encode("latin-1", "replace"))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"tEXt", b"Comment\x00" + label.encode("latin-1", "replace")) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

def _save_ticket_file(name: str) -> tuple[str, str]:
    path = UPLOAD_DIR / name
    path.write_bytes(_mini_png("ticket"))
    return name, str(path)

def _save_ge_file(name: str) -> tuple[str, str]:
    path = GE_UPLOAD_DIR / name
    path.write_bytes(_mini_png("gasto"))
    return name, str(path)

# ── Datos semilla ───────────────────────────────────────────────────────

CREATORS_DATA = [
    {"name": "Mariana López",      "cycle_budget_amount": 15000.0, "cycle_period": "mensual"},
    {"name": "Carlos Mendoza",     "cycle_budget_amount": 12000.0, "cycle_period": "mensual"},
    {"name": "Valentina Ruiz",     "cycle_budget_amount": 10000.0, "cycle_period": "mensual"},
    {"name": "Diego Fernández",    "cycle_budget_amount": 8000.0,  "cycle_period": "semanal"},
    {"name": "Sofía Herrera",      "cycle_budget_amount": 20000.0, "cycle_period": "mensual"},
    {"name": "Alejandro Torres",   "cycle_budget_amount": 9000.0,  "cycle_period": "semanal"},
    {"name": "Regina Vega",        "cycle_budget_amount": 11000.0, "cycle_period": "mensual"},
    {"name": "Emiliano Ríos",      "cycle_budget_amount": 7000.0,  "cycle_period": "semanal"},
]

BRANDS_DATA = [
    {"name": "Nike",           "priority": "alta"},
    {"name": "Coca-Cola",      "priority": "alta"},
    {"name": "Samsung",        "priority": "media"},
    {"name": "L'Oréal",        "priority": "alta"},
    {"name": "Spotify",        "priority": "media"},
    {"name": "Amazon",         "priority": "baja"},
    {"name": "Microsoft",      "priority": "media"},
    {"name": "Adobe",          "priority": "baja"},
    {"name": "Starbucks",      "priority": "media"},
    {"name": "Red Bull",       "priority": "alta"},
]

# (creator_index, brand_index, amount, days_ago, status_override, notes)
# status_override: None = auto-aprobado para admin/superadmin, "pendiente" o "rechazado"
TICKETS_DATA = [
    # Mariana López — Nike (alta prioridad)
    (0, 0, 3500, 180, None, "Campaña Instagram Stories + Reel"),
    (0, 0, 2800, 150, None, "Post patrocinado feed"),
    (0, 1, 4200, 120, None, "Activación evento presencial"),
    (0, 3, 1800, 90,  None, "Tutorial maquillaje con producto"),
    (0, 0, 5000, 60,  "pendiente", "Campaña Día de las Madres"),
    (0, 1, 2200, 30,  "pendiente", "Stories patrocinados"),
    (0, 4, 1500, 15,  None, "Playlist colaborativa"),
    (0, 9, 3100, 5,   "rechazado", "Contenido evento Red Bull — presupuesto excedido"),

    # Carlos Mendoza — Samsung/Microsoft
    (1, 2, 4000, 170, None, "Unboxing Galaxy S25"),
    (1, 6, 3500, 140, None, "Review Surface Pro"),
    (1, 2, 2500, 110, "pendiente", "Video comparativo cámaras"),
    (1, 5, 1800, 80,  None, "Setup productivo Amazon"),
    (1, 7, 3200, 50,  "rechazado", "Tutorial Premiere Pro — factura ilegible"),
    (1, 2, 4500, 20,  "pendiente", "Campaña lanzamiento Galaxy Watch"),
    (1, 6, 2800, 10,  None, "Curso certificación Azure"),

    # Valentina Ruiz — Nike/Coca-Cola
    (2, 0, 3000, 160, None, "Fotografía de running"),
    (2, 1, 2500, 130, None, "Campaña Navidad Coca-Cola"),
    (2, 0, 3800, 100, "pendiente", "Lanzamiento zapatillas edición especial"),
    (2, 3, 2000, 70,  None, "Skincare routine con producto"),
    (2, 4, 1600, 40,  "rechazado", "Playlist sin autorización de marca"),
    (2, 1, 3200, 25,  None, "Video receta con Coca-Cola"),

    # Diego Fernández — semanal, Adobe/Microsoft
    (3, 7, 2000, 175, None, "Diseño de banners"),
    (3, 6, 1800, 155, None, "Campaña LinkedIn Ads"),
    (3, 7, 2500, 135, "pendiente", "Motion graphics para sitio web"),
    (3, 5, 1200, 95,  None, "Fotos de producto"),
    (3, 7, 3000, 65,  None, "Edición de video corporativo"),
    (3, 6, 1500, 35,  "pendiente", "Presentación ejecutiva"),

    # Sofía Herrera — Coca-Cola/L'Oréal
    (4, 1, 5000, 145, None, "Campaña verano Coca-Cola"),
    (4, 3, 4000, 115, None, "Lanzamiento serum anti-edad"),
    (4, 1, 3500, 85,  "pendiente", "Evento de marca en centro comercial"),
    (4, 5, 2200, 55,  None, "Reseña dispositivos Alexa"),
    (4, 0, 2800, 22,  None, "Colaboración Nike Training Club"),

    # Alejandro Torres — semanal, Spotify/Amazon
    (5, 4, 2500, 125, None, "Curación playlist oficial"),
    (5, 5, 1800, 105, "rechazado", "Unboxing sin autorización"),
    (5, 2, 2200, 75,  None, "Comparativa tablets"),
    (5, 4, 3000, 45,  "pendiente", "Podcast patrocinado"),
    (5, 7, 1600, 18,  None, "Reel animado con After Effects"),

    # Regina Vega — L'Oréal/Starbucks
    (6, 3, 2800, 95,  None, "Review de rutina facial"),
    (6, 8, 1500, 60,  None, "Fotos latte art"),
    (6, 3, 3500, 38,  "pendiente", "Video tutorial maquillaje profesional"),
    (6, 9, 2200, 12,  None, "Cobertura evento extremo"),

    # Emiliano Ríos — semanal, Red Bull/Amazon
    (7, 9, 1800, 55,  None, "Reel deportivo extremo"),
    (7, 5, 1200, 35,  None, "Setup gamer económico"),
    (7, 9, 2500, 20,  "pendiente", "Campaña energía y deporte"),
    (7, 8, 1000, 8,   None, "Review bebida edición limitada"),
]

GASTOS_GENERALES = [
    # (brand_index, amount, days_ago, description)
    (0, 1500, 170, "Licencia anual Adobe Creative Cloud"),
    (2, 800,  160, "Dominio y hosting web"),
    (4, 1200, 150, "Suscripción Spotify for Business"),
    (5, 600,  140, "AWS S3 almacenamiento campañas"),
    (0, 2000, 130, "Fotógrafo externo sesión Nike"),
    (1, 3500, 120, "Producción comercial TV"),
    (6, 900,  110, "Microsoft 365 licencias equipo"),
    (3, 2500, 100, "Influencer colaboración L'Oréal"),
    (7, 700,  90,  "Stock de imágenes y assets"),
    (9, 1800, 80,  "Patrocinio atletas Red Bull"),
    (8, 400,  70,  "Merchandising Starbucks"),
    (2, 1100, 60,  "Campaña Google Ads"),
    (0, 1600, 50,  "Producción video corporativo"),
    (5, 500,  40,  "Envíos y logística"),
    (4, 950,  30,  "Licencia música comercial"),
    (1, 2200, 20,  "Evento lanzamiento producto"),
    (6, 750,  15,  "Consultoría SEO"),
    (9, 1300, 10,  "Equipo de grabación externo"),
    (3, 1800, 5,   "Kit de prensa digital"),
    (8, 350,  2,   "Cápsulas de café para oficina"),
]

EQUIPOS_EXTRA = [
    {"nombre": "Cámara Sony A7 IV",              "categoria": "Cámara profesional",            "marca": "Sony",   "modelo": "A7 IV",          "codigo": "EQ-CAM-001"},
    {"nombre": "Lente 24-70mm f/2.8",            "categoria": "Lente",                          "marca": "Sony",   "modelo": "FE 24-70mm GM",  "codigo": "EQ-LEN-001"},
    {"nombre": "Micrófono inalámbrico RODE",     "categoria": "Audio",                          "marca": "RODE",   "modelo": "Wireless GO II", "codigo": "EQ-MIC-001"},
    {"nombre": "Tripie Manfrotto profesional",   "categoria": "Accesorios",                     "marca": "Manfrotto", "modelo": "055XPROB",     "codigo": "EQ-TRI-001"},
    {"nombre": "Laptop MacBook Pro 16\"",         "categoria": "Equipo de cómputo",              "marca": "Apple",   "modelo": "MacBook Pro M3", "codigo": "EQ-MAC-002"},
]

EMPRESAS_EXTRA = [
    {"razon_social": "MERCASYSTEM SA DE CV",          "direccion": "Av. Insurgentes Sur 1234, CDMX", "rfc": "MER123456ABC"},
    {"razon_social": "CREATIVE MEDIA GROUP SAPI",     "direccion": "Calle Reforma 567, CDMX", "rfc": "CMG890123DEF"},
    {"razon_social": "PRODUCCIONES AUDIOVISUALES SA", "direccion": "Blvd. Puerta de Hierro 890, Zapopan", "rfc": "PAS456789GHI"},
]

# (empresa_index, creator_name, responsable_full_name, days_ago_entrega, estado, equipo_ids, motivo)
PRESTAMOS_DATA = [
    # Préstamo 1: completado — Emily llevó cámara + lente
    (0, "Mariana López", "Emily Vianney Pérez Morales", 90, "completado",
     [9, 10], "Campaña fotográfica Nike"),
    # Préstamo 2: activo — Gerson tiene micrófono y tripie
    (1, "Carlos Mendoza", "Gerson Fabricio Martínez Guerrero", 15, "activo",
     [11, 12], "Grabación de entrevistas para review"),
    # Préstamo 3: completado — Bárbara usó MacBook para edición
    (2, "Sofía Herrera", "Bárbara Montserrat Ayala Escobar", 60, "completado",
     [13], "Edición de video L'Oréal"),
    # Préstamo 4: borrador — Hillary solicita lente para sesión
    (0, "Valentina Ruiz", "Hillary Stephanie Torres Bravo", 0, "borrador",
     [10], "Sesión de fotos para marca deportiva"),
    # Préstamo 5: activo con atraso — Juan Pablo tiene cámara desde hace 40 días
    (1, "Regina Vega", "Juan Pablo Corona Corona", 40, "activo",
     [9], "Cobertura evento corporativo"),
]

USUARIOS_ADMIN_CREADOR = [
    {"username": "admin.mkt",     "email": "admin.mkt@grupo-ortiz.com",     "full_name": "Admin Marketing",    "role": "admin",        "password": None},
    {"username": "mariana.lopez", "email": "mariana.lopez@creadores.grupo-ortiz.com", "full_name": "Mariana López", "role": "creador", "password": None, "creator_name": "Mariana López"},
    {"username": "carlos.mendoza","email": "carlos.mendoza@creadores.grupo-ortiz.com","full_name": "Carlos Mendoza","role": "creador", "password": None, "creator_name": "Carlos Mendoza"},
]

# ── Ejecución ───────────────────────────────────────────────────────────

def main():
    db = SessionLocal()
    default_pw = security.hash_password("Marketing2026!")

    try:
        # ── 1. Creadores ──────────────────────────────────────────────
        print("=== Creadores ===")
        creators = []
        for c in CREATORS_DATA:
            existente = db.query(models.Creator).filter(models.Creator.name == c["name"]).first()
            if existente:
                print(f"  [existe] {c['name']}")
                creators.append(existente)
            else:
                obj = models.Creator(
                    name=c["name"],
                    initial_budget=c["cycle_budget_amount"] * 3,
                    spent_budget=0,
                    remaining_budget=c["cycle_budget_amount"] * 3,
                    cycle_budget_amount=c["cycle_budget_amount"],
                    cycle_period=c["cycle_period"],
                    is_active=True,
                )
                db.add(obj)
                db.flush()
                creators.append(obj)
                print(f"  [creado] {c['name']} ({c['cycle_period']}, ${c['cycle_budget_amount']:,.0f})")

        # ── 2. Marcas ──────────────────────────────────────────────────
        print("\n=== Marcas ===")
        brands = []
        for b in BRANDS_DATA:
            existente = db.query(models.Brand).filter(models.Brand.name == b["name"]).first()
            if existente:
                print(f"  [existe] {b['name']}")
                brands.append(existente)
            else:
                obj = models.Brand(name=b["name"], priority=b["priority"], is_active=True)
                db.add(obj)
                db.flush()
                brands.append(obj)
                print(f"  [creado] {b['name']} (prioridad: {b['priority']})")

        db.commit()

        # ── 3. Tickets ─────────────────────────────────────────────────
        print(f"\n=== Tickets ({len(TICKETS_DATA)} planeados) ===")
        admin_user = db.query(models.User).filter(models.User.role == "superadmin").first()
        creados_tickets = 0
        for ci, bi, amount, days_ago, status_ov, notes in TICKETS_DATA:
            creator = creators[ci]
            brand = brands[bi]
            ticket_date = TODAY - timedelta(days=days_ago)
            fname, fpath = _save_ticket_file(f"demo_{ci}_{bi}_{days_ago}.png")

            # Asignar ciclo por fecha
            from app.crud import get_or_create_cycle_for_date
            cycle = get_or_create_cycle_for_date(db, creator, ticket_date)
            if cycle is None:
                # Crear ciclo manualmente
                if creator.cycle_period == "semanal":
                    start = ticket_date - timedelta(days=ticket_date.weekday())
                    end = start + timedelta(days=6)
                else:
                    start = ticket_date.replace(day=1)
                    if start.month == 12:
                        end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
                cycle = models.BudgetCycle(
                    creator_id=creator.id, period_type=creator.cycle_period,
                    amount=creator.cycle_budget_amount, spent=0,
                    start_date=start, end_date=end,
                )
                db.add(cycle)
                db.flush()

            actual_status = status_ov or "aprobado"  # admin/superadmin auto-aprueban
            reviewed_by = admin_user.id if actual_status != "pendiente" else None
            reviewed_at = datetime.now() if actual_status != "pendiente" else None
            rejection_reason = "Presupuesto excedido para este ciclo." if actual_status == "rechazado" else None

            ticket = models.Ticket(
                creator_id=creator.id,
                brand_id=brand.id,
                budget_cycle_id=cycle.id,
                amount=amount,
                status=actual_status,
                rejection_reason=rejection_reason,
                reviewed_by_user_id=reviewed_by,
                reviewed_at=reviewed_at,
                file_name=fname,
                file_path=fpath,
                mime_type="image/png",
                upload_date=ticket_date,
                notes=notes,
            )
            db.add(ticket)
            db.flush()

            # Actualizar cycle.spent si está aprobado
            if actual_status == "aprobado":
                cycle.spent += amount

            creados_tickets += 1
        db.commit()
        print(f"  {creados_tickets} tickets creados")

        # ── 4. Gastos Generales ────────────────────────────────────────
        print(f"\n=== Gastos Generales ({len(GASTOS_GENERALES)} planeados) ===")
        creados_ge = 0
        for bi, amount, days_ago, desc in GASTOS_GENERALES:
            brand = brands[bi]
            exp_date = TODAY - timedelta(days=days_ago)
            fname, fpath = _save_ge_file(f"demo_ge_{bi}_{days_ago}.png")
            ge = models.GeneralExpense(
                brand_id=brand.id,
                amount=amount,
                description=desc,
                file_name=fname,
                file_path=fpath,
                mime_type="image/png",
                upload_date=exp_date,
                created_by_user_id=admin_user.id,
            )
            db.add(ge)
            creados_ge += 1
        db.commit()
        print(f"  {creados_ge} gastos creados")

        # ── 5. Empresas extra ──────────────────────────────────────────
        print("\n=== Empresas ===")
        for e in EMPRESAS_EXTRA:
            existente = db.query(Empresa).filter(Empresa.razon_social == e["razon_social"]).first()
            if not existente:
                db.add(Empresa(**e))
                print(f"  [creado] {e['razon_social']}")
            else:
                print(f"  [existe] {e['razon_social']}")
        db.commit()

        # ── 6. Equipos extra ───────────────────────────────────────────
        print("\n=== Equipos extra ===")
        equipos = list(db.query(Equipment).all())
        for eq in EQUIPOS_EXTRA:
            existente = db.query(Equipment).filter(Equipment.codigo == eq["codigo"]).first()
            if not existente:
                obj = Equipment(
                    nombre=eq["nombre"], categoria=eq["categoria"],
                    marca=eq["marca"], modelo=eq["modelo"], codigo=eq["codigo"],
                    estado_operativo=EstadoOperativo.ACTIVO.value,
                    accesorios_tipicos=json.dumps([]),
                )
                db.add(obj)
                db.flush()
                equipos.append(obj)
                # Auditoría inicial
                db.add(EquipmentAudit(
                    equipment_id=obj.id, condicion=CondicionEquipo.BUENO.value,
                    estado_fisico=EstadoFisico.NUEVO.value,
                    comentario="Equipo nuevo ingresado al inventario.",
                    fecha=TODAY, actor_user_id=admin_user.id,
                ))
                print(f"  [creado] {eq['nombre']} ({eq['codigo']})")
            else:
                print(f"  [existe] {eq['nombre']}")
        db.commit()

        # ── 7. Préstamos ───────────────────────────────────────────────
        print(f"\n=== Préstamos ({len(PRESTAMOS_DATA)} planeados) ===")
        empresas = db.query(Empresa).all()
        creadores_map = {c.name: c for c in creators}

        for emp_i, creator_name, resp_name, days_ago, estado, eq_ids, motivo in PRESTAMOS_DATA:
            empresa = empresas[emp_i % len(empresas)]
            creator = creadores_map.get(creator_name)
            responsable = db.query(models.User).filter(models.User.full_name == resp_name).first()
            if not responsable:
                print(f"  [saltado] responsable no encontrado: {resp_name}")
                continue

            entrega = TODAY - timedelta(days=days_ago)
            regreso = entrega + timedelta(days=14) if estado in ("activo", "completado") else entrega + timedelta(days=7)

            loan = Loan(
                empresa=empresa.razon_social,
                responsable_nombre=responsable.full_name,
                responsable_user_id=responsable.id,
                responsable_email=responsable.email,
                area="Marketing",
                motivo=motivo,
                estado=estado,
                fecha_entrega=entrega if estado != "borrador" else None,
                fecha_regreso_esperada=regreso,
                created_by_user_id=responsable.id,
                created_at=entrega - timedelta(days=3),
            )
            db.add(loan)
            db.flush()

            for eq_id in eq_ids:
                equipo = next((e for e in equipos if e.id == eq_id), None)
                if equipo:
                    item = LoanItem(
                        loan_id=loan.id,
                        equipment_id=eq_id,
                        devuelto_at=regreso if estado == "completado" else None,
                        decision="ok" if estado == "completado" else None,
                    )
                    db.add(item)

            print(f"  [creado] préstamo {loan.folio}: {motivo} ({estado}) — {resp_name}")

        db.commit()

        # ── 8. Usuarios admin + creador ────────────────────────────────
        print("\n=== Usuarios extra ===")
        for u in USUARIOS_ADMIN_CREADOR:
            existente = db.query(models.User).filter(models.User.username == u["username"]).first()
            if existente:
                print(f"  [existe] {u['username']}")
                continue
            creator_id = None
            if u.get("creator_name"):
                c = db.query(models.Creator).filter(models.Creator.name == u["creator_name"]).first()
                if c:
                    creator_id = c.id
            obj = models.User(
                username=u["username"], email=u["email"], full_name=u["full_name"],
                password_hash=default_pw, role=u["role"],
                creator_id=creator_id, is_active=True, must_change_password=False,
            )
            db.add(obj)
            print(f"  [creado] {u['username']} ({u['role']})")
        db.commit()

        # ── Resumen ────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("RESUMEN FINAL:")
        print(f"  Creadores:       {db.query(models.Creator).count()}")
        print(f"  Marcas:          {db.query(models.Brand).count()}")
        print(f"  Tickets:         {db.query(models.Ticket).count()}")
        print(f"  BudgetCycles:    {db.query(models.BudgetCycle).count()}")
        print(f"  Gastos Generales:{db.query(models.GeneralExpense).count()}")
        print(f"  Equipment:       {db.query(Equipment).count()}")
        print(f"  Loans:           {db.query(Loan).count()}")
        print(f"  EquipmentAudit:  {db.query(EquipmentAudit).count()}")
        print(f"  Users:           {db.query(models.User).count()}")
        print("=" * 60)
        print("Seeder completado. ¡A probar!")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
