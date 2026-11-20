"""El flag QA_MODE (entorno QA de deploy/qa/) y su inercia en produccion.

`QA_MODE` se lee al importar `app.main`, asi que cada caso corre en un
SUBPROCESO con su propio entorno: recargar el modulo dentro de pytest dejaria
dos apps y estado global duplicado.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

SCRIPT = """
import json, os
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.get("/api/health")
rb = c.get("/robots.txt")
print(json.dumps({
    "health": r.json(),
    "noindex": r.headers.get("x-robots-tag"),
    "robots_status": rb.status_code,
    "robots_ctype": rb.headers.get("content-type", ""),
    "robots_body": rb.text[:40],
}))
"""


def _correr(tmp_path, qa_mode):
    env = {k: v for k, v in os.environ.items() if k not in ("QA_MODE", "DATABASE_URL")}
    env.update(
        DATABASE_URL=f"sqlite:///{tmp_path / 'qa_mode.db'}",
        JWT_SECRET_KEY="test-secret-key-0123456789abcdef",
        ENV="production",
        NOTIF_ENABLED="false",
    )
    if qa_mode is not None:
        env["QA_MODE"] = qa_mode
    salida = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120,
    )
    assert salida.returncode == 0, salida.stderr[-800:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_con_qa_mode_el_entorno_se_declara_noindex_y_con_robots(tmp_path):
    r = _correr(tmp_path, "true")
    assert r["health"] == {"status": "ok", "version": "1.0.0", "qa": True}
    assert r["noindex"] == "noindex, nofollow"
    assert r["robots_status"] == 200
    assert r["robots_ctype"].startswith("text/plain")
    assert "Disallow: /" in r["robots_body"]


def test_sin_qa_mode_produccion_queda_identica(tmp_path):
    """Sin la variable no cambia NADA: ni cabecera, ni campo extra en health."""
    r = _correr(tmp_path, None)
    assert r["health"] == {"status": "ok", "version": "1.0.0"}
    assert r["noindex"] is None
    assert "Disallow" not in r["robots_body"]


def test_qa_mode_falso_tambien_es_inerte(tmp_path):
    r = _correr(tmp_path, "false")
    assert "qa" not in r["health"]
    assert r["noindex"] is None
