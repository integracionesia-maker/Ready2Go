# Prompt: Overhaul de usuarios, roles y permisos — RBAC granular

> **Rama objetivo**: `dami-branch`
> **Fecha**: 2026-07-30
> **Para**: Agente especializado de código (full-stack FastAPI + React)
> **Tiempo estimado**: 8-12 horas de implementación + 2-4 horas de testing

---

## Resumen ejecutivo

El sistema actual tiene 4 roles base (`superadmin`, `admin`, `creador`, `colaborador_mkt`) + 3 paquetes aditivos (`APROBADOR_EQUIPO`, `CUSTODIO_EQUIPO`, `AUDITOR`). El RBAC aditivo (patrón Bruckner) YA existe en el backend — el problema es que la UI de administración de usuarios/roles es pobre, no hay un rol "empleado general", y los permisos granulares no son visibles ni asignables fuera del `superadmin` vía código.

Hay que:

1. **Crear un nuevo rol base** para empleados generales (sin acceso por defecto a nada, solo piso `inicio:ver` + `perfil:ver/editar_propio`)
2. **Crear la UI de administración de RBAC** — una vista nueva exclusiva de `superadmin` que permita ver, crear, editar usuarios y asignar/remover paquetes aditivos por usuario
3. **Mover la gestión de usuarios fuera de Presupuestos/Administración** — el `admin` no puede ver ni tocar usuarios; el `superadmin` accede desde un nuevo botón en el menú de perfil del Header
4. **Auditar y actualizar el catálogo** de permisos para que cubra todas las acciones existentes en ambos módulos
5. **Testing**: toda migración de datos, endpoints nuevos y modificados, y flujos de UI deben tener pruebas

---

## FASE 0 — Auditoría del estado actual

### 0.1 Lo que YA existe (no reinventar)

#### Backend

| Archivo | Función |
|---------|---------|
| `backend/app/rbac_catalog.py` | Catálogo de 7 módulos, 8 paquetes (1 piso, 4 base, 3 aditivo). Fuente de verdad de permisos. |
| `backend/app/rbac.py` | Motor: `permisos_del_request()` resuelve permisos efectivos = piso + base + aditivos. |
| `backend/app/models_rbac.py` | Tablas: `roles` (catálogo), `role_permissions` (módulo+acción por paquete), `user_role_grants` (concesiones por usuario) |
| `backend/app/models.py` | `UserRole` enum: `SUPERADMIN`, `ADMIN`, `CREADOR`, `COLABORADOR_MKT`. Tabla `users` con campo `role`. |
| `backend/app/routers/roles.py` | `GET /api/roles/` — lista el catálogo. **Solo lectura.** |
| `backend/app/routers/user_roles.py` | `GET /api/user-roles/{user_id}` y `PUT /api/user-roles/{user_id}` — consulta y actualiza concesiones aditivas de un usuario. Protegido con `require_role(["superadmin"])`. |
| `backend/app/routers/auth.py:99` | Login NO retorna permisos. Solo `/auth/me` (línea 174) los resuelve. |
| `backend/migrate_rbac_aditivo.py` | Siembra/reconcilia `roles` y `role_permissions` desde el catálogo. |
| `backend/seed_rbac.py` | Concede paquetes aditivos de demo a usuarios existentes. |
| `backend/seed_auth.py` | Crea el `superadmin` inicial si no existe. |

#### Frontend

| Archivo | Función |
|---------|---------|
| `frontend/src/modules/presupuestos/components/AdminView.jsx` | Tabs: Creadores, Marcas, Usuarios (este último solo visible si `user.role === "superadmin"`, línea 542). |
| `frontend/src/modules/presupuestos/components/UserManagement.jsx` | CRUD de usuarios: crear admin/creador, editar, activar/desactivar, resetear contraseña. Solo accesible vía AdminView. |
| `frontend/src/modules/presupuestos/components/ProfilePopover.jsx` | Dropdown con 2 items: "Mi perfil" y "Cerrar sesión". **No tiene link de administración.** |
| `frontend/src/modules/equipos/permisos/usePermisos.js` | Hook `usePermisos()` — lee `user.permisos` de AuthContext, expone `puede(modulo, accion)`. |
| `frontend/src/modules/equipos/permisos/RequierePermiso.jsx` | Componente gate: oculta hijos si `puede(modulo, accion)` es false. |
| `frontend/src/modules/equipos/permisos/catalogo.js` | Espejo frontend del catálogo. Lo usa `usePermisos` para validar que (modulo, accion) existe. |

### 0.2 Lo que FALTA

| Brecha | Detalle |
|--------|---------|
| Nuevo rol base `usuario` | No existe en `UserRole` enum ni en `rbac_catalog.py`. Debe ser un empleado genérico sin acceso a ningún módulo excepto piso. |
| UI de administración RBAC | `UserManagement.jsx` solo maneja `admin` y `creador`. No muestra paquetes aditivos. No tiene vista de permisos por rol. |
| Acceso a UserManagement | Está enterrado en AdminView → tab Usuarios. El `admin` ni lo ve (bien), pero el `superadmin` no tiene un acceso directo desde el Header. |
| Botón en ProfilePopover | Solo tiene "Mi perfil" y "Cerrar sesión". Falta "Administración" para superadmin. |
| Catálogo de permisos incompleto | El módulo `usuarios` (`gestionar`, `gestionar_roles`) existe pero ningún paquete lo concede explícitamente (solo superadmin vía `*`). |
| Usuario `colaborador_mkt` sin permisos de presupuestos | Correcto por diseño, pero no hay un equivalente inverso (usuario de presupuestos sin acceso a equipos). |

---

## FASE 1 — Backend: nuevo rol base `usuario`

### 1.1 Agregar `USUARIO` al enum `UserRole`

**Archivo**: `backend/app/models.py`, clase `UserRole` (línea 14-23)

```python
class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    CREADOR = "creador"
    COLABORADOR_MKT = "colaborador_mkt"
    USUARIO = "usuario"                    # ← NUEVO
```

### 1.2 Agregar paquete base `usuario` al catálogo

**Archivo**: `backend/app/rbac_catalog.py`, constante `PAQUETES` (después de línea 111)

```python
"usuario": {
    "kind": KIND_BASE,
    "descripcion": "Empleado general. Acceso mínimo: solo inicio y perfil propio. "
                   "Los permisos a módulos se conceden vía paquetes aditivos.",
    "permisos": {
        # Solo piso — sin acceso a presupuestos ni equipos por defecto.
        # Los módulos se abren con paquetes aditivos.
    },
},
```

> ⚠️ **Importante**: Este paquete base NO incluye `presupuestos:ver_propio` ni `equipos_inventario:ver`. Un `usuario` puro solo puede ver Inicio y su Perfil. Para acceder a cualquier módulo, necesita paquetes aditivos. Esto es diferente de `creador` y `colaborador_mkt` que sí tienen permisos base.

### 1.3 Actualizar `ROLE_OPTIONS` en frontend

**Archivo**: `frontend/src/modules/presupuestos/components/UserManagement.jsx` (línea 15-18)

Agregar `{ value: "usuario", label: "Usuario" }` a `ROLE_OPTIONS`.

### 1.4 Actualizar `ROLE_LABELS`

Todos los lugares donde `ROLE_LABELS` está hardcodeado deben incluir el nuevo rol:
- `frontend/src/modules/presupuestos/components/UserManagement.jsx` (línea 9-13)
- `frontend/src/modules/presupuestos/components/ProfilePopover.jsx` (línea 5-9)

```javascript
const ROLE_LABELS = {
  superadmin: "Superadministrador",
  admin: "Administrador",
  creador: "Creador",
  colaborador_mkt: "Marketing",
  usuario: "Usuario",
};
```

### 1.5 Verificar migración

**Archivo**: `backend/migrate_rbac_aditivo.py`

Confirmar que `migrate_rbac_aditivo.py` siembra automáticamente el nuevo paquete `usuario` desde el catálogo. Si usa `rbac_catalog.PAQUETES` para iterar, ya lo hará. Si tiene una lista hardcodeada, agregar `usuario`.

---

## FASE 2 — Backend: endpoints de administración RBAC

### 2.1 Auditoría de endpoints de roles existentes

**Archivo**: `backend/app/routers/user_roles.py` (comparte prefijo `/api/users` con `users.py`)

Estos endpoints YA existen. Verificar que:

- [ ] `GET /api/users/{user_id}/roles` → devuelve `UserRolesResponse` con `role_base`, `aditivos[]` (lista de `GrantResponse`), y `permisos_efectivos`
- [ ] `POST /api/users/{user_id}/roles` → concede UN paquete aditivo. Body: `{ "role_name": "APROBADOR_EQUIPO" }`. Idempotente. Valida que sea kind=aditivo, que esté sembrado en DB, y que el target no sea superadmin.
- [ ] `DELETE /api/users/{user_id}/roles/{role_name}` → revoca un aditivo. 404 si no lo tenía.
- [ ] Todos requieren `usuarios:gestionar_roles` (actualmente usan `require_role("superadmin")`, migrar a `require_perm`).

### 2.2 Nuevo endpoint (opcional, si no existe): `GET /api/users/{id}/permisos`

Devuelve los permisos efectivos de cualquier usuario (para que el admin pueda previsualizar qué permisos tendrá un usuario antes de asignar paquetes).

```python
@router.get("/{user_id}/permisos", response_model=dict)
def ver_permisos_de_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validar: current_user debe tener usuarios:gestionar o ser superadmin
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "Usuario no encontrado")
    return rbac_catalog.a_json(permisos_del_usuario(db, target))
```

### 2.3 Endpoints de usuarios existentes: verificar permisos

**Archivo**: `backend/app/routers/users.py` (o donde estén `createUser`, `updateUser`, etc.)

- [ ] `GET /api/users/` — solo `usuarios:gestionar` o `superadmin`
- [ ] `POST /api/users/` — solo `usuarios:gestionar` o `superadmin`
- [ ] `PUT /api/users/{id}` — solo `usuarios:gestionar` o `superadmin`
- [ ] `PUT /api/users/{id}/active` — solo `usuarios:gestionar` o `superadmin`
- [ ] `POST /api/users/{id}/reset-password` — solo `usuarios:gestionar` o `superadmin`

Actualmente estos endpoints usan `require_role(["superadmin"])`. Deben migrarse a permisos RBAC: exigir `usuarios:gestionar` (que el `superadmin` tiene vía `*`).

---

## FASE 3 — Frontend: nueva vista de Administración (superadmin only)

### 3.1 Nueva ruta: `/administracion-sistema`

**No usar `/administracion`** — esa ruta ya existe en Presupuestos para Creadores/Marcas (AdminView).

Crear nueva página y ruta:

```
/administracion-sistema → SystemAdminPage (solo superadmin)
```

### 3.2 Componente: `SystemAdminPage.jsx`

**Ubicación**: `frontend/src/modules/presupuestos/pages/SystemAdminPage.jsx`

Estructura de tabs:

| Tab | Contenido | Descripción |
|-----|-----------|-------------|
| **Usuarios** | `UserManagement` (reescrito) | Lista, crea, edita, activa/desactiva usuarios. Ahora incluye TODOS los roles base. |
| **Roles y Permisos** | `RoleManagement` (NUEVO) | Vista de catálogo de paquetes (base + aditivos), permisos que abre cada uno, usuarios que lo tienen. Solo lectura (los paquetes se siembran del catálogo). |
| **Asignaciones** | `UserRoleAssignment` (NUEVO) | Seleccionar usuario → ver paquetes actuales → agregar/quitar paquetes aditivos. Vista previa de permisos efectivos resultantes. |

### 3.3 Reescribir `UserManagement.jsx`

Cambios necesarios:

1. **Agregar columna de paquetes aditivos**: Mostrar badges con los paquetes aditivos que cada usuario tiene concedidos.
2. **Incluir todos los roles base** en el selector (agregar `colaborador_mkt` y `usuario`).
3. **Eliminar vinculación `creator_id`** para roles no-creador (actualmente el formulario muestra el selector de creador solo si `role === "creador"`, eso está bien).
4. **Validar**: el `superadmin` no puede editar su propio rol ni desactivarse a sí mismo (ya existe la protección `isTargetSuperadmin`, verificar).
5. **Agregar columna "Último acceso"** (ya existe, está bien).

### 3.4 Nuevo componente: `RoleManagement.jsx`

**Ubicación**: `frontend/src/modules/presupuestos/components/RoleManagement.jsx`

Vista de solo lectura del catálogo:

```
┌──────────────────────────────────────────────────┐
│ Catálogo de Roles y Permisos                     │
├──────────────────────────────────────────────────┤
│ [Base] superadmin — Acceso total                 │
│   Todos los módulos (*)                          │
│ [Base] admin — Presupuestos completo             │
│   presupuestos: ver_global, subir_ticket, ...    │
│   equipos_inventario: ver                        │
│   equipos_prestamos: solicitar, ver_propios, ... │
│ [Base] creador — Solo sus tickets                │
│   presupuestos: ver_propio, subir_ticket         │
│ [Base] colaborador_mkt — Solo equipos            │
│   equipos_inventario: ver                        │
│   equipos_prestamos: solicitar, ver_propios, ... │
│ [Base] usuario — Solo inicio y perfil            │
│   inicio: ver                                    │
│   perfil: ver, editar_propio                     │
│ [Aditivo] APROBADOR_EQUIPO — ...                 │
│ [Aditivo] CUSTODIO_EQUIPO — ...                  │
│ [Aditivo] AUDITOR — ...                          │
└──────────────────────────────────────────────────┘
```

Datasource: `GET /api/roles/` (ya existe). Los permisos de cada paquete se obtienen del catálogo (puede venir en la respuesta de `/api/roles/` o consultarse del frontend).

### 3.5 Nuevo componente: `UserRoleAssignment.jsx`

**Ubicación**: `frontend/src/modules/presupuestos/components/UserRoleAssignment.jsx`

```
┌──────────────────────────────────────────────────┐
│ [Selector de usuario]  ▼                         │
├──────────────────────────────────────────────────┤
│ Paquetes actuales:                               │
│   [admin ×]  [APROBADOR_EQUIPO ×]                │
├──────────────────────────────────────────────────┤
│ Agregar paquete: [Selector de paquetes ▼] [Agregar] │
├──────────────────────────────────────────────────┤
│ Permisos efectivos resultantes:                  │
│   presupuestos: ver_global, ver_propio, ...      │
│   equipos_inventario: ver, crear, editar, ...    │
│   equipos_prestamos: solicitar, ver_propios, ... │
│   equipos_aprobacion: autorizar_entrega, ...     │
└──────────────────────────────────────────────────┘
```

Datasource:
- `GET /api/users/{user_id}/roles` → paquetes actuales + permisos efectivos
- `GET /api/roles/` → catálogo de paquetes disponibles para agregar
- `POST /api/users/{user_id}/roles` → conceder un aditivo
- `DELETE /api/users/{user_id}/roles/{role_name}` → revocar un aditivo
- La previsualización de permisos efectivos ya viene en la respuesta de `GET .../roles`.

### 3.6 Ruta en `PresupuestosLayout`

Agregar la nueva ruta en el `<Routes>` interno de `PresupuestosLayout.jsx`:

```jsx
<Route
  path="/administracion-sistema"
  element={
    <ProtectedRoute roles={["superadmin"]}>
      <SystemAdminPage />
    </ProtectedRoute>
  }
/>
```

### 3.7 Botón en `ProfilePopover`

**Archivo**: `frontend/src/modules/presupuestos/components/ProfilePopover.jsx`

Agregar un tercer `<button role="menuitem">` entre "Mi perfil" y "Cerrar sesión", visible solo si `user.role === "superadmin"`:

```jsx
{user.role === "superadmin" && (
  <button
    role="menuitem"
    onClick={() => navigate("/administracion-sistema")}
    className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
    style={{ color: "var(--go-text-primary)" }}
  >
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
    Administración
  </button>
)}
```

---

## FASE 4 — Remover UserManagement del AdminView

### 4.1 AdminView: eliminar tab "Usuarios"

**Archivo**: `frontend/src/modules/presupuestos/components/AdminView.jsx`

- Línea 31: eliminar `{ key: "users", label: "Usuarios", roles: ["superadmin"] }` de `SECTIONS`
- Línea 542: eliminar `{section === "users" && user.role === "superadmin" && <UserManagement creators={creators} />}`
- Línea 6: eliminar `import UserManagement from "./UserManagement"` (si ya no se usa en otro lado)

### 4.2 AdminView: verificaciones

- [ ] El admin sigue viendo solo 2 tabs: Creadores y Marcas
- [ ] El superadmin ve lo mismo que el admin en AdminView (la gestión de usuarios se fue a `/administracion-sistema`)
- [ ] Eliminar cualquier referencia a `UserManagement` en AdminView

---

## FASE 5 — Catálogo de permisos: auditoría y actualización

### 5.1 Revisar acciones existentes

El catálogo actual (`rbac_catalog.py`) tiene estas acciones por módulo. Verificar que cubran TODAS las operaciones reales del código:

| Módulo | Acciones actuales | ¿Falta algo? |
|--------|-------------------|--------------|
| `inicio` | `ver` | Suficiente |
| `perfil` | `ver`, `editar_propio` | Suficiente |
| `presupuestos` | `ver_global`, `ver_propio`, `subir_ticket`, `validar_ticket`, `borrar_ticket`, `gestionar_ciclos`, `gastos_generales`, `exportar` | ¿`editar_ticket`? ¿`aprobar_rechazar`? |
| `equipos_inventario` | `ver`, `crear`, `editar`, `auditar_condicion`, `dar_de_baja` | ¿`exportar`? |
| `equipos_prestamos` | `solicitar`, `ver_propios`, `ver_global`, `registrar_devolucion`, `cancelar`, `exportar` | ¿`editar_borrador`? |
| `equipos_aprobacion` | `autorizar_entrega`, `confirmar_devolucion`, `cerrar_incidencia` | Suficiente |
| `usuarios` | `gestionar`, `gestionar_roles` | Bien — pero necesitan ser concedidos explícitamente en algún paquete |

### 5.2 Conceder `usuarios:gestionar` y `usuarios:gestionar_roles`

Actualmente ningún paquete los concede explícitamente. Solo `superadmin` los tiene vía comodín `*`.

**Decisión**: El `superadmin` es el único que gestiona usuarios y roles. Como ya tiene `*`, estos permisos ya los tiene. Pero debe documentarse que `usuarios:gestionar` y `usuarios:gestionar_roles` son poderes exclusivos del `superadmin` y ningún paquete aditivo los concede.

### 5.3 Verificar consistencia del catálogo

Correr `rbac_catalog.validar_catalogo()` — ya existe (línea 224-242 de `rbac_catalog.py`). La migración lo llama antes de sembrar. Debe devolver lista vacía después de los cambios.

---

## FASE 6 — Testing

### 6.1 Backend tests existentes

Verificar que TODOS los tests existentes sigan en verde:
- `cd backend && python -m pytest` (167+ pruebas)
- `backend/tests/rbac/` — tests específicos de RBAC
- `backend/tests/equipos/` — tests de equipos

### 6.2 Nuevos tests backend

| Test | Archivo | Descripción |
|------|---------|-------------|
| `test_usuario_role_creation` | `tests/rbac/` | Crear un usuario con rol `usuario` y verificar que solo tiene permisos de piso |
| `test_usuario_no_acceso_presupuestos` | `tests/rbac/` | Un `usuario` sin aditivos recibe 403 en endpoints de presupuestos |
| `test_usuario_no_acceso_equipos` | `tests/rbac/` | Un `usuario` sin aditivos recibe 403 en endpoints de equipos |
| `test_aditivo_abre_equipos_a_usuario` | `tests/rbac/` | Conceder `APROBADOR_EQUIPO` a un `usuario` y verificar que ahora accede a equipos/aprobacion pero no a presupuestos |
| `test_admin_no_gestiona_usuarios` | `tests/rbac/` | Un `admin` recibe 403 en `/api/users/*` y `/api/user-roles/*` |
| `test_superadmin_gestiona_usuarios` | `tests/rbac/` | El `superadmin` sí accede a todo `/api/users/*` y `/api/user-roles/*` |

### 6.3 E2E tests

| Test | Archivo | Descripción |
|------|---------|-------------|
| Login como superadmin → ver "Administración" en menú perfil | `frontend/e2e/auth.spec.js` | Navegar a perfil, verificar que existe el botón |
| Login como admin → NO ver "Administración" | `frontend/e2e/auth.spec.js` | Verificar que no aparece para admin |
| Flujo: crear usuario "usuario" + asignar aditivos | Nuevo spec | Crear usuario, ir a SystemAdmin → asignar paquete, verificar permisos efectivos |

---

## FASE 7 — Notas y restricciones

### 7.1 Lo que NO se debe hacer

- ❌ **NO eliminar el sistema de roles base (`user.role`)**. El RBAC aditivo se suma al rol base, no lo reemplaza.
- ❌ **NO permitir que un `admin` gestione usuarios**. El `admin` ya perdió ese poder en R4 — mantenerlo.
- ❌ **NO modificar el motor de RBAC** (`rbac.py`) a menos que sea estrictamente necesario. El patrón Bruckner funciona.
- ❌ **NO tocar la tabla `users` para agregar columnas**. Los paquetes aditivos viven en `user_role_grants`.
- ❌ **NO cambiar la semántica de `permisos: {}` en login**. El diseño actual es correcto: login no resuelve RBAC (caro), solo `/auth/me` lo hace. Corregir el frontend si hace falta (ver B1 en `docs/asignaciones/beni-bugs-post-unificacion.md`).

### 7.2 Convenciones

- **Commits atómicos**: un commit por fase, con mensaje descriptivo.
- **Rutas explícitas en `git add`**: nunca `-A` ni `.`.
- **Pruebas antes de commit**: `python -m pytest` debe estar en verde.
- **Documentación**: cada cambio significativo debe reflejarse en los archivos de `docs/`.

### 7.3 Archivos de referencia

| Archivo | Usar para |
|---------|-----------|
| `docs/equipos/plan-quirurgico.md` | Contexto del RBAC aditivo (§3, §10.6) |
| `docs/equipos/rbac-aditivo.md` | Diseño detallado del sistema RBAC |
| `docs/equipos/contratos/permisos_catalogo.json` | Espejo JSON del catálogo (congelado) |
| `docs/presupuestos/auth/auth-arquitectura.md` | Matriz de permisos actual |
| `docs/asignaciones/beni-bugs-post-unificacion.md` | Bug B1 relacionado (sidebar vacío por permisos) |
