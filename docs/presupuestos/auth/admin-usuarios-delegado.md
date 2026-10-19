# Paquete ADMIN_USUARIOS — administración delegada de cuentas

> Conexiones: [[CLAUDE]] | [[docs/presupuestos/auth/auth-arquitectura]] | [[docs/equipos/rbac-aditivo]] | [[docs/equipos/firma-pendiente-al-confirmar]]

Antes, la única forma de que alguien más diera de alta usuarios, cambiara roles o reseteara contraseñas era darle `superadmin` (acceso total, incluida Auditoría). `ADMIN_USUARIOS` delega **solo esa parte** a un `admin`, sin darle superadmin. Se concede en Administración del Sistema → Asignaciones (solo superadmin), como cualquier aditivo.

## Qué abre

Dos acciones nuevas del módulo `usuarios` (catálogo en `rbac_catalog.py`, espejo en `docs/equipos/contratos/permisos_catalogo.json`):

| Acción | Para qué |
|---|---|
| `usuarios:administrar_cuentas` | `/api/users/*`: listar, ver, crear, editar (nombre, correo, rol), activar/desactivar, desbloquear y resetear contraseña |
| `usuarios:ver_roles` | Solo lectura: `GET /api/roles/` (catálogo) y `GET /api/users/{id}/roles` (paquetes de un usuario) |

**No** reutiliza `usuarios:gestionar` porque esa acción también guarda Empresas y Notificaciones (`empresas.py`, `notifications.py`). Esos módulos, Auditoría y las cuentas superadmin siguen siendo solo de superadmin.

## Quién puede tenerlo

- Solo usuarios con **rol base `admin`** (`roles_base_permitidos` en el catálogo). Dos capas:
  1. `POST /api/users/{id}/roles` rechaza (400) conceder el paquete a otro rol.
  2. `rbac._aditivos_concedidos` ignora una concesión de un usuario que ya no es `admin` (fila vieja o puesta a mano en la base).
- Cambiar a un admin a otro rol (`PUT /api/users/{id}`, hecho por superadmin) **revoca** el paquete; si vuelve a ser admin no revive solo.
- Solo un superadmin lo concede o revoca (`usuarios:gestionar_roles`).

## Límites del delegado (los impone el backend, `routers/users.py`)

El delegado opera solo sobre cuentas **por debajo de admin**. Resetear la contraseña o cambiar el rol de un admin equivale a tomar su cuenta y sus paquetes.

- No ve ni toca cuentas **superadmin** (no salen en el listado, `GET /{id}` y `/{id}/roles` dan 404, `reset-password-superadmin` sigue exigiendo `gestionar`).
- No toca cuentas **admin** (otros admins ni la suya propia): editar, resetear, desbloquear y activar/desactivar dan 403.
- **No crea ni promueve a nadie a `admin`** (403).
- No toca al **titular de la firma de Equipos** (`TITULAR_FIRMA_EQUIPO`): es una identidad que ningún permiso cubre; resetearle la contraseña sería firmar como el aprobador.
- **No concede ni revoca paquetes** (solo los ve): así nadie se da `APROBADOR_EQUIPO` a sí mismo ni se reparte el propio `ADMIN_USUARIOS`.
- Todo queda en la bitácora igual que si lo hiciera un superadmin (el actor es el delegado).

Lo que sí hace: ve usuarios, los crea (cualquier rol salvo admin/superadmin), cambia nombre/correo/rol, activa/desactiva, desbloquea, resetea contraseñas, y ve el catálogo de roles y los paquetes de cada usuario. La regla *creador ⇔ perfil de creador* (`auth-arquitectura.md` §4.2) aplica igual.

## UI

El menú de perfil muestra "Administración" a quien tenga `usuarios:administrar_cuentas` (`puedeAdministrarUsuarios` en `frontend/src/modules/presupuestos/roles.js`). El delegado ve las pestañas **Usuarios** y **Roles y Permisos** (sin **Asignaciones**), sin la tabla de superadministradores, sin acciones en filas de admin y sin la opción "Administrador" en el selector de rol. La UI solo pinta; cada endpoint valida por su cuenta.

## Puesta en marcha

El paquete es una fila nueva en la tabla `roles` (la FK de `user_role_grants` apunta ahí): hay que correr una vez `python migrate_rbac_aditivo.py` desde `backend/` en cada entorno (idempotente; reconcilia la base con el catálogo). Sin eso, Asignaciones responde "El paquete 'ADMIN_USUARIOS' no está sembrado".

## Pruebas

`backend/tests/test_admin_usuarios_delegado.py` (32 casos: catálogo, quién puede tenerlo, lo que puede y lo que no, y que Auditoría/Empresas/Notificaciones siguen cerradas).
