# CHANGELOG — GOCreate

Registro de cambios del proyecto. Formato: `Agregado` / `Actualizado` / `Eliminado` / `Corregido`.

---

## 2026-09-04 — Firma pendiente al confirmar, revisión 2 + titular de la firma (Control de Equipos)

Luz verde explícita de Jose para los tres cambios de este bloque.

### Actualizado

- **Rediseño de las firmas de préstamo (revisión 2)**: `POST /api/loans/{id}/confirmar` ya no exige ninguna firma (antes exigía al menos una) — solo las fotos de entrega siguen siendo obligatorias. El préstamo pasa a `prestado` con las dos firmas pendientes siempre; se completan después, cada una por su lado, sin bloquear la reserva del equipo ni la devolución. `firmas_completas` sigue bloqueando únicamente las dos rutas a `completado` (`confirmar-devolucion`, `cerrar-incidencia`).
  - Las firmas ya nunca se aceptan en `borrador` (antes sí); solo en `prestado`/`pendiente_confirmacion`/`incompleto`.
  - `firma_entrega` (aprobador) y `firma_responsable` (beneficiario) dejan de ser una sola pareja simétrica: cada una tiene su propio dueño y su propio candado (ver el paquete `TITULAR_FIRMA_EQUIPO` más abajo para `firma_entrega`; `firma_responsable` sigue abierta a cualquiera con `equipos_prestamos:solicitar`, porque el beneficiario puede no tener cuenta en GOCreate).
  - `LoanRow.firma_pendiente` (booleano único) se separó en `firma_entrega_pendiente` / `firma_responsable_pendiente` — Activos, Historial y las tres colas de Aprobaciones ya no pueden confundir cuál firma falta.
  - El formulario de préstamo (`/equipos/nuevo`) ya no tiene paso de Firmas (quedan 3 pasos: Datos, Equipos, Fotos) y ahora pide los datos del **Beneficiario** (nombre + correo, texto libre) en el paso 1 — el solicitante ya no se asume como beneficiario.
  - Aprobaciones tiene una cola nueva, "Firmas pendientes", y el sidebar de Equipos muestra un badge numérico contándolas (mismo patrón que Presupuestos).
  - Detalle completo y ejemplos: `docs/equipos/firma-pendiente-al-confirmar.md` (reescrito de punta a punta; la revisión 1 documentada ahí antes nunca llegó a producción).

- **Nuevo paquete aditivo `TITULAR_FIRMA_EQUIPO`, kind singleton**: solo un usuario a la vez puede tenerlo — concederlo a alguien nuevo revoca automáticamente al anterior (`crud_rbac.conceder`). Se asigna en `/administracion-sistema` → Asignaciones, igual que cualquier otro paquete (con aviso en la UI de que es único). Sirve para dos cosas: (1) mientras nadie ha firmado `firma_entrega`, su nombre aparece por default en la carta responsiva en vez de un espacio en blanco; (2) es, en la práctica, el único que puede subir `firma_entrega` — verificado por **identidad** (`current_user.id == titular.id`), no por permiso.
  - Nuevo endpoint `GET /api/loans/titular-firma-equipo` (`{user_id, nombre, soy_titular}`) para que la Ficha del préstamo y Aprobaciones sepan a quién pintarle el botón "Firmar" del aprobador.

### Corregido

- **CRÍTICO: superadmin (y cualquier `APROBADOR_EQUIPO` que no fuera el titular) podía firmar `firma_entrega`.** El candado original validaba por `rbac.tiene_permiso()`, que tiene el bypass de superadmin (`*` abre todo) integrado — una firma que "cualquier admin puede poner" no es una firma. Corregido comparando identidad directa contra el titular (`crud_rbac.titular_firma_equipo`), sin pasar por el motor de permisos genérico. El resto de acciones de aprobación (autorizar entrega, confirmar devolución, cerrar incidencia) siguen abiertas a cualquiera con `APROBADOR_EQUIPO`, sin cambio — la restricción es solo sobre la firma en sí.
- **`AdminView.jsx` (`/administracion`) tiraba la pantalla completa** con `ReferenceError: Cannot access 'cycleHistory' before initialization` — un `useSortable(cycleHistory, ...)` quedó declarado antes que el `useState` de `cycleHistory` al agregar los encabezados ordenables de tablas. Reordenado.
- **`/equipos/nuevo`, paso 2**: el card de "En este préstamo" (columna derecha) le faltaba el padding (`p-4`) que sí tiene el de la izquierda — se veía sin estilos ("delgado") en cuanto se agregaba un equipo.

### Pruebas

- Backend: 794 passed, 1 skipped (antes 786) — nuevos/actualizados en `test_loan_state.py`, `test_api_prestamos.py`, `test_aprobacion.py`, `test_media.py`, `test_notificaciones.py`, `test_responsiva_pdf.py`, `test_migracion_y_endpoints.py`.
- E2E (`equipos-flujo-completo.spec.js`, servidor real, 8 casos): actualizado para el wizard de 3 pasos y verificado en vivo contra un backend+DB aislados; de paso se corrigieron dos desfases preexistentes del archivo (selector de foto obsoleto, scoping de colas de Aprobaciones por `data-testid` en vez de `<section>`, que no existía en el markup real).
- De paso, corregido un drift preexistente no relacionado: a `frontend/.../mock/fixtures/permisos_catalogo.json` le faltaba `APROBADOR_PRESUPUESTOS` frente a su contrato congelado — ya sincronizados (`contrato-fixtures.spec.js` en verde).

---

## 2026-08-21 — Módulo Gastos Operativos

### Agregado
- **Nuevo módulo Gastos Operativos**, hermano de Presupuestos y Equipos: acumulador de gastos por **rubro** (catálogo propio editable), **aislado de marketing** (tablas, dashboard y exportación propios; sus totales no entran en ningún reporte de marketing). Sin ciclo, sin validación, sin límite.
  - Backend: tablas `expense_rubros` y `operational_expenses` (`models_operativos.py`); dos fechas (`fecha_gasto` manual define el mes, `upload_date` automática); comprobante obligatorio; **solo borrado lógico**. Endpoints `/api/rubros` (catálogo) y `/api/operational-expenses` (alta multipart, listado con filtros, descarga de comprobante autenticada, borrado lógico, `dashboard`, `export`). `crud_operativos.py`, `schemas_operativos.py`, seed idempotente `seed_gastos_operativos.py`.
  - RBAC: módulo `gastos_operativos` (`ver`/`crear`/`borrar`/`exportar`/`gestionar_rubros`) y rol base nuevo `operativo` (solo este módulo). Acceso: `admin`, `superadmin`, `operativo`; marketing sin acceso. Reflejado en el contrato congelado `permisos_catalogo.json`.
  - Frontend: módulo `modules/gastos-operativos/` (Layout + sidebar + Registro/Dashboard/Rubros), tercer tab en el switch de módulos (gateado por permiso), con cámara en móvil para el comprobante y visor de imágenes compartido.
  - Pruebas: `tests/operativos/` (16) + RBAC y migración/seeds actualizados; `DeleteConfirmModal` ahora oculta el borrado físico cuando el llamador no lo provee.
- Documentación: `docs/gastos-operativos/plan-implementacion.md` y `docs/gastos-operativos/manual-usuario.md`; regla crítica en `CLAUDE.md`; índice en `docs/README.md`.

---

## 2026-08-19 — Reset de contraseña entre superadmins (R4.1)

### Agregado
- **`POST /api/users/{id}/reset-password-superadmin`** — un superadmin puede resetear la contraseña de OTRO superadmin desde la app (antes solo con el script de servidor): contraseña temporal + `must_change_password`, revoca sesiones, desbloquea si estaba bloqueada, audita con `action="password.reset_superadmin"`. Nunca sobre uno mismo; rol y estado siguen inmutables; no reactiva cuentas desactivadas (divergencia deliberada del script de emergencia).
- **`exclude_role` en `GET /api/users/`** — filtro server-side para que la tabla principal excluya superadmins sin romper la paginación.
- **`backend/crear_superadmin_extra.py`** — siembra un segundo superadmin local (la API no puede crearlos por diseño; `seed_auth` solo crea si no existe ninguno).
- **UI**: tabla separada "Superadministradores" en la gestión de usuarios (los superadmin no tienen opción de editar) con botón dedicado "Resetear contraseña" y **confirmación fuerte** — el botón solo se habilita tecleando el username exacto del objetivo. `PasswordTemporal` extraído a componente propio.
- Tests: +8 casos (200 con segundo superadmin verificando temp/must_change/token_version/lockout/revocación/audit, login con la temporal, 400 self, 400 destino no-superadmin, 404, 403 admin, 401 sin token, `exclude_role`).

### Actualizado
- CLAUDE.md: regla de inmutabilidad enmendada (rol/estado inmutables; contraseña reseteable por otro superadmin) y conteo de pruebas.
- `docs/presupuestos/auth/auth-arquitectura.md`: sección R4.1, fila de la matriz y notas.

---

## 2026-08-18 — Diagnóstico de seguridad + lote de calidad (pulido UX/a11y/repo)

### Corregido (seguridad)

- **CRÍTICA: contraseñas en texto plano en `audit_log`.** El middleware de auditoría capturaba el body JSON de todo `/api/*` salvo login: cada cambio de contraseña y cada alta de usuario persistía la credencial en claro (con bypass vía `POST /api/auth/login/`). Ahora: redacción por campo (password/current_password/new_password/token/secret/authorization) + exclusión de change-password/refresh + comparación de rutas sin trailing slash.
- **CRÍTICA: auto-aprobación de tickets por cualquier rol no-creador.** `usuario`/`colaborador_mkt`/`marketing_*` podían crear tickets auto-aprobados que descontaban presupuesto de cualquier creador. Ahora solo `admin`/`superadmin` auto-aprueban; todo rol nuevo nace `pendiente`.
- **ALTA: `GET /api/tickets/` listaba todo a cualquier sesión** (montos, notas, `file_path` de disco). Ahora 403 para roles sin Presupuestos (`ROLES_CON_TICKETS`, misma allowlist que `download_file`).
- Test de regresión de path traversal del fallback SPA (el hotfix del 18/08 no tenía test) + 2 tests obsoletos corregidos + fixtures nuevos (`usuario`, `colaborador_mkt`).

### Agregado (calidad)

- **Página 404 personalizada** en ambos módulos (antes: redirección silenciosa a `/` o área vacía) — `design/NotFoundPage.jsx` + spec e2e.
- **ErrorBoundary global** con pantalla de recuperación (el crash de ApexCharts del 15/07 dejó pantalla en blanco; no volverá a pasar).
- **Título del documento por ruta** ("Dashboard · GOCreate") en las 21 pantallas — hook `usePageTitle`.
- **Anillo de foco visible** (`:focus-visible` global, naranja de marca) para navegación por teclado.
- **README.md raíz** (GitHub ya no muestra página vacía), `.editorconfig`, `.nvmrc` (Node 24), Prettier (`npm run format`, adopción gradual), `package.json` saneado (nombre actualizado, description, engines).
- **Versión visible en la UI** ("GOCreate v1.1.0" en el menú de perfil; `version` de package.json inyectada por vite) + meta description, `theme-color` y `apple-touch-icon` 180×180.
- **ScrollToTop** en cambio de ruta (`behavior: instant` — el smooth global se sentía como bug).
- **Paleta de comandos (Ctrl+K)**: se hizo descubrible con un hint en el header, se detectó que nunca se conectó a nada (cero comandos registrados, siempre "Sin resultados") y, por decisión de producto en la prueba manual, **se eliminó por completo** (infraestructura + hint + atajo).
- **Formateador de moneda compartido** `formatMXN` (`design/formatos.js`) — elimina 11 copias idénticas del Intl es-MX; salida byte-idéntica.
- **Acentos consistentes** en mensajes visibles al usuario del backend (5 rezagados).

### Estado de pruebas

Suite backend: **680 passed, 1 skipped** (era 669/2-failed antes del diagnóstico). Build frontend: verde. `pip-audit`: 0 vulnerabilidades; `npm audit`: 2 moderadas en react-router (fix disponible en v7.18.2, requiere migración major — planificado).

### Documentación

- `docs/seguridad/diagnostico-seguridad-2026-08-18.md` — informe completo: 2 críticas / 3 altas / 10 medias / 13 bajas, con plan de remediación priorizado.

---

## 2026-08-04 — Renombre a GOCreate

### Actualizado
- Nombre del proyecto: **Ready2Go** → **GOCreate**. Actualizadas las menciones de marca en `CLAUDE.md`, `status.md`, `context.md`, `RISKS.md`, `BACKLOG.md`, `MVP_BREAKDOWN.md`, `avances_diarios.md`, `docs/`, frontend (`LoginPage.jsx`, `Header.jsx`, `index.html`) y backend (correos, PDF, logger, `.env.example`).
- El repo de GitHub **no** se renombro: sigue en `github.com/integracionesia-maker/Ready2Go` (decision explicita, para no romper los remotes de Jose/Beni sin coordinar). Las referencias textuales a esa URL se dejaron intactas.

---

## 2026-07-27 (tarde) — Integracion a master, contrato de API v1 y reparto en carriles

### Agregado
- `docs/contratos/` — **contrato de API v1, congelado.** Es la frontera entre los dos carriles de trabajo: HTTP, no un archivo.
  - `API_EQUIPOS_v1.md`: 24 endpoints con permiso, request, response de ejemplo y codigos de error; maquina de estados del prestamo; reglas de fecha y atraso; limites y validacion de media.
  - `permisos_catalogo.json`: 7 modulos, sus acciones, los 8 paquetes del RBAC aditivo y las reglas del motor.
  - `auth_me.json`: forma exacta de `GET /api/auth/me` con el campo `permisos`.
  - `tokens_marca.md`: colores y fuentes para el PDF del servidor.
  - `fixtures/`: 8 equipos de la auditoria del 10/06, 3 razones sociales, un prestamo demo como criterio de aceptacion del payload, y los codigos de error feos (409, 403, 503, 413, 422, 401).
  - `CHANGELOG_CONTRATO.md`: lo que se aparta del plan y por que.
- `docs/ASIGNACION_EQUIPOS.md` en cada rama de trabajo — tareas ordenadas y atomicas, rutas propias, rutas fuera de alcance, como se reporta y definicion de terminado. Cada rama lleva solo la suya.

### Actualizado
- `master` = integracion del plan (`--no-ff`) + contrato v1. Replicado a las tres ramas.
- `status.md` — Fase 5 Build, sin bloqueo, carriles declarados.

### Decisiones
- **Corte del trabajo por capa**, frontera en el contrato HTTP. Interseccion de codigo entre carriles: cero archivos. De 47 archivos en disputa, 41 se resuelven por pertenencia de capa; los 6 de gobernanza pasan a integracion.
- **Rutas de la API unificadas en ingles** (`/api/equipment/dashboard`, no `/api/equipos/dashboard`): mezclar idiomas en el mismo recurso garantiza un bug de cliente.
- Tres huecos del plan cerrados en el contrato: miniatura de 96px generada en servidor (sin ella el inventario baja 3 MB por thumb), recuperar borrador propio (`?estado=borrador&mios=1`), y busqueda por folio (la ficha se navega por folio, la API solo hablaba por id).
- El listado de inventario devuelve `tenedor_actual`, `fecha_regreso_esperada`, `atrasado` y `dias_atraso` en la propia fila: la pantalla los pinta sin un segundo request.
- **Los documentos de estado de la raiz quedan congelados para los carriles.** Cada uno reporta en sus propios archivos bajo `docs/`; la consolidacion es de la integracion. Evita el conflicto de merge garantizado en markdown de linea por fila.

### Pendiente asentado
- `openapi_equipos_v1.json` no existe todavia: se genera del servidor cuando existan los primeros endpoints y se congela. Hasta entonces manda `API_EQUIPOS_v1.md` y la prueba guardia va en `skip` con el motivo escrito.

### Limpieza
- Rama remota basura `origin` eliminada (cero commits propios, respaldada con tag y bundle antes de borrar). El remoto queda con master y las tres ramas de trabajo.

---

## 2026-07-27 — Renombre a Ready2Go + plan de integracion de Control de Equipos (Fase 3.5)

### Agregado
- `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md` — plan quirurgico completo del modulo Control de Prestamo de Equipo: contexto de la reunion con marketing, decisiones tomadas, RBAC aditivo (3 tablas + motor deny-by-default), modelo de datos de 11 tablas, maquina de estados del prestamo, API nueva (24 endpoints), PDF de responsiva en servidor versionado, notificaciones SMTP con log idempotente, direccion visual liquid glass, 22 hallazgos de revision adversarial, plan de trabajo en 9 paquetes, verificacion y rollback.
- `docs/maqueta/CONTROL_DE_EQUIPOS_maqueta_mkt.htm` — maqueta HTML de marketing como especificacion funcional de referencia (su implementacion no se porta: localStorage, `mailto:`, HTML renderizado en el estado, importar/borrar todo desde la UI).
- `CHANGELOG.md` — este archivo (faltaba).
- Rama `jose-branch` para supervision de Jose.

### Actualizado
- Remote de git: `integracionesia-maker/presupuesto_creadores` → **`integracionesia-maker/Ready2Go`**. Carpeta local renombrada a `Ready2Go`.
- `CLAUDE.md` — nombre, alcance de dos modulos, politica de ramas por persona, regla de roles aditivos, decision de tipografia, direccion visual y sus limites.
- `context.md` — reescrito: dos modulos, tabla de fases por modulo, usuarios y roles (incluido `colaborador_mkt` y los aditivos), proceso objetivo de prestamo, dependencias de terceros.
- `status.md` — Fase 3.5, owner Damian, metricas reales (167 pruebas, 3 suites e2e, git si), metricas de impacto esperadas del modulo nuevo, bloqueo = luz verde de build.
- `MVP_BREAKDOWN.md` — dividido en modulo A (Presupuestos, 10/13 = 77%) y modulo B (Equipos, 0/12). Total 10/25 = **40%**. El porcentaje baja porque el alcance crecio.
- `BACKLOG.md` — 17 tareas nuevas del modulo Equipos ordenadas por paquete de trabajo, 7 pendientes de terceros, cierre de los pendientes historicos ya resueltos (git, auth, owner, responsividad, R12).
- `RISKS.md` — cerrados 3 riesgos obsoletos (sin git, owner sin confirmar, tipografia sin decidir); elevado el de backups (ahora `uploads/` guardara responsivas firmadas); 4 riesgos nuevos (el modulo no sirve en localhost, firma en canvas no es firma avanzada, alcance duplicado sin owner tecnico, rendimiento del cristal).
- `DESIGN_SYSTEM.md` — direccion liquid glass con receta CSS unica, 7 reglas duras (incluido que el SVG `backdrop-filter` es solo Chromium y que el cristal esta prohibido en tablas y scroll), tipografia oficial de marca decidida, componentes del sistema, presupuesto de rendimiento y registro de decisiones.

### Decisiones
- Arquitectura: **misma app FastAPI, misma DB SQLite, tablas nuevas** (descartado: DB aparte, servicio aparte).
- Roles: **aditivos** (patron portado de la implementacion de RBAC granular de otro proyecto del pool) — `users.role` sigue siendo el rol base.
- Notificaciones: **correo SMTP corporativo** (descartado WhatsApp por costo de API de Meta; Telegram y Resend por piezas extra que administrar).
- Responsiva: **PDF generado en servidor** (reportlab) y adjunto al correo, versionado y con hash; nunca se sobrescribe.
- Frontend: **100% React**, liquid glass en toda la app, React 18.3.1 (no se salta a 19 en esta entrega).

### Nota de proceso
La pasada adversarial del plan la hizo el agente principal por enumeracion, no tres agentes independientes en paralelo como pide el framework (fan-out deshabilitado en la sesion). Queda declarado en §10 del plan.

---

## 2026-07-23 — Responsividad movil + gastos generales vinculados a marca (R12.1)

### Agregado
- Responsividad movil completa: tablas, KPIs, graficas, modales y navegacion usables desde 320px. `hooks/useMobile.js`, `components/RowActions.jsx`, clases `go-table-scroll-wrapper`/`go-table-scroll`. Ver `doc/responsividad-movil.md`.
- Gastos generales vinculados a la tabla de marcas.

---

## 2026-07-17 — Autenticacion, roles, ciclos de presupuesto y validacion de tickets

### Agregado
- Sistema de autenticacion: JWT en cookie httpOnly + refresh token con rotacion, bloqueo incremental y rate limit de login, 3 roles con matriz de permisos por endpoint. Ver `doc/auth-arquitectura.md`.
- Ciclos de presupuesto semanal/mensual (snapshot inmutable), validacion de tickets (`pendiente → aprobado/rechazado`), prioridad de marcas. Ver `doc/presupuestos-y-validacion.md`.
- Gastos generales y borrado logico/fisico de tickets con reversion de ciclo (R12). Ver `doc/gastos-generales-manual.md`, `doc/borrado-tickets.md`.
- Repo git inicializado.

### Corregido
- IDOR en descarga de comprobantes: `GET /api/tickets/file/{id}` ahora responde 403 si el ticket no es del creador autenticado.
- `/uploads` como mount estatico eliminado: todo archivo se sirve por endpoint autenticado.

---

## 2026-07-15 — Estabilizacion del dashboard y limpieza de datos

### Corregido
- "Invalid hook call" por React duplicado: alias manual de `react`/`react-dom` eliminado de `vite.config.js`.
- Crash de ApexCharts por claves `undefined` explicitas en `createApexOptions`.
- KPI "Marcas Activas" mostraba 89 en vez de 8 (contaba filas del JOIN).
- Sobregiro de 3 creadores tras fusionar duplicados por acentos.

### Agregado
- 12 meses de historial de tickets de prueba; `seed.py` corregido para no reintroducir duplicados por acentos.
