# Prompt — Redefinición de roles y permisos RBAC

> **Para:** Agente especializado  
> **Fecha:** 2026-07-31  
> **Rama:** `dami-branch`  
> **Estado:** En progreso — el catálogo y backend ya se modificaron pero el rol `marketing_presupuestos` sigue recibiendo 403 en múltiples endpoints.

---

## Objetivo

Redefinir los roles y permisos del sistema para reflejar la estructura real del equipo de marketing. El rol `marketing_presupuestos` debe tener acceso **completo** al módulo de Presupuestos — sin restricciones — y cero acceso a Equipos.

---

## Contexto

### Roles actuales (ya implementados en `models.py`)

```python
class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"           # Todo
    ADMIN = "admin"                     # Presupuestos completo + Equipos completo + Aprobación
    CREADOR = "creador"                 # Solo sus propios tickets (aislado)
    MARKETING_PRESUPUESTOS = "marketing_presupuestos"  # Presupuestos completo, cero Equipos
    MARKETING_EQUIPOS = "marketing_equipos"            # Equipos completo, sin aprobación
    COLABORADOR_MKT = "colaborador_mkt" # Legacy — solo Equipos básico
    USUARIO = "usuario"                 # Sin permisos, solo piso
```

### Paquetes aditivos

| Paquete | Qué concede |
|---|---|
| `APROBADOR_EQUIPO` | `equipos_aprobacion:*` + `equipos_prestamos:ver_global` |
| `CUSTODIO_EQUIPO` | `equipos_inventario:crear,editar,auditar_condicion,dar_de_baja` + `equipos_prestamos:ver_global` |
| `AUDITOR` | Solo lecturas globales en ambos módulos |

### Usuarios en producción (seed_usuarios_mkt.py)

| Usuario | Rol |
|---|---|
| `integraciones.ia`, `josue.benitez`, `jose.aguilar` | `superadmin` |
| `melisa.avendano.zuniga` | `admin` |
| `sara.jion.mi.benito.reyes` | `marketing_presupuestos` |
| Los otros 11 | `colaborador_mkt` |

---

## Lo que YA está hecho (NO reimplementar — revisar por qué falla)

### 1. Catálogo RBAC (`backend/app/rbac_catalog.py`)

El paquete `admin` ya incluye Equipos completo:
```python
"admin": {
    "permisos": {
        "presupuestos": (todas las acciones),
        "equipos_inventario": ("ver","crear","editar","auditar_condicion","dar_de_baja"),
        "equipos_prestamos": ("solicitar","ver_propios","ver_global","registrar_devolucion","cancelar","exportar"),
        "equipos_aprobacion": ("autorizar_entrega","confirmar_devolucion","cerrar_incidencia"),
    },
},
```

El paquete `marketing_presupuestos` (nuevo) ya existe:
```python
"marketing_presupuestos": {
    "permisos": {
        "presupuestos": (todas las acciones: ver_global, ver_propio, subir_ticket,
                         validar_ticket, borrar_ticket, gestionar_ciclos,
                         gastos_generales, exportar),
    },
},
```

El paquete `marketing_equipos` (nuevo) ya existe:
```python
"marketing_equipos": {
    "permisos": {
        "equipos_inventario": ("ver","crear","editar","auditar_condicion","dar_de_baja"),
        "equipos_prestamos": ("solicitar","ver_propios","ver_global","registrar_devolucion","cancelar","exportar"),
    },
},
```

La migración RBAC (`migrate_rbac_aditivo.py`) YA se ejecutó — 11 paquetes, 90 permisos en base.

### 2. Backend routers — `require_role` actualizado

Se reemplazó `require_role("admin", "superadmin")` por `require_role("admin", "superadmin", "marketing_presupuestos")` en **todos** los routers de Presupuestos:

- `backend/app/routers/creators.py` — 3 ocurrencias
- `backend/app/routers/brands.py` — 2 ocurrencias
- `backend/app/routers/tickets.py` — 5 ocurrencias
- `backend/app/routers/dashboard.py` — 4 ocurrencias
- `backend/app/routers/general_expenses.py` — 6 ocurrencias

Total: 20 endpoints actualizados.

### 3. Frontend — Sidebar y rutas

- `Sidebar.jsx` — todos los items de Presupuestos incluyen `"marketing_presupuestos"` en `roles`
- `PresupuestosLayout.jsx` — `ADMIN_ROLES = ["admin", "superadmin", "marketing_presupuestos"]`

### 4. Mirrors JSON actualizados

- `docs/equipos/contratos/permisos_catalogo.json`
- `frontend/src/modules/equipos/api/mock/fixtures/permisos_catalogo.json`

### 5. Pruebas

- 102 pruebas RBAC pasan (`tests/rbac/`)
- 93 pruebas auth + permisos pasan
- 77 pruebas de permisos pasan

---

## El problema — 403 persisten

Al hacer login como `sara.jion.mi.benito.reyes` (`marketing_presupuestos`), el frontend carga pero múltiples endpoints devuelven 403:

```
GET /api/dashboard/summary → 403
GET /api/dashboard/monthly-spend → 403
GET /api/dashboard/creator-usage → 403
GET /api/dashboard/general-expenses-monthly → 403
GET /api/tickets/brand-spend → 403
GET /api/creators/kpi → 403
```

### Diagnóstico probable

El backend se reinició con `--reload` pero **las rutas de dashboard y creators/kpi pueden tener守卫 duplicados o el router no está refrescando correctamente**. Revisar:

1. **`backend/app/routers/dashboard.py`** — verificar que TODOS los endpoints tengan `require_role("admin", "superadmin", "marketing_presupuestos")`. Puede haber endpoints con `require_role` diferente (ej. `require_role("superadmin")` para alguna ruta de admin) o decoradores que no se actualizaron.

2. **`backend/app/routers/creators.py`** — verificar `GET /api/creators/kpi` específicamente. Puede tener un guard distinto o estar en otro archivo.

3. **Frontend: `PresupuestosLayout.jsx`** — `loadData()` se llama al montar el layout y dispara todas estas llamadas. Si el token JWT se emitió antes del cambio de rol, el claim `role` en el JWT podría seguir diciendo `colaborador_mkt` (el rol anterior de Sara). **Solución: cerrar sesión y volver a hacer login** para obtener un JWT fresco con el nuevo rol.

4. **`backend/app/routers/tickets.py`** — `GET /api/tickets/brand-spend` en línea 72. Verificar que tenga el guard actualizado.

---

## Lo que hay que hacer

### Paso 1 — Auditar cada endpoint que devuelve 403

Buscar en `backend/app/routers/` TODOS los endpoints accedidos desde el Dashboard y la vista de Presupuestos que usen `require_role` o `require_perm`. Para cada uno, verificar que `marketing_presupuestos` esté en la lista de roles permitidos.

Endpoints críticos a revisar:
- `GET /api/dashboard/summary`
- `GET /api/dashboard/monthly-spend`
- `GET /api/dashboard/creator-usage`
- `GET /api/dashboard/general-expenses-monthly`
- `GET /api/creators/kpi`
- `GET /api/tickets/brand-spend`
- `GET /api/creators/`
- `GET /api/brands/`
- `GET /api/tickets/`
- `POST /api/tickets/`
- `GET /api/general-expenses/`

### Paso 2 — Verificar que el JWT tenga el rol correcto

Cuando un usuario cambia de rol, los tokens JWT emitidos **antes** del cambio siguen teniendo el rol viejo en el claim `role`. Aunque esto no debería afectar los guards del backend (porque `get_current_user` lee el rol de la BD, no del JWT), vale la pena verificarlo.

Revisar `backend/app/dependencies.py` — `get_current_user`:
```python
user = crud.get_user(db, int(payload["sub"]))
```
Esto obtiene el usuario fresco de la BD, así que el rol debería ser el actual. Pero si hay algún endpoint que use `payload["role"]` en vez de `user.role`, daría 403.

### Paso 3 — Verificar guards en `tickets.py` para el endpoint de archivos

`GET /api/tickets/file/{ticket_id}` se arregló antes (solo superadmin, admin, creador). ¿Debería `marketing_presupuestos` poder descargar comprobantes? **Sí** — un admin de presupuestos debe poder ver los comprobantes de cualquier ticket. Agregar `"marketing_presupuestos"` a la lista de roles permitidos en ese endpoint.

### Paso 4 — Probar con pytest

Crear una prueba que:
1. Cree un usuario `marketing_presupuestos`
2. Haga login
3. Llame a cada endpoint del dashboard
4. Verifique que todos devuelvan 200

```python
def test_marketing_presupuestos_accede_a_todo_presupuestos(db, catalogo):
    user = make_user(db, username="test.mp", password="test", role="marketing_presupuestos")
    client = login("test.mp", "test")
    
    assert client.get("/api/dashboard/summary").status_code == 200
    assert client.get("/api/dashboard/monthly-spend").status_code == 200
    assert client.get("/api/creators/kpi").status_code == 200
    assert client.get("/api/tickets/brand-spend").status_code == 200
    # ... etc
```

### Paso 5 — Revisar el frontend

En `PresupuestosLayout.jsx`, la función `loadData()` llama a `fetchCreatorsKpi()` y varios endpoints del dashboard. Verificar que:
- `ADMIN_ROLES` incluya `marketing_presupuestos` ✅ (ya hecho)
- `isPrivileged` se calcule correctamente
- El botón "Nuevo Ticket" sea visible para `marketing_presupuestos`

---

## Reglas importantes

- **NO tocar los endpoints de `/api/users/*`** — siguen siendo exclusivos de `superadmin`
- **NO tocar los endpoints de `/api/audit-logs/*`** — exclusivos de `superadmin`
- **NO tocar los routers de Equipos** — `marketing_presupuestos` NO debe tener acceso a nada de Equipos
- **NO modificar el catálogo RBAC** — ya está correcto
- **NO modificar los modelos** — ya están correctos
- **Toda prueba nueva debe seguir el patrón de `backend/tests/`**: DB aislada, fixtures `db`, `catalogo`, helpers `make_user`, `login`

---

## Orden recomendado

1. Auditar cada endpoint listado arriba — `grep` en `backend/app/routers/` por `require_role` y `require_perm`
2. Corregir los que falten
3. Crear la prueba `test_marketing_presupuestos_accede_a_todo_presupuestos`
4. Correr `python -m pytest tests/ -q` y verificar que todo pase
5. Probar en el navegador con Sara (`sara.jion.mi.benito.reyes` / `Marketing2026!`)
