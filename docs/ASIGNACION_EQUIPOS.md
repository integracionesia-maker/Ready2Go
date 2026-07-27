# Asignacion de trabajo — Control de Equipos (servidor y datos)

> Fase 5 del proyecto. Tu carril: **servidor y datos**. Paquetes WP1 a WP6 del plan.
> Plan tecnico completo: `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` (secciones 3, 4, 5, 6, 7).
> Contrato de API: `docs/contratos/` — **solo lectura**.
> Este documento manda sobre el plan si algo se contradice. Si algo no esta aqui, preguntalo antes de escribirlo.

> **ANTES DE ESCRIBIR CODIGO:** el contrato de API (`docs/contratos/`) se publica en master el dia 0 y todavia no esta. Lee este documento completo, prepara tu entorno y planea tu orden de trabajo, pero **no arranques la tarea 0 hasta que se avise que el contrato ya esta en master**. Se avisa el mismo dia.

---

## Regla numero uno

Tu carril vive **dentro de `backend/`**. La frontera con el resto del trabajo no es un archivo: es el contrato HTTP. Si respetas el contrato y no sales de `backend/`, no vas a chocar con nadie en un merge. Nunca.

---

## Tus rutas (dueño unico, nadie mas las toca)

```
backend/app/rbac.py, rbac_catalog.py, models_rbac.py, schemas_rbac.py, crud_rbac.py
backend/app/models_equipos.py, disponibilidad.py, folio.py, tz.py, loan_state.py, media_manager.py
backend/app/schemas_equipment.py, schemas_loans.py, schemas_empresas.py, schemas_responsiva.py, schemas_notificaciones.py
backend/app/crud_equipment.py, crud_loans.py, crud_empresas.py, crud_dashboard_equipos.py
backend/app/pdf/                     (directorio nuevo completo)
backend/app/mailer.py, notificaciones.py, plantillas_correo.py
backend/app/routers/roles.py, user_roles.py, equipment.py, loans.py, approvals.py,
                    media.py, responsivas.py, empresas.py, equipos_dashboard.py, notifications.py
backend/app/main.py                  (unico editor: imports + include_router)
backend/migrate_rbac_aditivo.py, migrate_equipos.py
backend/seed_rbac.py, seed_equipos.py, seed_prestamo_demo.py
backend/scripts/                     (directorio nuevo completo)
backend/tests/rbac/, backend/tests/equipos/   (con __init__.py y conftest.py propios)
backend/tests/test_contrato_openapi.py
backend/requirements.txt, requirements-dev.txt, pytest.ini (sin cambiar testpaths)
doc/rbac-aditivo.md
docs/deploy/recordatorios_launchagent.md
docs/backlog_servidor.md, docs/avances/servidor.md, docs/changelog/servidor.md, docs/riesgos/servidor.md
```

Ediciones quirurgicas permitidas en archivos existentes (solo esas lineas, nada mas):

| Archivo | Lo unico que puedes cambiar |
|---|---|
| `backend/app/models.py` | valor `COLABORADOR_MKT` en el enum `UserRole` + 2 lineas de re-export. **Prohibido** editar la clase `User`: las relaciones se declaran con `backref` desde tus archivos nuevos |
| `backend/app/schemas.py` | agregar `permisos: dict[str, list[str]] = {}` a `UserResponse` |
| `backend/app/routers/auth.py` | **solo** el endpoint `GET /me`. Login, refresh, logout y change-password quedan fuera |

## Fuera de tu alcance — no los edites

```
frontend/                            el directorio completo. Ni package.json, ni los e2e.
backend/app/crud.py                  congelado (reglas de ciclos y filtro is_deleted)
backend/app/dependencies.py          congelado (require_role se conserva intacto)
backend/app/upload_manager.py        congelado (tu subida es media_manager.py, sin import cruzado)
backend/app/security.py, database.py congelados
backend/app/routers/tickets.py, users.py, creators.py, brands.py, dashboard.py, general_expenses.py
backend/tests/conftest.py y los 8 test_*.py existentes    red de regresion
backend/seed_auth.py, seed.py, seed_demo_year.py, seed_more_months.py, seed_test_data.py,
merge_duplicates.py, trim_overbudget.py, reset_superadmin_password.py, migrate_* viejos
raiz: BACKLOG.md, CHANGELOG.md, status.md, context.md, MVP_BREAKDOWN.md, RISKS.md,
      CLAUDE.md, DESIGN_SYSTEM.md, avances_diarios.md, .env.example, .gitignore
docs/contratos/                      solo lectura
docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md, doc/deploy-runbook.md, doc/auth-arquitectura.md
```

Hay trabajo en paralelo sobre varios de esos archivos. Si necesitas cambiar algo de esta lista, **pidelo, no lo edites**.

**Si una prueba existente se pone roja por tu cambio, NO la edites. Reportala.** Una prueba en rojo es una señal, no un estorbo.

---

## Tareas, en orden

### S0 — Costura (primer commit, mecanico, aislado)
Crear `models_rbac.py` y `models_equipos.py` vacios + las 2 lineas de re-export en `models.py`; agregar `COLABORADOR_MKT` al enum `UserRole`; `reportlab` y `pillow` a `requirements.txt`; `freezegun` a `requirements-dev.txt`.
**Cierra con:** un commit, `pytest` con las 167 pruebas verdes, cero logica.

### S1 — RBAC aditivo (WP1)
3 tablas (`roles`, `role_permissions`, `user_role_grants`), motor `rbac.py` (`permisos_efectivos`, `require_perm`, `PermisosNoDisponibles` → **503**), `rbac_catalog.py` como fuente unica del catalogo, `crud_rbac.py` con `usuarios_con_permiso()`, routers `roles.py` y `user_roles.py`, `GET /api/auth/me` con campo `permisos`, `migrate_rbac_aditivo.py` idempotente, `seed_rbac.py`. Lectura de `RBAC_MODO` para el rollback a legacy.
**Cierra con:** pruebas que enumeran el set efectivo de CADA combinacion de roles; prueba de que un fallo de DB da 503 y no 403; prueba de que el paquete aprobador **no abre ni un permiso de presupuestos**; migracion corrida dos veces sin fallar.

### S2 — Modelo de datos (WP2)
10 tablas + **indice unico parcial** `ux_loan_item_equipo_abierto`; `disponibilidad.py` con la formula derivada (**no existe `equipment.estado='prestado'`**); `folio.py` (CE-0000 transaccional, 3 reintentos); `tz.py` (America/Mexico_City); tabla `empresa` + `routers/empresas.py`; `migrate_equipos.py`; `seed_equipos.py` con los 8 equipos de la auditoria del 10/06; `seed_prestamo_demo.py`.
**Cierra con:** prueba de que un equipo no puede quedar en dos prestamos abiertos; prueba de folio bajo concurrencia; migracion idempotente.

### S3 — API inventario (WP3)
`routers/equipment.py`: listado con `q` y filtros, alta, edicion, ficha con auditorias e historial, `POST /auditoria`, `POST /baja` con **409 si hay prestamo abierto**. `routers/equipos_dashboard.py` con queries propias contra tablas (prohibido importar `crud_loans`). `schemas_equipment.py`, `crud_equipment.py`, `crud_dashboard_equipos.py`.
**Cierra con:** pruebas de permisos (403) y de conflicto (409); `GET /api/equipment/dashboard` declarado **antes** de `/{id:int}` para que el enrutador no lo trague como id.

### S4 — API prestamos, aprobacion y media (WP4)
`routers/loans.py`, `approvals.py`, `media.py`; `loan_state.py` (maquina de estados aislada y pura: `entrega_autorizada=0` **bloquea** llegar a `completado`; salida de `incompleto` por cerrar incidencia); `media_manager.py` (**magic bytes**, 3 MB foto / 250 KB firma, sha256, miniatura de 96px, `uploads/equipos/`); `schemas_loans.py`, `crud_loans.py`; export CSV; scoping server-side por `responsable_user_id`.
**Cierra con:** prueba de la maquina de estados completa **incluidas las transiciones invalidas**; prueba de que un usuario no descarga media de un prestamo ajeno (403).

### S5 — Carta responsiva en PDF (WP5)
`backend/app/pdf/` (`responsiva.py`, `plantilla.py`, `estilos.py`); `routers/responsivas.py` con su propio router bajo el mismo prefix `/api/loans` (FastAPI lo acepta; **no se edita `loans.py`**); versionado que **nunca sobrescribe**; sha256. Razon social **siempre** desde la tabla `empresa`, jamas hardcode.
**Cierra con:** prueba de que la version 2 no pisa la 1; un PDF generado con datos reales para revision visual.

### S6 — Correo y recordatorios (WP6)
`mailer.py` (smtplib de la libreria estandar, STARTTLS, `NOTIF_ENABLED` como corta-circuito); `notificaciones.py` con `encolar(db, tipo, loan, background_tasks)`; `plantillas_correo.py` con las 5 plantillas de la seccion 7 del plan; `routers/notifications.py` de diagnostico; `backend/scripts/recordatorios_vencimiento.py` para LaunchAgent. Destinatarios **resueltos por rol desde la DB**, nunca una constante con un correo dentro.
**Cierra con:** prueba de idempotencia (reintentar no duplica correos); prueba de que un SMTP caido **no** tumba el registro del prestamo.

### S7 — Guardias de contrato (obligatorias, no opcionales)
- `backend/tests/test_contrato_openapi.py`: compara el `openapi.json` generado contra `docs/contratos/openapi_equipos_v1.json` (rutas, metodos, codigos de estado, nombres de campo). Rojo = el servidor se salio del contrato. Se arregla en el servidor o se pide cambio de contrato. **Nunca se ignora.**
- `backend/tests/equipos/test_fixture_demo.py`: la respuesta de `GET /api/loans/{id}` para el prestamo de `seed_prestamo_demo.py` debe ser igual a `docs/contratos/fixtures/prestamo_demo.json`. **Ese archivo es el criterio de aceptacion del payload**, no la tabla SQL.

---

## Como reportas

Cuatro archivos tuyos, en `docs/`. **No abras los documentos de estado de la raiz** — se consolidan en otro lado y si los tocas hay conflicto de merge garantizado:

```
docs/avances/servidor.md      que hiciste, evidencia, bloqueo (una entrada por dia de trabajo)
docs/backlog_servidor.md      tus pendientes
docs/changelog/servidor.md    que agregaste, cambiaste, quitaste
docs/riesgos/servidor.md      riesgos que descubras
```

## Git

- Trabaja **solo en tu rama**. Nunca en master.
- `git add` con **rutas explicitas**. Nunca `git add -A` ni `git add .`.
- Push a tu rama al terminar el dia: el trabajo solo existe cuando esta en origin.
- Si un push sale rechazado o la rama diverge: **para y reporta**. Nada de `pull` pelado, `reset` ni force.

## Terminado significa

Codigo funciona + tus pruebas nuevas pasan + las 167 existentes siguen verdes + evidencia en `docs/avances/servidor.md`. Sin las cuatro, el paquete no esta cerrado.

## Si algo del contrato no alcanza

Se para y se reporta. **No improvises el endpoint ni cambies la forma del payload por tu cuenta**: hay codigo construyendose contra ese contrato al mismo tiempo. Un cambio aplicado de un solo lado es el modo tipico de falla de este reparto.
