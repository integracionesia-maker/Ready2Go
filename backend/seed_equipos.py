"""Seed del inventario real: los 8 equipos de la auditoria del 10/06/2026 y las
3 razones sociales.

Ejecutar desde backend/:

    python seed_equipos.py

Idempotente: cada equipo se inserta con id explicito y se salta si ya esta.

Por que id explicito y no autoincrement: `docs/contratos/fixtures/equipos.json`
y `fixtures/prestamo_demo.json` traen ids concretos y el cliente alimenta sus
mocks con esa copia literal. Si el seed produjera otros ids, la guardia de
contrato de S7 compararia manzanas con peras.

Los comentarios de auditoria son los reales del area, no relleno: el cable tipo
C fallado de los RODE es la razon de que ese equipo este en `condicion=atencion`.
"""

import argparse
import json
from datetime import date

from app.database import Base, SessionLocal, engine

# Import necesario aunque no se use directo: los modelos de Equipos declaran
# relaciones contra `User` por nombre. Sin cargar `app.models`, SQLAlchemy no
# encuentra la clase al configurar los mappers y el script no arranca.
from app import models  # noqa: F401
from app.models_equipos import (
    CondicionEquipo,
    Empresa,
    Equipment,
    EquipmentAudit,
    EstadoFisico,
    EstadoOperativo,
)

AUDITORIA = date(2026, 6, 10)

# Inventario auditado el 10/06/2026. Espejo de docs/contratos/fixtures/equipos.json.
EQUIPOS = [
    {
        "id": 1,
        "codigo": None,
        "nombre": "Celular para grabaciones — iPhone 17 Pro gris (Jeziel)",
        "categoria": "Celular para grabaciones y videos",
        "modelo": "iPhone 17 Pro",
        "espacio_disponible": "87.43 GB de 256 GB",
        "accesorios_tipicos": ["Cargador", "Funda"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": (
            "Sin rayones, excelente estado, como nuevo. Se solicita cambio de funda "
            "porque la actual tapa la calidad de los lentes."
        ),
        "fecha_auditoria": AUDITORIA,
    },
    {
        "id": 2,
        "codigo": None,
        "nombre": "Microfonos RODE (2 pzas., Barbara)",
        "categoria": "Microfonos para grabacion",
        "modelo": None,
        "espacio_disponible": "",
        "accesorios_tipicos": ["Bolsa", "Estuche de microfonos", "Cable conector"],
        "condicion": CondicionEquipo.ATENCION.value,
        "estado_fisico": EstadoFisico.USADO.value,
        "comentario": (
            "El cable tipo C presenta falla. El resto del equipo esta en excelente "
            "estado, sin golpes y funcionando bien."
        ),
        "fecha_auditoria": AUDITORIA,
    },
    {
        "id": 3,
        "codigo": None,
        "nombre": "Celular para grabaciones — iPhone 17 Pro plateado (Barbara)",
        "categoria": "Celular para grabaciones y videos",
        "modelo": "iPhone 17 Pro",
        "espacio_disponible": "200.06 GB de 256 GB",
        "accesorios_tipicos": ["Cargador", "Funda"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": (
            "Sin rayones ni golpes, buen estado. Mica con leves despostillados en la "
            "orilla; case con rayon pequeno en el lente."
        ),
        "fecha_auditoria": AUDITORIA,
    },
    {
        "id": 4,
        "codigo": None,
        "nombre": "Microfonos DJI Mic Mini (duo, plaza)",
        "categoria": "Audio / microfonos inalambricos",
        "modelo": "DJI Mic Mini",
        "espacio_disponible": "",
        "accesorios_tipicos": ["Bolsa", "Cargador portatil", "Fundas para ruido", "Cables"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": "El equipo esta en excelente estado y completo.",
        "fecha_auditoria": AUDITORIA,
    },
    {
        "id": 5,
        "codigo": "OSMO-1",
        "nombre": "(1) Osmo DJI 7",
        "categoria": "Estabilizadores",
        "modelo": "DJI Osmo 7",
        "espacio_disponible": "",
        "accesorios_tipicos": ["Estuche", "Cargador", "Accesorios de montaje"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": "Excelente estado, sin defectos y completo.",
        "fecha_auditoria": AUDITORIA,
    },
    {
        "id": 6,
        "codigo": "OSMO-2",
        "nombre": "(2) Osmo DJI 7",
        "categoria": "Estabilizadores",
        "modelo": "DJI Osmo 7",
        "espacio_disponible": "",
        "accesorios_tipicos": ["Estuche", "Cargador", "Accesorios de montaje"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": "Excelente estado, sin defectos y completo.",
        "fecha_auditoria": AUDITORIA,
    },
    {
        # Sin auditoria fisica todavia: fecha en NULL a proposito. Inventarlo
        # seria firmar una revision que nadie hizo.
        "id": 7,
        "codigo": None,
        "nombre": "Celular para grabaciones — iPhone 17 Pro Max",
        "categoria": "Celular para grabaciones y videos",
        "modelo": "iPhone 17 Pro Max",
        "espacio_disponible": "",
        "accesorios_tipicos": ["Cargador", "Funda"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": (
            "Equipo agregado al inventario; pendiente de auditoria fisica inicial y "
            "fotos de referencia."
        ),
        "fecha_auditoria": None,
    },
    {
        "id": 8,
        "codigo": None,
        "nombre": "Celular para grabaciones — iPhone 17 Pro",
        "categoria": "Celular para grabaciones y videos",
        "modelo": "iPhone 17 Pro",
        "espacio_disponible": "",
        "accesorios_tipicos": ["Cargador", "Funda"],
        "condicion": CondicionEquipo.BUENO.value,
        "estado_fisico": EstadoFisico.NUEVO.value,
        "comentario": (
            "Equipo agregado al inventario; pendiente de auditoria fisica inicial y "
            "fotos de referencia."
        ),
        "fecha_auditoria": None,
    },
]

# Espejo de docs/contratos/fixtures/empresas.json.
EMPRESAS = [
    {
        "id": 1,
        "razon_social": "MERCASYSTEM SA DE CV",
        "direccion": None,
        "ciudad": None,
        "rfc": None,
        "is_active": True,
    },
    {
        "id": 2,
        "razon_social": (
            "DISTRIBUCION Y COMERCIALIZACION DE PRODUCTOS INNOVADORES INNOVA SA DE CV"
        ),
        "direccion": None,
        "ciudad": None,
        "rfc": None,
        "is_active": True,
    },
    {
        # Emisora de la carta responsiva segun la maqueta. PENDIENTE que
        # marketing confirme que es la correcta (§14.3 del plan). Es la unica con
        # RFC y direccion, que es lo que necesita el encabezado del PDF.
        "id": 3,
        "razon_social": "SERVICIOS CORPORATIVOS QUANTUM DE OCCIDENTE, S.C.",
        "direccion": "Belisario Dominguez No. 30 Col. Centro",
        "ciudad": "Morelia, Michoacan",
        "rfc": "SCQ1212149P0",
        "is_active": True,
    },
]


def sembrar_equipos(db, verbose: bool = True) -> int:
    creados = 0
    for datos in EQUIPOS:
        existente = db.get(Equipment, datos["id"])
        if existente is not None:
            if verbose:
                print(f"  = [{datos['id']}] {existente.nombre}")
            continue

        equipo = Equipment(
            id=datos["id"],
            codigo=datos["codigo"],
            nombre=datos["nombre"],
            categoria=datos["categoria"],
            modelo=datos["modelo"],
            espacio_disponible=datos["espacio_disponible"],
            estado_operativo=EstadoOperativo.ACTIVO.value,
            accesorios_tipicos=json.dumps(datos["accesorios_tipicos"], ensure_ascii=False),
        )
        db.add(equipo)
        db.flush()

        db.add(
            EquipmentAudit(
                equipment_id=equipo.id,
                condicion=datos["condicion"],
                estado_fisico=datos["estado_fisico"],
                espacio_disponible=datos["espacio_disponible"],
                comentario=datos["comentario"],
                fecha=datos["fecha_auditoria"],
                actor_user_id=None,
            )
        )
        creados += 1
        if verbose:
            print(f"  + [{equipo.id}] {equipo.nombre} ({datos['condicion']})")

    db.commit()
    return creados


def sembrar_empresas(db, verbose: bool = True) -> int:
    creadas = 0
    for datos in EMPRESAS:
        if db.get(Empresa, datos["id"]) is not None:
            if verbose:
                print(f"  = [{datos['id']}] {datos['razon_social']}")
            continue
        db.add(Empresa(**datos))
        creadas += 1
        if verbose:
            print(f"  + [{datos['id']}] {datos['razon_social']}")
    db.commit()
    return creadas


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed del inventario de Control de Equipos.")
    parser.add_argument("--silencioso", action="store_true")
    args = parser.parse_args()
    verbose = not args.silencioso

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("=== Equipos (auditoria 10/06/2026) ===")
        creados = sembrar_equipos(db, verbose)
        print("=== Razones sociales ===")
        creadas = sembrar_empresas(db, verbose)
        print(f"Listo: {creados} equipos nuevos, {creadas} razones sociales nuevas.")
        print(f"Total en base: {db.query(Equipment).count()} equipos, {db.query(Empresa).count()} empresas.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
