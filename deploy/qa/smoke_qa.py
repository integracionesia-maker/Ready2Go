#!/usr/bin/env python3
"""Prueba de humo del QA (comprobacion 11 de verificar_aislamiento.sh).

Se corre desde backend/ de la release del QA, con el python de su venv:

    cd <release>/backend && venv/bin/python ../deploy/qa/smoke_qa.py --credenciales <archivo>

Maneja la app EN PROCESO (TestClient) contra la base del QA. Hace: iniciar
sesion, crear una marca, editarla, subir un archivo (gasto general con
comprobante), borrarlo y desactivar la marca. Deja la marca desactivada con el
prefijo "Smoke QA" (no hay borrado de marcas en la app).

Se niega a correr sin QA_MODE, igual que sembrar_datos.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from dotenv import load_dotenv

load_dotenv(Path.cwd() / ".env")
if os.getenv("QA_MODE", "").strip().lower() not in ("1", "true", "yes", "si", "on"):
    sys.exit("ABORTADO: QA_MODE no esta activo; la prueba de humo solo corre en el QA.")
os.environ["NOTIF_ENABLED"] = "false"

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

resultados: list[tuple[str, bool, str]] = []


def paso(nombre: str, ok: bool, detalle: str = "") -> bool:
    resultados.append((nombre, ok, detalle))
    print(f"{'PASS' if ok else 'FAIL'}  {nombre}" + (f"  ({detalle})" if detalle and not ok else ""))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--credenciales", type=Path, required=True)
    ap.add_argument("--usuario", default="qa.admin")
    args = ap.parse_args()

    clave = None
    for linea in args.credenciales.read_text(encoding="utf-8").splitlines():
        if linea.startswith("#") or not linea.strip():
            continue
        partes = linea.split("\t")
        if partes[0] == args.usuario:
            clave = partes[2]
    if clave is None:
        sys.exit(f"No hay credenciales de {args.usuario} en {args.credenciales}")

    c = TestClient(app, base_url="https://testserver")
    r = c.post("/api/auth/login", json={"identificador": args.usuario, "password": clave})
    if not paso("iniciar sesion", r.status_code == 200, f"HTTP {r.status_code}"):
        return 1

    r = c.post("/api/brands/", json={"name": "Smoke QA temporal", "priority": "baja"})
    if not paso("crear registro (marca)", r.status_code == 201, f"HTTP {r.status_code} {r.text[:120]}"):
        return 1
    marca = r.json()["id"]

    r = c.put(f"/api/brands/{marca}", json={"name": "Smoke QA editada"})
    paso("editar registro", r.status_code == 200 and r.json().get("name") == "Smoke QA editada", f"HTTP {r.status_code}")

    buf = BytesIO()
    Image.new("RGB", (120, 80), (200, 200, 200)).save(buf, format="JPEG")
    r = c.post(
        "/api/general-expenses/",
        data={"brand_id": str(marca), "amount": "1.00", "description": "Prueba de humo QA"},
        files={"file": ("humo.jpg", buf.getvalue(), "image/jpeg")},
    )
    subio = paso("subir un archivo (gasto con comprobante)", r.status_code == 201, f"HTTP {r.status_code} {r.text[:120]}")
    if subio:
        gasto = r.json()["id"]
        r = c.get(f"/api/general-expenses/{gasto}/file")
        paso("leer el archivo subido", r.status_code == 200 and len(r.content) > 0, f"HTTP {r.status_code}")
        r = c.delete(f"/api/general-expenses/{gasto}/permanent")
        paso("borrar registro", r.status_code == 200, f"HTTP {r.status_code}")

    r = c.put(f"/api/brands/{marca}", json={"is_active": False})
    paso("desactivar la marca de prueba", r.status_code == 200 and r.json().get("is_active") is False, f"HTTP {r.status_code}")

    fallos = [n for n, ok, _ in resultados if not ok]
    print(f"\nPrueba de humo: {len(resultados) - len(fallos)}/{len(resultados)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
