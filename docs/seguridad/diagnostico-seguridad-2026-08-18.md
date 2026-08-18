# Diagnóstico de Seguridad — GOCreate — 2026-08-18

> Alcance: repositorio completo (`backend/`, `frontend/`, `docs/`, configuración), ~10.8k líneas backend + ~17.3k líneas frontend.
> Método: 4 revisiones independientes por dominio (auth/sesión, acceso a datos, archivos/infra, frontend) + verificación personal de cada hallazgo contra el código real + `pip-audit`/`npm audit` + suite pytest completa (672 pruebas) + análisis del historial git (incluido el hotfix de path traversal del mismo día).
> Convención de severidad: **CRÍTICA** (compromiso de datos/credenciales), **ALTA** (fuga de datos de negocio o DoS dirigido), **MEDIA** (superficie de ataque real con mitigación parcial), **BAJA** (higiene/robustez).

---

## Resumen ejecutivo

| Severidad | Total | Corregido hoy | Pendiente (recomendación) |
|---|---|---|---|
| CRÍTICA | 2 | 2 | 0 |
| ALTA | 3 | 1 | 2 |
| MEDIA | 10 | 2 | 8 |
| BAJA | 13 | 0 | 13 |

Los dos hallazgos críticos eran: **(1)** contraseñas en texto plano persistidas en `audit_log` por el middleware de auditoría (cada cambio de contraseña y cada alta de usuario dejaba la credencial en claro en la base, para siempre), y **(2)** cualquier rol nuevo (`usuario`, `colaborador_mkt`, `marketing_*`) podía crear tickets **auto-aprobados** que descontaban presupuesto de cualquier creador sin validación. Ambos quedaron corregidos con pruebas de regresión.

El módulo **Control de Equipos** salió limpio: RBAC por catálogo correcto, sin IDOR, magic bytes, PDF escapado, correo sin inyección. Los problemas se concentran en el módulo **Presupuestos**, que nunca se migró al RBAC nuevo, y en deudas de infraestructura ya conocidas (HTTPS, backups, cabeceras).

---

## Cambios aplicados en esta sesión

| Archivo | Cambio |
|---|---|
| `backend/app/middleware_audit.py` | Redacción de campos sensibles (`password`, `current_password`, `new_password`, `token`, `secret`, `authorization`, …) en `request_body_summary` + exclusión de `/api/auth/change-password` y `/api/auth/refresh` + comparación de rutas **sin trailing slash** (cerraba el bypass `POST /api/auth/login/`) |
| `backend/app/routers/tickets.py` | **Auto-aprobación corregida**: solo `admin`/`superadmin` auto-aprueban; todo rol nuevo nace `pendiente`. **`GET /api/tickets/` restringido** a los roles con acceso a Presupuestos (misma allowlist que `download_file`, ahora constante compartida `ROLES_CON_TICKETS`) |
| `backend/tests/conftest.py` | Fixtures nuevos: `usuario_user`, `logged_in_usuario`, `colaborador_mkt_user`, `logged_in_colaborador_mkt` |
| `backend/tests/test_permissions.py` | 2 tests obsoletos corregidos (mount de uploads agnóstico a `frontend/dist`; payload de creador con `username`/`email`) + **test de regresión de path traversal del fallback SPA** + clase nueva `TestRolesSinAccesoPresupuestos` (5 tests) |
| `backend/tests/test_audit_log.py` | 3 tests de regresión de redacción de credenciales en auditoría |
| `frontend/src/modules/presupuestos/components/AdminView.jsx` | Eliminada la auto-copia de la contraseña temporal al portapapeles al montar el modal (solo se copia con clic explícito) |
| `frontend/src/modules/presupuestos/roles.js` | Nueva constante `TICKETS_ROLES` (espejo de `ROLES_CON_TICKETS` del backend) |
| `frontend/src/modules/presupuestos/PresupuestosLayout.jsx` | Ruta `/transacciones` protegida con `ProtectedRoute roles={TICKETS_ROLES}` |

---

## Hallazgos CRÍTICOS

### C1. Contraseñas en texto plano persistidas en `audit_log` — **CORREGIDO**

**Código original** (`backend/app/middleware_audit.py`): el middleware capturaba el cuerpo JSON (hasta 500 chars) de **todo** `/api/*` salvo `/api/auth/login`, por coincidencia exacta de string.

**Explotación:** `POST /api/auth/change-password` envía `{"current_password": "...", "new_password": "..."}` (`schemas.py:239-241`); `POST /api/users` acepta `password` explícito (`schemas.py:247-253`). Ambos cuerpos quedaban íntegros en `audit_log.request_body_summary` — la contraseña vigente de cada usuario (incluido superadmin) en claro, retroactivamente, en el mismo archivo SQLite que guarda los hashes argon2. Exposición por API: `GET /api/audit-logs/{id}` (`crud_audit.py:138`). Bypass adicional: `POST /api/auth/login/` (barra final) no matcheaba la exclusión y el body con la contraseña se capturaba igual (respuesta 405 del catch-all SPA).

**Corrección:** exclusión de rutas con credenciales + redacción por regex de campos sensibles en `_resumen_body` (segunda línea de defensa para rutas futuras) + normalización de trailing slash antes de comparar.

**Regresión:** `test_change_password_no_persiste_el_body`, `test_login_con_trailing_slash_no_persiste_password`, `test_alta_de_usuario_redacta_password` (`tests/test_audit_log.py`).

**Pendiente (no bloqueante):** las filas de `audit_log` **ya persistidas** con contraseñas en claro (creadas antes de hoy) siguen en `backend/presupuesto.db`. Recomendado: script de saneo que ponga `NULL` en `request_body_summary` de las rutas `/api/auth/change-password` y `/api/users` anteriores al fix.

### C2. Auto-aprobación de tickets para cualquier rol que no sea "creador" — **CORREGIDO**

**Código original** (`backend/app/routers/tickets.py:150-157`):

```python
status = (
    models.TicketStatus.PENDIENTE.value
    if current_user.role == "creador"
    else models.TicketStatus.APROBADO.value
)
```

La regla del proyecto (CLAUDE.md) dice: *"Solo los tickets subidos por un `creador` nacen `pendiente`; los de `admin`/`superadmin` se auto-aprueban"*. El código implementaba "todo el que NO sea creador se auto-aprueba". Con los roles nuevos (`usuario`, `colaborador_mkt`, `marketing_equipos`, `marketing_basico`, …) cualquier sesión autenticada podía `POST /api/tickets/` con `creator_id` de cualquier creador, `amount` arbitrario, y el ticket nacía `aprobado` descontando `cycle.spent` de inmediato (`crud.py:297-300`) — sin validación, sin permisos de presupuestos en el catálogo (`rbac_catalog.py`: `usuario` = solo piso).

**Corrección:** `auto_aprobado = current_user.role in ("admin", "superadmin")`; todo lo demás nace `pendiente` y pasa por la cola de validación.

**Regresión:** `test_usuario_ticket_nace_pendiente_y_no_descuenta_ciclo` (verifica además `cycle.spent == 0`), `test_colaborador_mkt_ticket_nace_pendiente`, `test_admin_ticket_sigue_auto_aprobado` (protege contra sobre-corrección).

---

## Hallazgos ALTOS

### A1. `GET /api/tickets/` listaba TODOS los tickets (montos, notas, `file_path` de disco) a cualquier sesión — **CORREGIDO**

Solo `creador` y `marketing_basico` tenían scoping; el `else` (`tickets.py:78-82`) entregaba el listado completo a `usuario`, `colaborador_mkt`, `marketing_equipos` y cualquier paquete solo-equipos, con la ruta absoluta del comprobante en disco (`schemas.py:102`). Misma raíz que C2: módulo Presupuestos fuera del RBAC.

**Corrección:** allowlist `ROLES_CON_TICKETS` (la misma que ya usaba `download_file`) → 403 para roles sin acceso. Regresión: `test_usuario_no_puede_listar_tickets`, `test_colaborador_mkt_no_puede_listar_tickets`.

**Residual (documentado):** un usuario con paquete `AUDITOR` (concede `presupuestos:ver_global` en el catálogo) recibe 403 en este endpoint. Inconsistencia del catálogo vs. endpoints legacy — ver hallazgo M4.

### A2. DoS por bloqueo de cuentas + oráculo de enumeración de usuarios — **RECOMENDADO**

- Mensaje distinto para cuenta bloqueada (`auth.py:78-81`: "Cuenta bloqueada temporalmente…") vs. credenciales inválidas (`auth.py:66`) → confirma existencia de username (los usernames son nombres de pila, predecibles). Hay incluso un test que afirma el mensaje distintivo como contrato (`test_auth.py:52-59`).
- Bloqueo exponencial (5→10→20→40→60 min, `crud.py:753-759`) y `failed_login_attempts` solo se resetea con login exitoso: ~26 intentos/día bastan para mantener bloqueada **indefinidamente** cualquier cuenta, incluida la única `superadmin` (sin endpoint de desbloqueo; el reset de contraseña no limpia `locked_until`).
- El rate limit por IP (30/15min, en memoria) no frena a un atacante con varias IPs.

**Recomendación:** mensaje único para ambos casos; desbloquear en reset de contraseña/reactivación; límite por usuario además del de IP. **No corregido hoy** porque el mensaje distintivo es comportamiento afirmado por un test existente — es decisión de producto cambiar ese contrato.

### A3. PII real del equipo en el repositorio git — **RECOMENDADO (requiere decisión)**

Tres capas de datos reales commiteados:
1. `backend/seed_usuarios_mkt.py:28-50` — directorio real del área: 14 nombres completos + correos corporativos (Melisa Avendaño, José Aguilar, Emily Pérez, Betzabet Fuentes, …). Es el seed funcional de las cuentas reales locales.
2. `docs/contratos/fixtures/` (contrato congelado) + `backend/seed_equipos.py`/`seed_prestamo_demo.py` — demo con nombres reales ("Melisa Avendano", "Ana Ruiz"), nombres de empleados en el inventario ("Jeziel", "Barbara"), razón social + RFC + dirección reales de un proveedor (`SCQ1212149P0`).
3. Copias literales en `frontend/src/modules/equipos/api/mock/fixtures/` (con guardia de igualdad en `e2e/contrato-fixtures.spec.js` y `tests/equipos/test_fixture_demo.py`).

**Por qué no se saneó hoy:** la capa 2 vive en el **contrato congelado** con pruebas de igualdad en ambos lados (pytest y Playwright) y nombres de usuario atados en los tests (`ana.ruiz`, `melisa`). Sanear requiere un cambio de contrato coordinado con entrada en `CHANGELOG_CONTRATO.md`.

**Plan propuesto (cuando decidas):** (a) renombrar usuarios demo a `melisa.aprobadora`/`ana.solicitante` con `@example.com`, equipos "(sin asignar)", empresas y RFC ficticios en: `docs/contratos/fixtures/*`, `seed_equipos.py`, `seed_prestamo_demo.py`, `tests/equipos/test_fixture_demo.py`, fixtures del mock; (b) decidir con marketing si el directorio real en `seed_usuarios_mkt.py` se queda (repo privado de la org) o se sustituye por plantilla sintética; (c) considerar que `C:\Users\USUARIO\drive\` sugiere sincronización con Google Drive — si la carpeta está sincronizada, `.env` (JWT_SECRET_KEY, SMTP) y `presupuesto.db` suben a la nube; confirmar y excluir de la sincronización.

---

## Hallazgos MEDIOS

### M1. Subida de comprobantes sin magic bytes (contrasta con el módulo Equipos que sí los valida)
`upload_manager.py:18-30` valida extensión + `Content-Type` declarado **por el cliente**; el MIME atacante-controlado se guarda en DB y se sirve en `tickets.py:119`. El vector XSS por contenido activo está mitigado por construcción (sin SVG permitido, `attachment`, MIME imagen/PDF), pero es deuda de defensa en profundidad y permite distribuir contenido falso (HTML como "comprobante.jpg"). **Recomendación:** portar la validación por firma de `media_manager.py:89-101` (PNG `\x89PNG`, JPEG `\xff\xd8\xff`, PDF `%PDF`) y derivar el MIME de los bytes.

### M2. Lectura completa del archivo a RAM antes de validar el límite de 10 MB
`upload_manager.py:39-44`: `contents = file.file.read()` y recién después el chequeo de tamaño. Un archivo de 10 GB se lee completo a RAM (DoS) pudiendo abortar en el byte 10 MB+1. Ídem en `loans.py:346`. **Recomendación:** lectura por chunks con aborto temprano.

### M3. Bomba de descompresión parcial en miniaturas de media
`media_manager.py:65-69` permite hasta 50 Mpx y `miniatura()` (`:222-248`) decodifica el bitmap completo por cada `GET /api/media/{id}?tamano=thumb` (sin caché: `Cache-Control: private, max-age=0`): ~200-400 MB de RAM por request con un PNG sólido de pocos cientos de KB. **Recomendación:** bajar el tope de píxeles (12-20 Mpx), cachear la miniatura en disco al subir, o servir con caché pública.

### M4. Módulo Presupuestos fuera del RBAC: catálogo decorativo y doble deriva
Ningún endpoint de `tickets.py`/`creators.py`/`brands.py`/`dashboard.py`/`general_expenses.py` usa `require_perm`; siguen con `require_role` + listas hardcodeadas que divergen del catálogo en ambas direcciones: `marketing_presupuestos`/`marketing_admin` tienen `validar_ticket` en el catálogo pero reciben 403 al aprobar (`tickets.py` usa `require_role("admin","superadmin")`); `AUDITOR` tiene `ver_global` pero `list_tickets` le corta 403 (post-fix). El módulo Equipos demuestra el patrón correcto (`require_cualquiera`, scoping server-side en `loans.py`). **Recomendación:** migrar los 5 routers al catálogo (`ver_global`/`ver_propio`/`subir_ticket`/`validar_ticket`/`borrar_ticket`/`gestionar_ciclos`/`gastos_generales`/`exportar`), cerrando de raíz A1/C2 y la vista abierta de `creators.py:25-34` (listado de creadores y ciclos a cualquier sesión, con materialización de ciclos desde un GET en `creators.py:71`).

### M5. Sin cabeceras de seguridad en ninguna respuesta
Sin `X-Content-Type-Options: nosniff`, `X-Frame-Options`/`frame-ancestors`, `CSP`, `Referrer-Policy` ni HSTS (`main.py` sin middleware de seguridad; `index.html` sin meta CSP). El servido inline de media sin `nosniff` amplifica M1. **Recomendación:** middleware que fije `nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: same-origin` y CSP `default-src 'self'`; HSTS al cerrar HTTPS (prerequisito ya documentado).

### M6. Fuga de detalle de errores del sistema en respuestas 500
`upload_manager.py:49` (`detail=f"Error al guardar el archivo: {exc}"`), `tickets.py:193`, `general_expenses.py:129` — exponen rutas absolutas del filesystem y fragmentos de error al cliente. **Recomendación:** loggear en servidor, responder mensaje genérico.

### M7. `must_change_password` se escribe pero nunca se exige
`users.py:189` marca la flag al resetear contraseña, pero ni `login` ni `get_current_user` la revisan (el test `test_auth.py:46-49` afirma login 200 con flag activa). La contraseña temporal (`Temporal-` + 64 bits, `security.py:67-68`) queda válida indefinidamente. **Recomendación:** exigir el cambio en login (403/412 con scope restringido) — requiere actualizar el test que afirma lo contrario.

### M8. Enumeración de usuarios por timing en login
Usuario inexistente → respuesta inmediata; existente → `argon2.verify` (~50-200ms) (`auth.py:69-93`). **Recomendación:** verificar contra hash dummy de coste equivalente cuando el usuario no existe.

### M9. Rate limit de login solo por IP, en memoria, sin limpieza, y cuenta logins exitosos
`security.py:112-130` + `auth.py:58-64`: el dict nunca elimina claves (fuga lenta de memoria), los logins exitosos consumen bucket (una oficina NAT se auto-bloquea a 30/15min), y no hay límite por usuario. **Recomendación:** bucket `(IP, usuario)`, TTL de claves, no contar éxitos. Nota: no confía en `X-Forwarded-For` — correcto.

### M10. Auto-copia de contraseña temporal al portapapeles — **CORREGIDO**
`AdminView.jsx` escribía la contraseña temporal en el portapapeles del sistema al montar el modal, sin gesto del usuario (máquinas compartidas: el siguiente Ctrl+V la vierte en cualquier app). Eliminado el `useEffect`; solo se copia con el botón explícito.

---

## Hallazgos BAJOS

| # | Hallazgo | Ubicación | Recomendación |
|---|---|---|---|
| B1 | `int(payload["sub"])` → 500 si el JWT no trae `sub` | `dependencies.py:19` | `payload.get("sub")` + validación |
| B2 | `JWT_SECRET_KEY` sin longitud mínima (una clave de 3 chars arranca) | `security.py:24-31` | exigir ≥32 bytes al arrancar |
| B3 | `CORS_ORIGINS="*"` con `allow_credentials=True` reflejaría cualquier origen | `main.py:25-28,49-55` | rechazar wildcard con credenciales (fail-fast) |
| B4 | Sin rate limit en `change-password` (fuerza bruta de `current_password` con sesión robada) | `auth.py:210-218` | límite por usuario en el endpoint |
| B5 | Carrera en rotación concurrente de refresh (dos refreshes paralelos pueden dejar dos tokens vivos) | `auth.py:138-143`, `crud.py:789-801` | `UPDATE … WHERE revoked_at IS NULL` atómico |
| B6 | Política de contraseña sin blocklist de comunes (`password123` con un dígito pasa) | `security.py:54-64` | blocklist + variantes del nombre |
| B7 | `crud.get_ticket`/`get_general_expense` sin `is_deleted == False` — la invariante vive en los call sites (bomba de tiempo para el próximo endpoint) | `crud.py:261-262,572-573` | meter el filtro en el crud (patrón: `crud_loans.obtener`) |
| B8 | `crud.approve_ticket` no valida estado: doble aprobación re-descontaría el ciclo si se llamara sin la guarda del router | `crud.py:308-322` | guarda idempotente como `crud_loans.autorizar_entrega` |
| B9 | Scoping de listado de préstamos (solo `responsable_user_id`) vs. detalle (5 campos de participación) — inconsistencia documentada | `crud_loans.py:326-329` vs `113-116` | unificar definición de participante |
| B10 | `GET /%00` (byte nulo) → 500 en el fallback SPA; y `/api/typo` responde `index.html` 200 en vez de 404 JSON | `main.py:122-133` | `try/except ValueError` + excluir `/api/*` del catch-all |
| B11 | `mailer._armar` fuera del `try`: `responsable_email` con CRLF (schema sin `EmailStr`, `schemas_loans.py:129`) produce `ValueError` fuera del contrato "nunca levanta" y notificación reintentando para siempre | `mailer.py:131`, `notificaciones.py:288-291` | `EmailStr` + mover `_armar` al try |
| B12 | `/docs`/`/redoc` abiertos si `ENV` no está seteada; `SMTP_STARTTLS` apagable sin guarda de producción | `main.py:31,44-45`, `mailer.py:71` | default seguro + enforcement en producción |
| B13 | Huérfanos en `uploads/` ante crash entre escritura y commit | `upload_manager.py:45` | barrido periódico o escritura post-commit |
| B14 | `EquiposLayout` redirige en silencio si `permisos` llega vacío (debería ser pantalla de error con reintento, como `ProtectedRoute` con `networkError`) | `EquiposLayout.jsx:17-23` | distinguir "sin permiso" de "resolución fallida" |

---

## Dependencias

- **`pip-audit`** (backend, `requirements.txt` + `requirements-dev.txt`): **0 vulnerabilidades conocidas**.
- **`npm audit`** (frontend, lockfile temporal sobre `package.json`): **2 moderadas** en `react-router` / `react-router-dom@^6.30.4`:
  - GHSA-wrjc-x8rr-h8h6 — open redirect vía backslash en `<Link>`/`useNavigate` (bypass de CVE-2025-68470).
  - GHSA-337j-9hxr-rhxg — inyección de constructor vía `deserializeErrors()` en SSR (no aplica: la app es SPA sin SSR).
  - **Impacto real:** bajo. Los `navigate()` de la app usan rutas fijas o `pathname` propio del router (`LoginPage.jsx:18,28`); no hay input de usuario en los destinos. **Fix disponible:** `react-router-dom@7.18.2` (major — requiere migración de la v6; planificar, no urgente).

---

## Lo que se verificó limpio (sin hallazgos)

- **Path traversal del fallback SPA** (hotfix de ayer): contención completa — `realpath` + `startswith(dist + sep)` cubre rutas absolutas, `..`/`..\`, `%2e`/`%2e%2e`, doble encoding, symlinks y case-mixing en Windows. Verificado empíricamente + test de regresión agregado hoy.
- **Rotación de refresh tokens**: rotación con detección de reuso que revoca toda la cadena y bump de `token_version` (`auth.py:115-127`); logout y cambio de contraseña matan sesiones robadas.
- **Validación JWT**: `algorithms=[HS256]` fijo (sin alg-confusion), exp/iat verificados, `JWT_SECRET_KEY` obligatoria (fallo ruidoso), el claim `role` del JWT es inerte (los permisos se resuelven de la DB por request).
- **Cookies**: `HttpOnly` en ambas, `Secure` con `ENV=production`, `SameSite=Lax`, paths correctos.
- **Módulo Control de Equipos completo**: RBAC por catálogo consistente, scoping server-side por participación, máquina de estados en todas las transiciones, `is_deleted` en todas las queries, media con magic bytes y autorización por participación, PDF con escaping XML completo, folio transaccional con UNIQUE, cero IDOR.
- **Sin SQL injection**: todo parametrizado; whitelists en `sort_by`; `folio.py` con bind params.
- **Frontend**: cero sinks XSS (`dangerouslySetInnerHTML`/`innerHTML`/`eval`/`document.write`), sin tokens en localStorage (solo theme/sidebar/clave del mock), `window.open` con `noopener`, rutas DEV gated por `import.meta.env.DEV`, sin `console.log` de datos sensibles, `Math.random` solo en texto decorativo, `csvEscape` con defensa contra fórmulas.
- **Sin `eval`/`exec`/`subprocess`/`pickle`/`yaml.load`** en `app/` (subprocess solo en tests); `random` solo en seeds.
- **`.env` correctamente ignorado en git** (solo `.env.example` trackeado).
- **Gestión de usuarios**: sin escalada a superadmin, superadmin inmutable por API, solo superadmin gestiona usuarios (R4), `reset_superadmin_password.py` como vía fuera de la app.

---

## Pruebas agregadas hoy (regresiones de seguridad)

1. `test_spa_fallback_does_not_serve_outside_dist` — path traversal del fallback SPA (3 payloads `%2e%2e`).
2. `test_uploads_static_mount_removed` — corregido a agnóstico del entorno (`frontend/dist` presente o no).
3. `test_admin_can_create_and_update_creator` — corregido al payload con `username`/`email`.
4. `TestRolesSinAccesoPresupuestos` (5): usuario/colaborador_mkt no listan tickets; sus tickets nacen pendientes sin descuento de ciclo; admin sigue auto-aprobando.
5. Redacción de auditoría (3): change-password sin body, login con trailing slash sin contraseña, alta de usuario con `"password":"***"`.

Resultado de la suite completa tras los cambios: **680 passed, 1 skipped, 0 failed** (antes del diagnóstico: 669 passed, 2 failed, 1 skipped — los 2 rojos eran tests obsoletos, corregidos como parte de este trabajo). `npm run build` del frontend: exitoso.

---

## Plan de remediación priorizado

**Ya hecho hoy:** C1, C2, A1, M10, ruta `/transacciones` protegida, regresiones.

1. **Saneo de datos históricos**: `NULL` en `request_body_summary` de `audit_log` para las rutas de credenciales previas al fix de C1 (script one-off).
2. **Migrar Presupuestos al RBAC del catálogo** (M4) — cierra la deriva sobre-restrictiva/bajo-restrictiva y las vistas abiertas de `creators.py`; es el cambio estructural de mayor retorno.
3. **Magic bytes + lectura por chunks en `upload_manager`** (M1+M2) y cabeceras de seguridad (M5) — los tres son cambios acotados y de bajo riesgo.
4. **A2 (bloqueo/oráculo) y M7 (`must_change_password`)** — requieren decisión de producto (cambian contratos afirmados por tests actuales) y actualización de esos tests.
5. **Decidir sobre PII en el repo (A3)**: plan de saneo del contrato congelado + directorio en `seed_usuarios_mkt.py` + verificación de sincronización de `C:\Users\USUARIO\drive\`.
6. **Backups de `presupuesto.db` + `uploads/`** (RISKS #3, BACKLOG #3) — hoy el riesgo #1 no atendido.
7. **`react-router-dom` 6→7.18.2** cuando haya ventana (fix de las 2 moderadas).
8. **HTTPS + CSP/HSTS + dominio** antes de exponer fuera de `127.0.0.1` (RISKS #7, #9) — prerequisito del piloto de Equipos.
9. **`SECURITY.md`** (BACKLOG #5) — puede nacer de este documento.

## Gobernanza pendiente (contexto, no seguridad)

Los docs raíz (`CLAUDE.md`, `status.md`, `BACKLOG.md`, `MVP_BREAKDOWN.md`, `avances_diarios.md`) siguen congelados al 04/08 y afirman que Control de Equipos está "sin construir" (Módulo B 0/12), cuando está construido e integrado con 672 pruebas. Recomendado actualizarlos; el CLAUDE.md raíz también debería reflejar las correcciones de este diagnóstico en "Reglas críticas".

---

*Generado por diagnóstico automatizado + verificación manual el 2026-08-18. Los hallazgos de agentes de revisión se verificaron uno a uno contra el código antes de incluirlos; los falsos positivos se descartaron.*
