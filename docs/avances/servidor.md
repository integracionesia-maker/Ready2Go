# Avances — carril servidor y datos (Control de Equipos)

Una entrada por dia de trabajo. Que hice, evidencia, bloqueos.

---

## 2026-07-28 — S1 RBAC aditivo (WP1)

Hecho:

- `backend/app/rbac_catalog.py` — catalogo de 7 modulos, 27 acciones, 8 paquetes.
- `backend/app/models_rbac.py` — `roles`, `role_permissions`, `user_role_grants`.
- `backend/app/rbac.py` — `permisos_efectivos`, `require_perm`,
  `require_cualquiera`, `modo_rbac`, cache por request.
- `backend/app/errores.py` — sobre de error `{detail, codigo}` del contrato §0.
- `backend/app/crud_rbac.py` — siembra reconciliadora, conceder/revocar,
  `usuarios_con_permiso()`.
- `backend/app/schemas_rbac.py`, `routers/roles.py`, `routers/user_roles.py`.
- `backend/migrate_rbac_aditivo.py`, `backend/seed_rbac.py`.
- `backend/app/schemas.py` — `permisos: dict[str, list[str]] = {}` en `UserResponse`.
- `backend/app/routers/auth.py` — solo `GET /me`, ahora llena `permisos`.
- `backend/app/main.py` — 2 include_router + registro del manejador de error.
- `doc/rbac-aditivo.md` — documentacion del modulo.
- `backend/tests/rbac/` — 80 pruebas.

Evidencia:

```
$ python -m pytest -q
249 passed, 1 warning in 124.67s      (169 existentes + 80 nuevas)

$ python migrate_rbac_aditivo.py      # corrida 1
  paquetes nuevos: 8 / permisos nuevos: 62 / permisos borrados: 0
$ python migrate_rbac_aditivo.py      # corrida 2 — idempotente
  paquetes nuevos: 0 / permisos nuevos: 0 / permisos borrados: 0

$ python seed_rbac.py --crear-si-falta
  + APROBADOR_EQUIPO concedido a 'melisa'
  permisos efectivos de 'melisa':
    inicio: ver
    perfil: ver, editar_propio
    equipos_inventario: ver
    equipos_prestamos: solicitar, ver_propios, ver_global, registrar_devolucion
    equipos_aprobacion: autorizar_entrega, confirmar_devolucion, cerrar_incidencia
```

Ese bloque es identico, campo por campo y en el mismo orden, a
`docs/contratos/auth_me.json`. Hay una prueba que lo afirma
(`test_permisos_de_melisa_iguales_al_fixture_del_contrato`).

Respaldo previo a la migracion: copia de `presupuesto.db` fuera del repo antes
de la primera corrida.

Criterios de cierre de S1, uno por uno:

| Criterio | Prueba | Estado |
|---|---|---|
| Set efectivo de CADA combinacion de roles | `test_set_efectivo_de_cada_combinacion` (32 casos parametrizados) | verde |
| Fallo de DB da 503, no 403 | `test_permisos_no_disponibles_es_503_con_codigo_estable` | verde |
| APROBADOR_EQUIPO no abre ni un permiso de presupuestos | `test_aprobador_no_abre_ni_un_permiso_de_presupuestos` | verde |
| Migracion corrida dos veces sin fallar | corrida real arriba + `test_sembrar_catalogo_dos_veces_no_falla_ni_duplica` | verde |
| Lectura de `RBAC_MODO` para rollback a legacy | 4 pruebas en `test_migracion_y_endpoints.py` | verde |

### Lo que encontre trabajando

**Un `lazy="selectin"` que se comia la base.** `Role.grants` y `Role.permisos`
estaban con carga anticipada: un `GET /api/roles/` inocente pegaba a
`user_role_grants` y traia todas las concesiones de todos los usuarios sin que
nadie usara el resultado. Lo detecto la prueba de que el superadmin sigue
entrando con la base de concesiones rota — se caia. Cambiado a carga diferida.

### Decisiones que hay que revisar

**1. `backend/app/errores.py` es un archivo nuevo que no estaba en mi lista de
rutas.** El contrato §0 exige un sobre de error plano `{detail, codigo}`.
`HTTPException` de FastAPI no puede producirlo: su manejador envuelve el detalle
y `codigo` sale anidado, donde el cliente no lo busca. Hace falta una excepcion
propia con su manejador. Meterla en `rbac.py` la dejaria en el modulo equivocado
— la usan tambien media, prestamos y aprobacion. Es un archivo nuevo dentro de
`backend/app/`, nadie mas lo toca, riesgo de merge cero. **Pido que se agregue a
mi lista de rutas.**

**2. `main.py` recibio una linea de mas de la cuenta.** La regla dice "imports +
include_router". Ademas de eso hay un `registrar_manejadores(app)`. Es cableado
de aplicacion, no logica: los manejadores de excepcion solo se registran a nivel
app, no hay donde mas ponerlos. Soy el unico editor del archivo, asi que no hay
riesgo de conflicto, pero lo reporto porque se sale de la letra de la regla.

**3. El catalogo de permisos vive en codigo, no en la tabla.** Las 3 tablas se
crean y se siembran, pero el motor resuelve el **contenido** de los paquetes
desde `rbac_catalog.py` y solo consulta `user_role_grants` en caliente. Razon: la
asignacion dice que `rbac_catalog.py` es la fuente unica del catalogo, y una base
sin migrar o a medio sembrar produciria el conjunto vacio que la regla del 503
existe para evitar. Hay una prueba que compara materializacion contra codigo.
Detalle completo en `doc/rbac-aditivo.md`.

### Huecos del contrato (reportados, no improvisados)

**A. `GET /api/roles/` es lo unico que el contrato congela para ese recurso.**
La tarea S1 pedia "CRUD de paquetes". El contrato v1 §7 no tiene POST, PUT ni
DELETE sobre `/api/roles/`. **No los invente.** El catalogo se edita en
`rbac_catalog.py` + migracion. Si de verdad hace falta administrarlo por API, es
cambio de contrato a v2, no una decision mia.

**B. No hay codigo de error para "paquete no asignable".** Conceder `admin`
como aditivo tiene que fallar y el contrato §0 no tiene un codigo que aplique.
Reuse `NO_ENCONTRADO` (404) en vez de inventar uno: desde ese endpoint la
coleccion asignable son los aditivos, y `admin` no es miembro. Si el cliente
necesita distinguirlo, hace falta codigo nuevo en v2.

**C. El contrato no congela la forma del cuerpo de §7.** Ni de `GET /api/roles/`
ni de `GET/POST /api/users/{id}/roles`. Las formas que elegi estan en
`app/schemas_rbac.py` y documentadas en `doc/rbac-aditivo.md`. Si el cliente ya
codifico contra otra forma, hay que alinear ahora, no en integracion.

**D. Consecuencia no escrita de `RBAC_MODO=legacy`:** apaga los aditivos, asi
que la aprobacion de equipos queda solo en manos del superadmin. Es un rollback
de emergencia, no un modo de operacion. Documentado en `doc/rbac-aditivo.md`.

Bloqueos: ninguno.

---

## 2026-07-28 — S0 Costura

Hecho:

- `backend/app/models.py`: `COLABORADOR_MKT = "colaborador_mkt"` en el enum `UserRole`.
- `backend/app/models.py`: 2 lineas de re-export al final (`models_rbac`, `models_equipos`).
  Van al final y no arriba porque los modulos nuevos referencian `users` por
  cadena, nunca por import. Import en sentido contrario cierra el ciclo.
- `backend/app/models_rbac.py`: creado, solo docstring.
- `backend/app/models_equipos.py`: creado, solo docstring.
- `backend/requirements.txt`: `reportlab>=4.2.0`, `pillow>=11.0.0`.
- `backend/requirements-dev.txt`: `freezegun>=1.5.0`.
- Dependencias instaladas.

Evidencia:

```
$ python --version
Python 3.14.6

$ python -c "import reportlab, PIL, freezegun; ..."
reportlab 5.0.0
pillow 12.2.0
freezegun ok

$ python -m pytest -q
169 passed, 1 warning in 35.07s
```

Baseline antes de tocar nada: 169 passed. Despues de S0: 169 passed. Cero
regresion, cero logica.

Nota de conteo: `CLAUDE.md` y el plan dicen 167 pruebas; la suite real en
`dami-branch` tiene 169. Uso 169 como linea base.

Bloqueos: ninguno.
