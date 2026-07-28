# Changelog — carril servidor y datos (Control de Equipos)

Que agregue, cambie, quite. Orden inverso: lo nuevo arriba.

---

## 2026-07-28 — S0 Costura

### Agregado

- `backend/app/models_rbac.py` — vacio, solo docstring. Contenido en S1.
- `backend/app/models_equipos.py` — vacio, solo docstring. Contenido en S2.
- `backend/requirements.txt` — `reportlab>=4.2.0`, `pillow>=11.0.0`.
- `backend/requirements-dev.txt` — `freezegun>=1.5.0`.
- `docs/avances/servidor.md`, `docs/backlog_servidor.md`,
  `docs/changelog/servidor.md`, `docs/riesgos/servidor.md`.

### Cambiado

- `backend/app/models.py` — enum `UserRole`: nuevo valor `COLABORADOR_MKT`.
- `backend/app/models.py` — 2 lineas de re-export al final del archivo.

### Quitado

- Nada.
