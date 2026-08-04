# RBAC aditivo (patron Bruckner) — GOCreate

> Modulo Control de Equipos, paquete WP1/S1. Diseño original: `docs/equipos/plan-quirurgico.md` §3.
> Contrato de la respuesta: `docs/contratos/API_EQUIPOS_v1.md` §1 y §7, `docs/contratos/permisos_catalogo.json`.
> Sistema viejo (roles fijos, `require_role`): `docs/presupuestos/auth/auth-arquitectura.md`. Sigue vigente y funcionando.

## Que problema resuelve

Melisa aprueba prestamos de equipo, pero puede o no administrar presupuestos.
Emily pide equipo y ademas podria custodiar el inventario. Con un solo rol por
usuario, cada combinacion obliga a inventar un rol nuevo, y a los seis meses hay
once roles que nadie sabe explicar.

Solucion: **rol base + paquetes aditivos**. Los permisos efectivos son la union.

```
permisos_efectivos(user) = _PISO  ∪  paquete[users.role]  ∪  paquete[cada aditivo concedido]
```

## Las tres reglas duras

1. **Deny-by-default.** Un `(modulo, accion)` que no aparece en ningun paquete
   del usuario no esta concedido. No hay herencia ni comodines, salvo el bypass
   de `superadmin`.
2. **Un aditivo solo abre lo que lista.** Jamas sustituye ni amplia el rol base
   en otro modulo. `APROBADOR_EQUIPO` no concede un solo permiso de
   presupuestos, y hay una prueba que lo afirma por enumeracion
   (`tests/rbac/test_permisos_efectivos.py`).
3. **Fallo al resolver = 503, nunca `{}`.** Ver abajo.

## Por que 503 y no 403

Si la base falla y el motor devuelve un diccionario vacio, cada endpoint
contesta 403. El cliente lee 403 como *decision de politica*: esconde la
interfaz o desloguea. Nadie se entera de que lo que fallo fue la base.

Por eso `rbac.permisos_efectivos()` levanta `PermisosNoDisponibles` y el sobre
de error sale con `503` y `codigo: PERMISOS_NO_DISPONIBLES`. El contrato §0 dice
explicito: **jamas se interpreta como sesion invalida, no desloguear.**

Falta de cookie sigue siendo 401. Falta de permiso sigue siendo 403. Los tres
casos son distinguibles por el cliente sin adivinar.

## Donde vive cada cosa

| Pieza | Archivo | Rol |
|---|---|---|
| Catalogo de modulos, acciones y paquetes | `backend/app/rbac_catalog.py` | **Fuente de verdad del contenido** |
| Tablas `roles`, `role_permissions`, `user_role_grants` | `backend/app/models_rbac.py` | Materializacion + concesiones |
| Motor | `backend/app/rbac.py` | `permisos_efectivos`, `require_perm`, `require_cualquiera` |
| Acceso a datos | `backend/app/crud_rbac.py` | Siembra, concede, revoca, `usuarios_con_permiso()` |
| Sobre de error | `backend/app/errores.py` | `{detail, codigo}` del contrato §0 |
| Migracion | `backend/migrate_rbac_aditivo.py` | Idempotente |
| Seed | `backend/seed_rbac.py` | Catalogo + `APROBADOR_EQUIPO` a Melisa |

### Por que el catalogo vive en codigo y no en la tabla

Decision explicita, y es la que mas se presta a malentendido: las tablas `roles`
y `role_permissions` existen y se siembran, pero el motor **no las lee para
resolver permisos**. Lee el catalogo de `rbac_catalog.py`.

Razon: una base sin migrar, a medio sembrar o con la siembra revertida
produciria un conjunto de permisos vacio. Y un conjunto vacio es exactamente el
403 masivo que la regla 3 existe para evitar. Con el catalogo en codigo, ese
modo de falla no existe: lo peor que puede pasar es que la tabla este
desincronizada, y para eso hay una prueba que compara las dos
(`test_materializacion_en_base_coincide_con_el_catalogo`).

Lo unico que el motor consulta en caliente es `user_role_grants` — dato por
usuario que tiene que aplicar al siguiente request, no al siguiente despliegue.

Las tablas siguen sirviendo para: listar/inspeccionar el catalogo, dar
integridad referencial a las concesiones, y apagar un paquete completo con
`roles.is_active = 0` sin ir usuario por usuario.

## Catalogo

Espejo obligatorio de `docs/contratos/permisos_catalogo.json`. Hay una prueba
que compara los dos archivos y se pone roja si divergen. Renombrar una accion en
el servidor sin cambiarla en el contrato **no produce ningun error visible**:
simplemente desaparecen botones de la interfaz.

| modulo | acciones |
|---|---|
| `inicio` | `ver` |
| `perfil` | `ver`, `editar_propio` |
| `presupuestos` | `ver_global`, `ver_propio`, `subir_ticket`, `validar_ticket`, `borrar_ticket`, `gestionar_ciclos`, `gastos_generales`, `exportar` |
| `equipos_inventario` | `ver`, `crear`, `editar`, `auditar_condicion`, `dar_de_baja` |
| `equipos_prestamos` | `solicitar`, `ver_propios`, `ver_global`, `registrar_devolucion`, `cancelar`, `exportar` |
| `equipos_aprobacion` | `autorizar_entrega`, `confirmar_devolucion`, `cerrar_incidencia` |
| `usuarios` | `gestionar`, `gestionar_roles` |

### Paquetes

| Paquete | kind | Abre |
|---|---|---|
| `_PISO` | piso | `inicio:ver`, `perfil:ver`, `perfil:editar_propio`. Se suma a cualquier sesion |
| `superadmin` | base | Todo (bypass en el motor, ademas de sus filas) |
| `admin` | base | Todo `presupuestos` + `equipos_inventario:ver` + `equipos_prestamos:{solicitar,ver_propios,ver_global,registrar_devolucion,exportar}`. **Sin** `usuarios:*` (R4). **Sin** `equipos_aprobacion:*` |
| `creador` | base | `presupuestos:{ver_propio,subir_ticket}` |
| `colaborador_mkt` | base | `equipos_inventario:ver` + `equipos_prestamos:{solicitar,ver_propios,registrar_devolucion}`. Nada de presupuestos |
| `APROBADOR_EQUIPO` | aditivo | `equipos_aprobacion:*` + `equipos_prestamos:ver_global` |
| `CUSTODIO_EQUIPO` | aditivo | `equipos_inventario:{crear,editar,auditar_condicion,dar_de_baja}` + `equipos_prestamos:ver_global` |
| `AUDITOR` | aditivo | `presupuestos:ver_global` + `equipos_inventario:ver` + `equipos_prestamos:ver_global`. Cero escritura |

**Solo `superadmin` tiene `usuarios:gestionar_roles`.** R4 sigue vigente: un
admin no gestiona usuarios ni sus paquetes.

Asignacion inicial acordada el 27/07: Melisa = base `colaborador_mkt` + aditivo
`APROBADOR_EQUIPO`. La siembra `seed_rbac.py`.

## Uso en un endpoint

```python
from ..rbac import require_perm, require_cualquiera

@router.post("/{id}/autorizar-entrega")
def autorizar(id: int, user = Depends(require_perm("equipos_aprobacion", "autorizar_entrega"))):
    ...

# Cuando dos permisos abren la misma ruta con distinto alcance:
@router.get("/")
def listar(user = Depends(require_cualquiera(("equipos_prestamos", "ver_propios"),
                                             ("equipos_prestamos", "ver_global")))):
    ...   # el filtro por responsable_user_id lo aplica el endpoint, no la dependencia
```

`require_perm` valida contra el catalogo **al importar el modulo**: un typo en
el nombre del permiso revienta el arranque en vez de producir un 403 permanente
que nadie relaciona con el typo.

El alcance (ver lo propio vs ver todo) **no** lo resuelve la dependencia. La
dependencia decide si pasa; el filtro por `responsable_user_id` lo aplica el
endpoint. Mezclarlos haria imposible una ruta que sirva a los dos casos.

## Cache

Por request, nunca por proceso: se guarda en `request.state`. Un cambio de rol
tiene que verse en el siguiente request; un cache de proceso lo dejaria pegado
hasta reiniciar uvicorn.

## `GET /api/auth/me`

Unico endpoint que resuelve y devuelve `permisos`. Login, refresh y la gestion
de usuarios devuelven `UserResponse` con `permisos: {}` — el default del schema.
Es a proposito: resolver RBAC en cada login seria trabajo que nadie usa.

El cliente usa `permisos` **solo para pintar**. Cada endpoint valida por su
cuenta. El control jamas vive solo en la interfaz.

## Rollback

`RBAC_MODO=legacy` (variable de entorno, se lee en cada llamada, no al
importar): las tres tablas quedan pero **no se consultan**. Los permisos salen
de `_PISO` + rol base.

**Consecuencia que hay que conocer antes de activarlo:** los paquetes aditivos
dejan de aplicar, asi que la aprobacion de equipos queda solo en manos del
`superadmin`. Es un rollback de emergencia, no un modo de operacion.

Solo la palabra exacta `legacy` activa el rollback; cualquier otro valor cae en
`aditivo`, para que un typo en la variable no apague los aditivos en silencio.

Rollback duro: `DROP` de las tres tablas. En modo legacy la app sigue de pie sin
ellas, y `require_role(...)` nunca se retiro, asi que Presupuestos funciona
igual.

## Endpoints (contrato §7)

| Metodo | Ruta | Permiso |
|---|---|---|
| GET | `/api/roles/` | `usuarios:gestionar_roles` |
| GET | `/api/users/{id}/roles` | `usuarios:gestionar_roles` |
| POST | `/api/users/{id}/roles` | `usuarios:gestionar_roles`, body `{role_name}` |
| DELETE | `/api/users/{id}/roles/{role_name}` | `usuarios:gestionar_roles` |

Solo se conceden paquetes de kind `aditivo`. El rol base se cambia por
`PUT /api/users/{id}`, que es del otro carril. Intentar conceder un paquete base
por esta puerta da 404: desde este endpoint la coleccion asignable son los
aditivos, y `admin` no es miembro de esa coleccion.

La cuenta `superadmin` es inmutable tambien aqui: 403.

El contrato v1 **no** define POST/PUT/DELETE sobre `/api/roles/`, asi que el
catalogo de paquetes es de solo lectura por API. Se edita en
`rbac_catalog.py` + migracion.

## Pruebas

`backend/tests/rbac/` — 80 pruebas.

- `test_permisos_efectivos.py` — el set efectivo de **cada** combinacion:
  4 roles base x 8 subconjuntos de aditivos = 32 casos, uno por uno. Los
  conjuntos esperados estan escritos a mano, no derivados del catalogo: derivarlos
  haria la prueba tautologica y cualquier cambio se volveria "correcto" solo.
- `test_503_no_403.py` — mismo usuario, mismo endpoint, 403 cuando falta el
  permiso y 503 cuando la base esta caida. Se prueba tirando la tabla de
  concesiones de verdad, no parcheando la funcion.
- `test_catalogo_contrato.py` — catalogo en codigo == contrato congelado;
  materializacion en base == catalogo; `/api/auth/me` de Melisa == `auth_me.json`.
- `test_migracion_y_endpoints.py` — idempotencia y reconciliacion de la siembra,
  `usuarios_con_permiso()`, modo legacy, endpoints del contrato §7.
