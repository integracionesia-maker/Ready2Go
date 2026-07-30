# Backend — convenciones y gotchas

> Ver también [[CLAUDE]] en la raíz del repo para reglas de negocio y arquitectura general.

- Rutas de `backend/app/main.py` y `database.py` son relativas al cwd (`./presupuesto.db`, `./uploads`) — siempre levantar uvicorn con cwd = `backend/`.
- Datos de creadores/marcas: evitar duplicados por acentos al re-seedear (`seed.py` ya usa ortografia con acento — no revertir a versiones sin acento).
