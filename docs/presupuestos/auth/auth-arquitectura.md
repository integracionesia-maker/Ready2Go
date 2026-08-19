# Arquitectura del sistema de autenticación, usuarios, roles y permisos

> Diseño final implementado (Fases 2-3 completas: código en `dami-branch`, 167 pruebas pytest + 16 E2E Playwright en verde). Complementa — y en algunos puntos corrige — el diseño preliminar de Fase 1 (archivado, ver `docs/historico/prompt-sistema-autenticacion.md`).
>
> **Actualizado por el paquete R1-R11** (`docs/historico/prompt-mejoras-integrales.md`): la matriz de permisos cambió (R4-R6, ver §3.1) y se agregaron endpoints nuevos (ciclos de presupuesto, validación de tickets). Reglas de negocio completas de esa parte en `docs/presupuestos/presupuestos-y-validacion.md`.
>
> **Actualizado por el paquete R12** (`docs/historico/plan-gastos-generales-y-borrado-tickets.md`): endpoints nuevos de gastos generales y borrado lógico/físico de tickets, todos exclusivos de `admin`/`superadmin` (ver §3.1). Reglas de negocio completas en `docs/presupuestos/gastos-generales-manual.md` y `docs/presupuestos/borrado-tickets.md`.

---

## 1. Resumen

Se agregó autenticación por cookies httpOnly (JWT de acceso + refresh opaco con rotación), tres roles (`superadmin`, `admin`, `creador`) y una matriz de permisos aplicada en cada endpoint. El riesgo **RISKS.md #2** ("sin autenticación en la API") queda mitigado.

## 2. Esquema de base de datos

Tres tablas nuevas, aditivas (no tocan `creators`/`brands`/`tickets`):

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : posee
    USERS ||--o{ AUDIT_LOG : "genera (actor)"
    USERS |o--|| CREATORS : "vincula (solo rol creador)"

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role
        int creator_id FK "nullable, UNIQUE si no es null"
        bool is_active
        bool must_change_password
        int token_version
        int failed_login_attempts
        datetime locked_until
    }
    REFRESH_TOKENS {
        int id PK
        int user_id FK
        string token_hash UK
        datetime expires_at
        datetime revoked_at
        int replaced_by_id FK
    }
    AUDIT_LOG {
        int id PK
        int actor_user_id FK
        string action
        string target_type
        int target_id
    }
```

- `role` es un `String` validado por el enum Python `UserRole` (`app/models.py`), **sin** `CHECK` a nivel DB — agregar un rol nuevo no requiere migración, solo actualizar el enum y la matriz de permisos.
- `creator_id` tiene un índice único parcial (`WHERE creator_id IS NOT NULL`): un `Creator` tiene a lo sumo un usuario vinculado.
- Todas las fechas usadas en comparaciones (`RefreshToken.expires_at`, `User.locked_until`) se guardan y comparan como **UTC naive** (sin tzinfo) — SQLite no preserva tzinfo al leer de vuelta, así que mezclar aware/naive revienta con `TypeError`. Ver `app/security.py` (`refresh_token_expiry`) y `app/crud.py` (`is_locked`, `register_failed_login`).

## 3. Matriz de permisos

### 3.1 Cambios del paquete R1-R11 (R4-R6) — reemplazan lo descrito en `auth-diseno-fase1.md`

**R4 — Gestión de usuarios ahora es exclusiva de `superadmin`.** Antes, un `admin` podía gestionar usuarios `role=creador` (y su propia fila). Eso se eliminó: **todo** `/api/users/*` ahora exige `require_role("superadmin")` — un `admin` recibe `403` en cualquier endpoint de usuarios, y la pestaña "Usuarios" ni siquiera se renderiza para su rol en `AdminView.jsx`/`Sidebar.jsx`. La lógica de auto-desactivación con confirmación (`_ensure_can_manage_target`, "escribe tu usuario para confirmar") quedó **eliminada por completo** — era inalcanzable una vez que solo superadmin entra a esos endpoints y superadmin nunca puede apuntarse a sí mismo (`_ensure_not_superadmin_target` ya lo bloqueaba).

**R4.1 (2026-08-19) — Reset de contraseña entre superadmins.** El patrón "escribe el username para confirmar" vuelve, ahora alcanzable, para la única operación permitida sobre la cuenta superadmin: `POST /api/users/{id}/reset-password-superadmin` (solo `superadmin`, nunca sobre uno mismo, nunca cambia rol/estado). Genera contraseña temporal + `must_change_password`, revoca sesiones, desbloquea si estaba bloqueada, y audita con `action="password.reset_superadmin"`. La UI separa a los superadmins en su propia tabla ("Superadministradores") con botón dedicado y confirmación fuerte tecleando el username exacto. El script `backend/reset_superadmin_password.py` queda como emergencia sin otro superadmin disponible.

**R5 — El alcance del `admin` en TODO lo demás se mantiene/amplía**: dashboard global, creadores, marcas, transacciones de todos, administración de creadores/marcas, asignación de presupuestos por ciclo, validación de tickets, descarga del PDF. Solo pierde acceso a usuarios (R4).

**R6 — El alcance del `creador` se mantiene sin cambios de fondo**, pero ahora incluye más superficie a auditar: no ve el histórico de ciclos de otro creador (`GET /api/creators/{id}/ciclos` → 403 si `creator_id` no es el suyo), no ve la bandeja de Validación (ruta y endpoints `aprobar`/`rechazar` con `require_role("admin", "superadmin")`), y sus tickets propios siempre nacen `pendiente` (nunca auto-aprueban, a diferencia de los de admin/superadmin).

Endpoints nuevos de este paquete (matriz completa, ver `docs/presupuestos/presupuestos-y-validacion.md` para las reglas de negocio detrás):

| Endpoint | Rol requerido | Notas |
|---|---|---|
| `GET /api/creators/{id}/ciclos` | Cualquiera autenticado | `creador` solo el propio (403 si no), admin/superadmin cualquiera |
| `POST /api/tickets/{id}/aprobar` | `admin`, `superadmin` | 400 si el ticket no está `pendiente`; 404 si `is_deleted` |
| `POST /api/tickets/{id}/rechazar` | `admin`, `superadmin` | Body `{reason}` obligatorio (422 si falta); 400 si no está `pendiente`; 404 si `is_deleted` |
| `GET /api/tickets/?status=` | Cualquiera autenticado | Filtro adicional por estado, respeta el scoping de creador |
| `POST/PUT /api/brands/` con `priority` | `admin`, `superadmin` | 400 si `priority` no es `alta`/`media`/`baja` |

**Endpoints del paquete R12** (borrado de tickets y gastos generales, ver `docs/presupuestos/borrado-tickets.md` y `docs/presupuestos/gastos-generales-manual.md`):

| Endpoint | Rol requerido | Notas |
|---|---|---|
| `POST /api/tickets/{id}/soft-delete` | `admin`, `superadmin` | 404 si ya estaba `is_deleted`; revierte el ciclo si el ticket estaba `aprobado` |
| `DELETE /api/tickets/{id}/permanent` | `admin`, `superadmin` | Borra registro y archivo; revierte el ciclo solo si no se había revertido ya por un soft-delete previo |
| `GET /api/general-expenses/` | `admin`, `superadmin` | Filtros opcionales `start_date`/`end_date`; excluye `is_deleted` |
| `POST /api/general-expenses/` | `admin`, `superadmin` | Multipart: `amount`, `description`, `file` |
| `GET /api/general-expenses/{id}/file` | `admin`, `superadmin` | 404 si `is_deleted` |
| `GET /api/general-expenses/export` | `admin`, `superadmin` | Query `months` (lista separada por comas, ej. `2026-07,2026-08`); 400 si viene vacía |
| `POST /api/general-expenses/{id}/soft-delete` | `admin`, `superadmin` | Análogo a tickets, sin reversión de ciclo (no aplica) |
| `DELETE /api/general-expenses/{id}/permanent` | `admin`, `superadmin` | Análogo a tickets |
| `GET /api/dashboard/general-expenses-monthly` | `admin`, `superadmin` | Totales mensuales para la gráfica del Dashboard, excluye `is_deleted` |

### 3.2 Reglas heredadas de la Fase 1 de autenticación (sin cambios)

Verificadas por la suite de pruebas (`backend/tests/test_permissions.py`, `test_users_management.py`). Resumen de las reglas que más importan:

| Regla | Detalle |
|---|---|
| Un `creador` solo ve su propio `Creator`/tickets | Filtrado server-side en `routers/creators.py` y `routers/tickets.py`, ignora intentos de filtrar por otro nombre |
| `GET /api/tickets/file/{id}` | 403 si el ticket no es del creador autenticado — corrige el IDOR original (antes, cualquiera con el ID podía descargar cualquier comprobante) |
| `POST /api/tickets/` | 403 si un creador intenta crear el ticket a nombre de otro `creator_id` |
| `superadmin` | Único, inmutable por API: `POST /api/users/` nunca acepta `role=superadmin`; ningún endpoint permite cambiar su `role`/`is_active`. Excepción R4.1: su contraseña SÍ puede resetearla otro superadmin (`POST /api/users/{id}/reset-password-superadmin`, nunca sobre uno mismo) |
| `/uploads` (mount estático) | Eliminado; todo archivo se sirve por `GET /api/tickets/file/{id}` (autenticado) |
| `/docs`, `/redoc` | Deshabilitados si `ENV=production` |

## 4. Estrategia de tokens

- **Access token**: JWT (HS256), cookie `access_token`, `Path=/`, `httpOnly`, `SameSite=Lax`, `Secure` solo si `ENV=production`. Vida: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (15 por defecto). Claims: `sub`, `role`, `tv` (token_version), `exp`.
- **Refresh token**: opaco (`secrets.token_urlsafe(32)`), cookie `refresh_token`, `Path=/api/auth`, mismos flags. Vida: `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (7). Se guarda **hasheado** (SHA-256) en `refresh_tokens`, nunca en claro.
- **Por qué cookies y no `localStorage`**: un XSS no puede leer una cookie `httpOnly` directamente. El CSRF clásico queda mitigado por `SameSite=Lax` (no se envía en POST/PUT cross-site) + CORS restrictivo (`allow_origins` explícito), sin necesidad de un token CSRF adicional.
- **Revocación de access token**: en cada request, `get_current_user` compara el `tv` del JWT contra `User.token_version` en DB — un cambio de contraseña o una desactivación invalida el access token vigente en la siguiente request, sin esperar a que expire.
- **Rotación de refresh token**: cada `/api/auth/refresh` emite uno nuevo y marca el usado como `revoked_at` + `replaced_by_id`. Si un token ya revocado se vuelve a presentar (señal de robo/reuso), se revoca **toda la cadena** de refresh tokens del usuario, forzando login de nuevo. Verificado en `test_refresh_reuse_detected_revokes_chain`.
- **Rate limiting de login**: doble capa — (1) bloqueo incremental por cuenta (`User.failed_login_attempts`/`locked_until`, 5 intentos → bloqueo creciente hasta 60 min) y (2) límite de 30 intentos/15 min por IP en memoria (`app/security.py`, se reinicia si el proceso se reinicia — aceptable en un backend de proceso único sin `--workers`).

## 5. Decisiones y desviaciones respecto al diseño de Fase 1

Estas surgieron durante la implementación/verificación y **no** estaban en `auth-diseno-fase1.md`:

1. **`GET /api/users/` para un `admin` incluye su propia fila**, aunque su rol no sea `creador`. Necesario para que la regla "un admin puede autodesactivarse con confirmación" (ya prevista en el diseño §0.3) sea alcanzable desde la UI — si no, un admin nunca vería su propia fila en la tabla que gestiona. Ver `routers/users.py::list_users`.
2. **Dominios de correo para cuentas auto-generadas**: `email-validator` (usado por Pydantic `EmailStr`) rechaza TLDs de uso especial (`.local`, `.test`, `.example`, `.invalid`) por RFC 6761/2606. `seed_auth.py` genera `{usuario}@creadores.grupo-ortiz.com` en vez de `.local` — encontrado y corregido durante la verificación manual (causaba `500` en `GET /api/users/`).
3. **`/uploads` no solo se dejó de montar** — la entrada correspondiente en `frontend/vite.config.js` (proxy) también se eliminó, y el proxy de `/api` ahora lee el puerto de un env var opcional (`VITE_BACKEND_PORT`, default `8000`) para poder apuntar la suite E2E a un backend de pruebas sin editar el archivo committeado.

## 6. Limitaciones conocidas (fuera de alcance de esta fase)

- Un `GET /api/tickets/file/{id}` abierto en pestaña nueva (`target="_blank"`) no pasa por el interceptor de refresh de `api/index.js` — si el access token expiró justo en ese instante, el navegador muestra el JSON de error crudo en vez de refrescar la sesión. Con un access token de 15 min esto es infrecuente; se podría resolver a futuro sirviendo el archivo vía `fetch` + blob, a costa de perder la vista previa nativa del navegador para PDFs/imágenes.
- El límite de intentos de login por IP vive en memoria (no persiste ni se comparte entre procesos). Si el despliegue pasa a múltiples workers/instancias, habría que moverlo a algo compartido (Redis u otro almacén).
- El reset de contraseña por un admin/superadmin devuelve la contraseña temporal una sola vez en la respuesta HTTP — no hay integración de correo; quien resetea es responsable de comunicarla por un canal seguro. Aplica igual al reset entre superadmins (R4.1): la temporal del otro superadmin viaja en la respuesta del que ejecuta el reset, nunca en `audit_log` (el endpoint no tiene body y la respuesta no se audita).
- OWASP Top 10 — cobertura y lo que queda fuera:
  - **A01 Broken Access Control**: cubierto (matriz de permisos + pruebas de IDOR).
  - **A02 Cryptographic Failures**: contraseñas con argon2id; secretos por variable de entorno.
  - **A03 Injection**: SQLAlchemy ORM parametrizado en todo el código; sin SQL crudo.
  - **A04/A05 Diseño inseguro / Config de seguridad**: cookies `httpOnly`/`SameSite`, CORS restrictivo, `/docs` deshabilitado en producción.
  - **A07 Identification and Authentication Failures**: cubierto (bloqueo incremental, rotación de refresh, política de contraseñas).
  - **Fuera de alcance**: cabeceras de seguridad HTTP adicionales (CSP, HSTS, X-Frame-Options) — no se agregaron; recomendable antes de exponer fuera de `127.0.0.1`. Tampoco hay 2FA/MFA.

## 7. Cobertura de pruebas

- **Backend (pytest)**: `backend/tests/` — 688 pruebas. `test_auth.py` (login, bloqueo, rate limit, cambio de contraseña, refresh/rotación/reuso, logout), `test_permissions.py` (401 sin token, matriz por rol incluido R4-R6 y R12, IDOR de tickets/archivos/ciclos), `test_users_management.py` (R4: admin recibe 403 en todo `/api/users/*`, inmutabilidad de superadmin, reset entre superadmins R4.1 con temp+must_change+lockout+revocación+audit), `test_budget_cycles.py` (R7: ver `docs/presupuestos/presupuestos-y-validacion.md` §7), `test_ticket_validation.py` (R10, ídem), `test_brand_priority.py` (R9, ídem), `test_ticket_soft_delete.py` y `test_general_expenses.py` (R12: ver `docs/presupuestos/borrado-tickets.md` y `docs/presupuestos/gastos-generales-manual.md`). Ejecutar: `cd backend && python -m pytest`.
- **E2E (Playwright)**: archivos en `frontend/e2e/`:
  - `auth.spec.js` (7 pruebas): superadmin → crea admin → admin ve dashboard/creadores pero NO usuarios (403 en la API) → superadmin vincula el usuario `creador` → creador ve solo lo suyo → usuario desactivado no puede entrar.
  - `presupuesto-flujo-completo.spec.js` (9 pruebas): el flujo de negocio completo del paquete R1-R11 — bootstrap de admin/creador/marca, ticket pendiente sin descuento, validación con visor y rechazo motivado, re-subida y aprobación con descuento del ciclo, tema persistente, popover, PDF con contenido real, y el recorrido en 375px. Detalle de reglas en `docs/presupuestos/presupuestos-y-validacion.md` §7.
  - `gastos-generales.spec.js` (paquete R12): creación y borrado de gastos generales, exportación a PDF, acceso denegado para el rol `creador`, borrado lógico/físico de un ticket reflejado en Dashboard y Transacciones.
  - Todos requieren un backend + frontend dedicados a pruebas (ver `docs/presupuestos/auth/auth-manual-usuario.md` §Pruebas E2E). **Nota**: el rate limit de login (30/15min por IP, §4) puede alcanzarse si se corren varios archivos juntos en una sola invocación — se recomienda correrlos por separado (cada uno se mantiene bien por debajo del límite).
