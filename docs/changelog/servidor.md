# Changelog — carril servidor y datos (Control de Equipos)

Que agregue, cambie, quite. Orden inverso: lo nuevo arriba.

---

## 2026-07-28 — S6 Correo y recordatorios (WP6) + S7 Guardias de contrato

### Agregado

- `backend/app/mailer.py` — SMTP con `smtplib`, STARTTLS, `NOTIF_ENABLED`.
- `backend/app/plantillas_correo.py` — 5 plantillas de texto plano.
- `backend/app/notificaciones.py` — encolado idempotente, destinatarios por rol
  desde la base, reintentos con tope, aviso ruidoso cuando no hay aprobadores.
- `backend/app/routers/notifications.py` — `GET /api/notifications/`,
  `GET /api/notifications/config`,
  `POST /api/notifications/{id}/reintentar`. **Fuera del contrato v1**: los pide
  la asignacion en S6; protegidos con `usuarios:gestionar`.
- `backend/scripts/recordatorios_vencimiento.py` — recordatorio diario.
- `docs/deploy/recordatorios_launchagent.md` — plist, variables de entorno y
  diagnostico.
- `backend/tests/equipos/test_notificaciones.py` — 35 pruebas.
- `backend/tests/test_contrato_openapi.py` — 37 pruebas.
- `backend/tests/equipos/test_fixture_demo.py` — 10 pruebas.

### Cambiado

- `backend/app/routers/loans.py` — `POST /confirmar` avisa a aprobadores y al
  responsable (con el PDF adjunto); `POST /devolucion` avisa a aprobadores.
  Todo en `BackgroundTasks`.
- `backend/app/routers/approvals.py` — `POST /confirmar-devolucion` avisa al
  responsable con el resultado.
- `backend/app/main.py` — include_router de `notifications`.

### Quitado

- Nada.

---

## 2026-07-28 — S5 Carta responsiva en PDF (WP5)

### Agregado

- `backend/app/pdf/__init__.py`, `estilos.py`, `plantilla.py`, `responsiva.py`.
- `backend/app/routers/responsivas.py` — `GET /api/loans/{id}/responsiva.pdf`
  con `?version=` opcional.
- `backend/tests/equipos/test_responsiva_pdf.py` — 27 pruebas.
- `backend/requirements-dev.txt` — `pypdf>=5.0.0`.

### Cambiado

- `backend/app/main.py` — include_router de `responsivas`.
- `backend/seed_prestamo_demo.py` — precondicion explicita de que exista la
  razon social emisora, con mensaje que manda a `seed_equipos.py`.
- `backend/tests/equipos/test_aprobacion.py`, `test_media.py`,
  `test_migracion_y_seeds.py` — sus fixtures ahora siembran tambien las
  razones sociales: confirmar genera la carta y la emisora sale de esa tabla.

### No hecho a proposito

- Endpoint de regeneracion de la responsiva: no esta en el contrato v1.

---

## 2026-07-28 — S4 API de prestamos, aprobacion y media (WP4)

### Agregado

- `backend/app/loan_state.py` — maquina de estados pura: tabla de transiciones,
  guarda de `entrega_autorizada` contra el estado destino, y las dos unicas
  acciones que escriben `devuelto_at`.
- `backend/app/media_manager.py` — magic bytes (PNG 8 bytes, JPEG SOI de 3),
  limites por kind, sha256 de los bytes originales, miniatura de 96px al vuelo,
  reemplazo con borrado del archivo anterior, freno a la bomba de descompresion.
- `backend/app/schemas_loans.py` — `LoanDetail` (espejo del fixture), `LoanRow`,
  cuerpos de entrada.
- `backend/app/crud_loans.py` — serializacion, listado con scoping, las seis
  transiciones, versionado de responsiva, filas del CSV.
- `backend/app/routers/loans.py` — `POST /`, `GET /`, `GET /export`,
  `GET /by-folio/{folio}`, `GET /{id}`, `POST /{id}/items`,
  `DELETE /{id}/items/{item_id}`, `POST /{id}/media`, `POST /{id}/confirmar`,
  `POST /{id}/cancelar`, `POST /{id}/devolucion`.
- `backend/app/routers/approvals.py` — `/autorizar-entrega`,
  `/confirmar-devolucion`, `/cerrar-incidencia`.
- `backend/app/routers/media.py` — `GET /api/media/{id}` con `?tamano=thumb`.
- `backend/tests/equipos/test_loan_state.py`, `test_api_prestamos.py`,
  `test_media.py`, `test_aprobacion.py` — 148 pruebas.

### Cambiado

- `backend/app/main.py` — include_router de `loans`, `approvals` y `media`.
- `backend/tests/equipos/conftest.py` — fixture autouse que manda media y
  responsivas a un temporal, y helpers `png_bytes`, `jpeg_bytes`, `subir`.

### No hecho a proposito

- `PUT /api/loans/{id}`, `?version=` en la responsiva, endpoint de regeneracion
  y endpoint de borrado de prestamo: ninguno esta en el contrato v1.
- Validacion de participacion en las escrituras: el contrato no la pide. Ver
  R-SRV-11 (critico) en `docs/riesgos/servidor.md`.

---

## 2026-07-28 — S3 API de inventario (WP3)

### Agregado

- `backend/app/schemas_equipment.py` — fila del listado, ficha, alta, edicion,
  auditoria, baja y dashboard.
- `backend/app/crud_equipment.py` — listado con filtros, ultima auditoria por
  equipo en una consulta, alta/edicion, registro de auditoria, baja logica,
  historial de prestamos del equipo.
- `backend/app/crud_dashboard_equipos.py` — contadores, distribucion por estado
  y "requiere atencion". Sin importar `crud_loans`.
- `backend/app/routers/equipment.py` — `GET /`, `GET /{id}`, `POST /`,
  `PUT /{id}`, `POST /{id}/auditoria`, `POST /{id}/baja`.
- `backend/app/routers/equipos_dashboard.py` — `GET /api/equipment/dashboard`.
- `backend/tests/equipos/test_api_inventario.py` — 31 pruebas.

### Cambiado

- `backend/app/main.py` — include_router de `equipos_dashboard` (primero) y
  `equipment` (despues).

### Quitado

- Nada.

---

## 2026-07-28 — S2 Modelo de datos de Equipos (WP2)

### Agregado

- `backend/app/models_equipos.py` — 10 tablas (`equipment`, `equipment_audit`,
  `loan`, `loan_item`, `media_asset`, `responsiva_doc`, `loan_event`,
  `notification_log`, `empresa`, `folio_counter`), el indice unico parcial
  `ux_loan_item_equipo_abierto` y los vocabularios del modulo.
- `backend/app/disponibilidad.py` — formula derivada, `mapa_prestamos_abiertos`
  en una sola consulta, calculo de atraso en servidor.
- `backend/app/folio.py` — `CE-0001`, contador transaccional, 3 reintentos,
  `sincronizar_contador`.
- `backend/app/tz.py` — America/Mexico_City; `hoy`, `iso_cdmx`, `dias_de_atraso`.
- `backend/app/schemas_empresas.py`, `backend/app/crud_empresas.py`,
  `backend/app/routers/empresas.py` — `GET /api/empresas/`,
  `POST /api/empresas/`, `PUT /api/empresas/{id}`.
- `backend/migrate_equipos.py` — idempotente, verifica precondicion e indice.
- `backend/seed_equipos.py` — 8 equipos de la auditoria del 10/06/2026 y las
  3 razones sociales, con ids fijos del fixture.
- `backend/seed_prestamo_demo.py` — prestamo `CE-0007` con ids fijos y archivos
  de media reales (2 fotos + 2 firmas, con sha256).
- `backend/tests/equipos/` — `__init__.py`, `conftest.py` y 65 pruebas en
  4 archivos, incluidas las que corren cada script en un proceso propio.

### Cambiado

- `backend/requirements.txt` — `tzdata>=2024.1`. En Windows `zoneinfo` no trae
  la base IANA; estaba entrando de transitiva.
- `backend/app/main.py` — import e `include_router` de `empresas`.
- `backend/migrate_rbac_aditivo.py` — import explicito de `app.models` y
  precondicion de que exista la tabla `users`.

### Corregido

- `app/folio.py` — el incremento del contador estaba dentro del SAVEPOINT: el
  rollback del choque lo deshacia y los 3 reintentos pedian el mismo numero.
- `migrate_equipos.py`, `seed_equipos.py`, `migrate_rbac_aditivo.py` — les
  faltaba `import app.models`; no arrancaban fuera de pytest.

### Quitado

- Nada.

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
