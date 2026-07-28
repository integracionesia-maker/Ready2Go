# Changelog — carril servidor y datos (Control de Equipos)

Que agregue, cambie, quite. Orden inverso: lo nuevo arriba.

---

## 2026-07-28 — S1 RBAC aditivo (WP1)

### Agregado

- `backend/app/rbac_catalog.py` — catalogo unico: 7 modulos, 27 acciones,
  8 paquetes. Fuente de verdad del contenido de cada paquete.
- `backend/app/models_rbac.py` — `Role`, `RolePermission`, `UserRoleGrant`.
- `backend/app/rbac.py` — motor: `permisos_efectivos`, `require_perm`,
  `require_cualquiera`, `modo_rbac`, cache por request.
- `backend/app/errores.py` — sobre `{detail, codigo}` del contrato §0 y las
  excepciones tipadas (`SinPermiso`, `PermisosNoDisponibles`, `NoEncontrado`,
  `EquipoOcupado`, `TransicionInvalida`, `MediaInvalida`, `MediaMuyGrande`).
  Archivo fuera de la lista de rutas del reparto — ver `docs/avances/servidor.md`.
- `backend/app/crud_rbac.py` — `sembrar_catalogo` (reconciliadora), `conceder`,
  `revocar`, `usuarios_con_permiso`.
- `backend/app/schemas_rbac.py`.
- `backend/app/routers/roles.py` — `GET /api/roles/`.
- `backend/app/routers/user_roles.py` — GET/POST/DELETE de `/api/users/{id}/roles`.
- `backend/migrate_rbac_aditivo.py` — idempotente.
- `backend/seed_rbac.py` — catalogo + `APROBADOR_EQUIPO` a Melisa.
- `backend/tests/rbac/` — `__init__.py`, `conftest.py` y 80 pruebas en
  4 archivos.
- `doc/rbac-aditivo.md`.

### Cambiado

- `backend/app/schemas.py` — `UserResponse`: campo `permisos: dict[str, list[str]] = {}`.
- `backend/app/routers/auth.py` — **solo** `GET /me`: resuelve y devuelve
  `permisos`. Login, refresh, logout y change-password intactos.
- `backend/app/main.py` — import de `roles` y `user_roles` + sus
  `include_router`, e `import`/llamada de `registrar_manejadores(app)`.
- `backend/app/models_rbac.py` — `Role.permisos` y `Role.grants` pasaron de
  `lazy="selectin"` a carga diferida. Con carga anticipada, listar el catalogo
  arrastraba todas las concesiones de todos los usuarios sin que nadie las usara.

### Quitado

- Nada.

### No hecho a proposito

- POST/PUT/DELETE sobre `/api/roles/`. El contrato v1 §7 solo congela `GET`.
  Ver hueco A en `docs/avances/servidor.md`.

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
