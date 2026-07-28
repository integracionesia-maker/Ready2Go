# Avances — carril servidor y datos (Control de Equipos)

Una entrada por dia de trabajo. Que hice, evidencia, bloqueos.

---

## 2026-07-28 — S0 Costura

Hecho:

- `backend/app/models.py`: `COLABORADOR_MKT = "colaborador_mkt"` en el enum `UserRole`.
- `backend/app/models.py`: 2 lineas de re-export al final (`models_rbac`, `models_equipos`).
  Van al final y no arriba porque los modulos nuevos referencian `users` por
  cadena, nunca por import. Import en sentido contrario cierra el ciclo.
- `backend/app/models_rbac.py`: creado, solo docstring.
- `backend/app/models_equipos.py`: creado, solo docstring.
- `backend/requirements.txt`: `reportlab>=4.2.0`, `pillow>=11.0.0`.
- `backend/requirements-dev.txt`: `freezegun>=1.5.0`.
- Dependencias instaladas.

Evidencia:

```
$ python --version
Python 3.14.6

$ python -c "import reportlab, PIL, freezegun; ..."
reportlab 5.0.0
pillow 12.2.0
freezegun ok

$ python -m pytest -q
169 passed, 1 warning in 35.07s
```

Baseline antes de tocar nada: 169 passed. Despues de S0: 169 passed. Cero
regresion, cero logica.

Nota de conteo: `CLAUDE.md` y el plan dicen 167 pruebas; la suite real en
`dami-branch` tiene 169. Uso 169 como linea base.

Bloqueos: ninguno.
