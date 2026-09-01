# Plan de implementación — Módulo **Gastos Operativos** (GOCreate)

> **SUPERADO (WP fusión, sept-2026)**: el módulo aislado que describe este documento se retiró. Gastos Operativos vive ahora fusionado en la UI de Presupuestos → Gastos Generales (mismo formulario con selector de tipo, mismo listado con distintivo visual), aunque conserva sus tablas y endpoints propios. El rol base `operativo` (amurallado, único que veía este módulo) se retiró del catálogo RBAC. Ver `docs/presupuestos/gastos-generales-manual.md` para el estado actual. Se conserva este documento como referencia histórica del diseño original.

> Estado original: **propuesta de diseño**, sin construir. Requiere luz verde explícita antes de codificar (mismo criterio que el módulo Equipos).
> Autor del plan: sesión de asistencia · Owner: Damián · Supervisión: Jose Aguilar
> Rama de trabajo: `dami-branch` · Integración a `master` solo cuando se pida.

---

## 0. Resumen ejecutivo

Un tercer módulo de la plataforma, **hermano** de Presupuestos y Equipos, para llevar un **acumulador de gastos totalmente aislado de marketing**. Cada gasto se clasifica en un **rubro** (E-commerce, IA, Aplicaciones, Campañas, Activaciones… ampliable desde la app). No hay presupuesto ni límite: el contador solo sube. Sirve para ver, mes a mes, en qué se gasta más. Tiene su propio dashboard, su propia exportación y un **rol dedicado** (`operativo`), además de `admin`/`superadmin`. Marketing no lo ve.

Técnicamente es un espejo de **Gastos Generales** (`general_expenses`) con tres diferencias: la dimensión de clasificación es un catálogo propio (`rubro`, no `brand`), hay **dos fechas** (`fecha_gasto` manual + `upload_date` automática), y **solo borrado lógico** (sin físico). El grueso del riesgo y del trabajo no está en la tabla, sino en el **RBAC** (nuevo módulo + rol, con el contrato de permisos congelado) y en el **cableado del nuevo switch** en el frontend.

---

## 1. Planeación

### 1.1 Objetivo

Registrar y consultar gastos operativos ajenos a marketing, clasificados por rubro, con evidencia obligatoria, exportables por mes o rango, y con un tablero para ver la distribución del gasto.

### 1.2 Alcance

**Dentro:**
- Dos tablas nuevas: catálogo de rubros + gastos operativos.
- CRUD de rubros (crear / editar / desactivar).
- Alta, listado (con filtros), descarga de comprobante y borrado lógico de gastos.
- Dashboard: total histórico, total por rubro y tendencia mensual.
- Exportación propia (mensual por defecto + rango configurable).
- RBAC: módulo nuevo + rol base `operativo`; acceso también para `admin`/`superadmin`.
- Nuevo switch de módulo en el frontend, con su Layout, rutas y gating por permiso.
- Pruebas (backend + e2e) y documentación completa.

**Fuera (explícito):**
- Sin presupuesto/límite/saldo restante ni ciclos.
- Sin validación/aprobación de gastos (se cuentan de inmediato, como Gastos Generales).
- Sin borrado físico.
- Sin ninguna relación con marcas, creadores, ciclos ni con los dashboards/KPIs/exportaciones de marketing.
- Sin notificaciones por correo (por ahora).

### 1.3 Decisiones ya tomadas (por el usuario)

| Tema | Decisión |
|---|---|
| Ubicación | **Switch propio** (Presupuestos / Equipos / **Gastos Operativos**) |
| Naturaleza | Acumulador puro, **sin límite** |
| Clasificación | **Rubro**, catálogo **editable** desde la app (crear/editar/desactivar) |
| Cardinalidad | **Un** rubro por gasto |
| Campos | Iguales a Gastos Generales |
| Comprobante | **Obligatorio** |
| Fechas | `fecha_gasto` (manual, define el mes) **+** `upload_date` (automática) |
| Exportación | Propia, **mensual por defecto** + rango configurable |
| Dashboard | Sí (gráficos + tabla) |
| Acceso | `admin` + `superadmin` + **rol nuevo dedicado** |
| Gestión de rubros | `admin`/`superadmin` **y** el rol nuevo |
| Borrado | **Solo lógico** |
| Aislamiento | **Total** respecto a marketing |

### 1.4 Decisiones abiertas (a ratificar antes de WP1)

Nombres técnicos propuestos — cambiarlos ahora es barato, después no:
- Módulo RBAC: `gastos_operativos`
- Rol base: `operativo`
- Tablas: `expense_rubros` (catálogo) · `operational_expenses` (gastos)
- Prefijos de API: `/api/rubros` · `/api/operational-expenses`
- Carpeta frontend: `frontend/src/modules/gastos-operativos/`

### 1.5 Restricciones del proyecto que este plan debe respetar

1. **RBAC aditivo, deny-by-default, 503-no-403.** El módulo entra por el motor existente (`rbac.py`/`rbac_catalog.py`), no con `require_role` a mano. Un fallo al resolver permisos responde 503, nunca `{}`.
2. **Contrato de permisos congelado.** `rbac_catalog.py` (`MODULOS`, `PAQUETES`) debe quedar **idéntico** a `docs/equipos/contratos/permisos_catalogo.json`, o la prueba `tests/rbac/test_catalogo_contrato.py` falla. Cualquier módulo/acción/paquete nuevo se agrega en **los dos lados**.
3. **Autenticación obligatoria** en todo endpoint (excepto `/api/health` y `/api/auth/login`).
4. **Archivos servidos solo por endpoint autenticado**, nunca mount estático (lección del IDOR de comprobantes y del path traversal del SPA fallback).
5. **Rutas relativas al cwd** del backend (`./uploads`, `./presupuesto.db`): levantar uvicorn desde `backend/`.
6. **Git por rama**, rutas explícitas en `git add` (nunca `-A`/`.`); integrar a `master` solo cuando se pida.
7. **Aislamiento de marketing**: ninguna query de este módulo toca `tickets`/`general_expenses`/`brands`/dashboards de Presupuestos, y viceversa.

### 1.6 Riesgos y mitigaciones

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Divergencia catálogo RBAC ↔ contrato congelado → botones ocultos o prueba roja | Editar los dos archivos en el mismo commit; correr `test_catalogo_contrato` antes de avanzar |
| R2 | El nuevo `require_perm("gastos_operativos", …)` truena al importar si la acción no está en el catálogo | Agregar módulo+acciones al catálogo **antes** de decorar rutas (WP1 antes que WP3) |
| R3 | Bucketing por fecha equivocada (usar `upload_date` en vez de `fecha_gasto`) → gasto en el mes incorrecto | Regla dura + prueba dedicada (gasto del día 30 subido el 4 cae en el mes del 30) |
| R4 | Fuga de aislamiento (el total operativo aparece en un KPI de marketing, o al revés) | Tablas y queries separadas; prueba de aislamiento que verifica que los endpoints de marketing no cambian al crear gastos operativos |
| R5 | IDOR / archivo servido sin permiso | Descarga por endpoint con `require_perm("gastos_operativos","ver")`; sin mount estático; nombres en disco con uuid |
| R6 | El rol `operativo` termina viendo Presupuestos/Equipos por herencia accidental | Rol base con **solo** su módulo; prueba de permisos efectivos que lo afirma por enumeración |
| R7 | En producción las tablas nuevas no se crean | `Base.metadata.create_all` corre en cada arranque; el deploy reinicia uvicorn → tablas creadas. Sembrar rubros y RBAC con scripts idempotentes |
| R8 | Módulo de tamaño real sin owner técnico dedicado | Igual que Equipos: partir en WP y estimar antes de comprometer |

### 1.7 Paquetes de trabajo y orden

Orden estricto **pruebas → motor → migración/seed → API → frontend → e2e → docs**, igual que el patrón de Equipos.

| WP | Contenido | Depende de |
|---|---|---|
| **WP0** | Ratificar nombres (§1.4) | — |
| **WP1** | RBAC: módulo `gastos_operativos` + rol `operativo` en catálogo **y** contrato; migración/seed; pruebas de permisos efectivos y de contrato | WP0 |
| **WP2** | Modelo de datos: `expense_rubros` + `operational_expenses` (+ índices); seed idempotente de los 5 rubros iniciales | WP1 |
| **WP3** | API rubros (catálogo) + API gastos (alta, listado, descarga, borrado lógico, export, dashboard) | WP2 |
| **WP4** | Frontend: switch nuevo, Layout, rutas, `roles.js`; pantallas Registro/Listado, Rubros, Dashboard, Export | WP3 |
| **WP5** | e2e Playwright del flujo completo + gating del switch por permiso | WP4 |
| **WP6** | Documentación (manual, reglas críticas, contrato, changelog, índices) | WP1–WP5 |

---

## 2. Diseño

### 2.1 Modelo de datos

Dos tablas nuevas en un archivo propio (p. ej. `backend/app/models_operativos.py`, re-exportado desde `models.py` al final, mismo patrón que `models_equipos`/`models_rbac` para no cerrar ciclos de import).

**`expense_rubros`** (catálogo, espejo de `brands`):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `nombre` | String(100) | **único**, no nulo |
| `is_active` | Boolean | default `True`; desactivar oculta de altas nuevas, conserva histórico |

**`operational_expenses`** (espejo de `general_expenses`, con dos fechas y sin hard delete):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `rubro_id` | FK → `expense_rubros.id` `ondelete=RESTRICT` | **obligatorio** (`nullable=False`) |
| `amount` | Float | no nulo, > 0 (validado en schema) |
| `description` | Text | no nulo |
| `fecha_gasto` | Date | **manual, no nula** — define el mes/periodo |
| `file_name` / `file_path` / `mime_type` | String | comprobante **obligatorio** |
| `upload_date` | DateTime | automática (`_ahora_utc`), trazabilidad |
| `created_by_user_id` | FK → `users.id` `ondelete=SET NULL` | |
| `is_deleted` / `deleted_at` / `deleted_by_user_id` | Bool/DateTime/FK | **solo borrado lógico** |

Índices: `ix_operational_expenses_rubro` (rubro_id), `ix_operational_expenses_fecha` (fecha_gasto). Todas las queries filtran `is_deleted == False` **sin excepción** (misma regla que tickets).

**Migración:** las tablas se crean solas con `Base.metadata.create_all` al arrancar. No hace falta `ALTER`. Sí hace falta un seed idempotente (`seed_gastos_operativos.py`) que inserte los 5 rubros iniciales sin duplicar si ya existen.

### 2.2 Reglas de negocio

1. **Acumulador puro.** No hay presupuesto ni saldo; el dashboard solo suma lo gastado. Ninguna operación bloquea por "fondos".
2. **El mes lo define `fecha_gasto`.** Un gasto del 30-ago subido el 4-sep cuenta en agosto. `upload_date` es solo metadato.
3. **Comprobante obligatorio** en el alta (400/422 si falta), validado por extensión + MIME + tamaño (mismo criterio que `upload_manager`).
4. **Un rubro por gasto**; el rubro debe existir y estar activo al momento del alta.
5. **Solo borrado lógico.** `is_deleted=True` lo saca de todo cálculo; el registro y el archivo se conservan. No existe endpoint de borrado físico.
6. **Aislamiento.** Cero relación con `tickets`/`general_expenses`/`brands`/ciclos/dashboards de marketing.

### 2.3 RBAC

**Módulo nuevo** en `MODULOS` (código) y en `permisos_catalogo.json` (contrato):

```
"gastos_operativos": ["ver", "crear", "borrar", "exportar", "gestionar_rubros"]
```

**Paquetes** (código + contrato):
- **`operativo`** (base, nuevo): `{ "gastos_operativos": ["ver","crear","borrar","exportar","gestionar_rubros"] }`. Solo su módulo + el piso (inicio, perfil). Nada de Presupuestos ni Equipos.
- **`admin`** (base, se le agrega): sumar `"gastos_operativos": [las 5 acciones]`.
- **`superadmin`**: `*` — incluye el módulo nuevo automáticamente.
- **Marketing** (`marketing_*`, `creador`, etc.): **no se tocan** → sin acceso.

Matriz resultante:

| Acción \ Rol | superadmin | admin | operativo | marketing_* / creador |
|---|:--:|:--:|:--:|:--:|
| ver / crear / borrar / exportar | ✔ | ✔ | ✔ | ✗ (403) |
| gestionar_rubros | ✔ | ✔ | ✔ | ✗ |

Siembra: editar el catálogo → correr `migrate_rbac_aditivo.py` (que llama `crud_rbac.sembrar_catalogo`, reconciliador: agrega filas nuevas y limpia las que salieron del código).

### 2.4 API

Autenticación en todos. Permiso vía `require_perm(...)` del motor aditivo.

**Catálogo de rubros — `/api/rubros`**

| Método | Ruta | Permiso | Request | Response |
|---|---|---|---|---|
| GET | `/api/rubros?active_only=` | `gastos_operativos:ver` | — | `[{id, nombre, is_active}]` |
| POST | `/api/rubros` | `gastos_operativos:gestionar_rubros` | `{nombre}` | rubro creado (409 si nombre duplicado) |
| PUT | `/api/rubros/{id}` | `gastos_operativos:gestionar_rubros` | `{nombre?, is_active?}` | rubro actualizado |

Desactivar = `PUT {is_active:false}`. Un rubro con gastos históricos **no** se borra (RESTRICT); solo se desactiva.

**Gastos — `/api/operational-expenses`**

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| GET | `/?rubro_id=&start_date=&end_date=` | `…:ver` | Lista no borrados, filtra por `fecha_gasto`. Devuelve `rubro_nombre` en la fila |
| POST | `/` (multipart) | `…:crear` | `rubro_id, amount>0, description, fecha_gasto, file` (comprobante obligatorio) |
| GET | `/{id}/file` | `…:ver` | Descarga autenticada del comprobante (sin mount estático) |
| POST | `/{id}/soft-delete` | `…:borrar` | Borrado lógico |
| GET | `/export?months=YYYY-MM,…` **o** `?start_date=&end_date=` | `…:exportar` | Datos para CSV/PDF; mensual por defecto |
| GET | `/dashboard?start_date=&end_date=` | `…:ver` | `{ total, por_rubro:[{rubro,total,count}], mensual:[{month,total,count}] }` (agrega por `fecha_gasto`) |

Sin endpoint de borrado físico (a diferencia de `general_expenses`).

Errores: 401 sin sesión, 403 sin permiso, 503 si el motor no resuelve permisos, 400/422 en validación (monto ≤ 0, sin comprobante, rubro inexistente/inactivo, formato de archivo).

### 2.5 Almacenamiento de archivos

- Validación por extensión + MIME + tamaño (≤10 MB), reusando el patrón de `upload_manager`.
- Nombre en disco = uuid (dato de nombre del cliente es hostil); carpeta propia `./uploads/operativos/`.
- Servido **solo** por `GET /{id}/file` con `require_perm("gastos_operativos","ver")`. Nunca mount estático. Estos gastos no son "de un usuario", así que la autorización es por permiso de módulo (no IDOR por dueño), pero **sí** exige el permiso: un rol de marketing recibe 403 y una request sin sesión, 401.

### 2.6 Frontend

- **Switch:** agregar item a `MODULE_NAV_ITEMS` (`shell/navItems.js`), visible solo si el usuario tiene algún permiso de `gastos_operativos` (mismo patrón que Equipos, que redirige a `/` si no hay permiso).
- **Rutas:** en `App.jsx`, subárbol `/gastos-operativos/*` bajo `AppShell` + `ProtectedRoute`.
- **`roles.js` propio del módulo** (o extender el patrón) con los conjuntos de roles, fuente única para rutas/menú/tarjetas.
- **Layout** `GastosOperativosLayout` (calcado de `EquiposLayout`: Header con subtítulo propio + sidebar propio).
- **Pantallas:**
  1. **Registro + listado** — modal de alta (rubro, monto, descripción, **fecha del gasto**, comprobante obligatorio, con soporte de cámara en móvil vía `CameraCaptureButton`), tabla con filtros (rubro, rango de fechas) usando `DateRangeFilter`, `RowActions` (ver comprobante con `MediaViewer`, borrar), y total.
  2. **Dashboard** — KPIs (total, # gastos), donut por rubro, barras/línea de tendencia mensual (ApexCharts + `createApexOptions`), rango configurable.
  3. **Rubros** — tabla + alta/edición/desactivar (gateado por `gestionar_rubros`).
  4. **Exportación** — modal propio (CSV/PDF), mensual por defecto + rango; PDF con el generador existente (`jspdf`/`html2canvas`, import dinámico).
- **Reúso:** `GlassPanel`, `RowActions`, `DateRangeFilter`, `MediaViewer`, `CameraCaptureButton`, `KpiTile`, `SkeletonShimmer`, tema Apex. Cero HTML/JS suelto (100% React).

---

## 3. Implementación (paso a paso)

**WP1 — RBAC (pruebas primero).**
1. Prueba: `operativo` resuelve solo `{inicio, perfil, gastos_operativos}`; marketing no obtiene el módulo; admin sí.
2. Editar `rbac_catalog.py`: agregar módulo `gastos_operativos` a `MODULOS` y paquete `operativo` + acciones en `admin`.
3. Reflejar **idéntico** en `docs/equipos/contratos/permisos_catalogo.json`.
4. Correr `test_catalogo_contrato` (verde) + las pruebas nuevas.
5. `migrate_rbac_aditivo.py` para sembrar en la base.

**WP2 — Datos.** `models_operativos.py` (2 tablas + índices), re-export desde `models.py`. `seed_gastos_operativos.py` idempotente con los 5 rubros. Prueba de creación de tablas y del seed.

**WP3 — API.** `schemas_operativos.py`, `crud_operativos.py`, `routers/rubros.py` y `routers/operational_expenses.py`; registrar routers en `main.py` (dashboard antes de `/{id}` para que no se lo trague, como en Equipos). Reusar `upload_manager` para archivos. Pruebas de API por endpoint.

**WP4 — Frontend.** Módulo `gastos-operativos/` con su `api/`, Layout, sidebar, `roles.js`, y las 4 pantallas. Registrar el switch y las rutas. Gating por permiso.

**WP5 — e2e.** Flujo: crear rubro → registrar gasto con comprobante y fecha → verlo en tabla/total → dashboard → export; y que un usuario sin permiso no ve el switch.

**WP6 — Docs** (ver §5).

---

## 4. Testeo

**Backend (pytest, DB de prueba propia):**

`tests/operativos/test_rubros.py`
- Alta, nombre único (409 duplicado), edición, desactivar.
- Desactivar oculta de altas pero conserva gastos históricos.
- Solo `gestionar_rubros` muta; `ver` solo lista.

`tests/operativos/test_operational_expenses.py`
- Alta válida cuenta de inmediato; monto ≤ 0 → 422; **sin comprobante → 400/422**; rubro inexistente/inactivo → 400.
- **Bucketing por `fecha_gasto`**: gasto con `fecha_gasto` = 30-ago subido "hoy" (freeze en sep) aparece en agosto en export y dashboard.
- Listado con filtros (rubro, rango) y total correcto.
- Borrado lógico saca del total; **no existe** endpoint de borrado físico (404/405).
- Descarga de comprobante: con permiso 200; rol de marketing 403; sin sesión 401.
- Dashboard: total, por_rubro y mensual cuadran con los datos.

`tests/rbac/` (extender)
- `operativo` efectivo = piso + `gastos_operativos` (enumerado); nada de presupuestos/equipos.
- Marketing y `creador` → 403 en el módulo.
- 503-no-403 en fallo de resolución (patrón existente).
- `test_catalogo_contrato` verde tras el cambio.

`tests/operativos/test_aislamiento.py`
- Crear gastos operativos **no** altera ningún endpoint/total de marketing (`/api/dashboard/*`, brand-spend, `general-expenses`), ni al revés.

**Frontend (Playwright):** `e2e/gastos-operativos.spec.js` — flujo completo + gating del switch. Correr aislado del resto por el rate limit de login.

**Meta de cobertura:** toda regla de negocio de §2.2 con al menos una prueba; toda acción de permiso con su caso 200/403.

---

## 5. Documentación (entregable de primer nivel)

La documentación es parte del "terminado", no un extra. Se crea/actualiza:

**Nueva, en `docs/gastos-operativos/`:**
- `plan-implementacion.md` — este documento.
- `manual-usuario.md` — por rol (`operativo`, `admin`, `superadmin`): cómo registrar un gasto, gestionar rubros, leer el dashboard, exportar; capturas; qué ve y qué no cada rol.
- `reglas-de-negocio.md` — acumulador sin límite, `fecha_gasto` define el mes, comprobante obligatorio, borrado solo lógico, aislamiento de marketing (con ejemplos).

**Actualizaciones a docs existentes:**
- **`CLAUDE.md`** → nueva entrada en "Reglas críticas": el módulo, su aislamiento de marketing, `fecha_gasto` define el mes, solo borrado lógico, rol `operativo`, quién gestiona rubros. (Igual de vinculante que las reglas de tickets/gastos generales.)
- **`docs/README.md`** → índice con la nueva carpeta.
- **`docs/equipos/contratos/permisos_catalogo.json`** → módulo `gastos_operativos` + paquete `operativo` (contrato congelado; espejo obligatorio del código).
- **`docs/presupuestos/auth/auth-arquitectura.md`** → agregar el rol `operativo` a la matriz de roles/permisos.
- **`CHANGELOG.md`**, **`avances_diarios.md`**, **`status.md`**, **`MVP_BREAKDOWN.md`** → registrar el módulo y su avance.
- **`backend/CLAUDE.md`** / **`frontend/CLAUDE.md`** → si se agregan convenciones (carpeta de uploads propia, patrón de módulo nuevo).

**Docstrings de código** (mismo estándar que el resto del repo): los `models_operativos.py`, `crud_operativos.py` y routers explican el *porqué* de las decisiones no obvias (dos fechas, solo soft-delete, aislamiento).

---

## 6. Definición de terminado (DoD)

- [ ] Nombres de §1.4 ratificados.
- [ ] Catálogo RBAC (código) == contrato (JSON); `test_catalogo_contrato` verde.
- [ ] Tablas creadas; seed de rubros idempotente corre sin duplicar.
- [ ] Todos los endpoints con su permiso correcto (200/403/401/503 probados).
- [ ] Reglas de negocio de §2.2 cubiertas por pruebas (incluido el bucketing por `fecha_gasto` y el aislamiento).
- [ ] Frontend: switch gateado por permiso; las 4 pantallas funcionan; comprobante obligatorio y cámara en móvil.
- [ ] e2e del flujo completo en verde.
- [ ] Suite backend completa en verde (`cd backend && python -m pytest`).
- [ ] Documentación de §5 escrita y enlazada.
- [ ] Revisión de seguridad mínima: archivo servido solo con permiso, sin mount estático, sin fuga de aislamiento.

## 7. Checklist de despliegue (cuando se apruebe)

1. Integrar a `master` con `--no-ff` (respaldo con tags `pre-integracion/*` primero).
2. En el droplet: respaldo de `presupuesto.db` + `uploads/` → `git reset --hard origin/master`.
3. Reiniciar backend → `Base.metadata.create_all` crea las tablas nuevas.
4. Correr `migrate_rbac_aditivo.py` (siembra módulo/rol) y `seed_gastos_operativos.py` (rubros iniciales).
5. `npm ci` + `vite build` (frontend nuevo) → restart.
6. Verificar por `gocreate.mx`: el switch aparece para `operativo`/`admin`, no para marketing; alta con comprobante; export; y que el traversal sigue cerrado.
7. Crear los usuarios con rol `operativo` desde gestión de usuarios (superadmin).

---

## Anexo A — Mapa de archivos

**Backend nuevos:** `app/models_operativos.py`, `app/schemas_operativos.py`, `app/crud_operativos.py`, `app/routers/rubros.py`, `app/routers/operational_expenses.py`, `seed_gastos_operativos.py`, `tests/operativos/*`.
**Backend tocados:** `app/models.py` (re-export), `app/main.py` (routers), `app/rbac_catalog.py` (módulo+rol), `migrate_rbac_aditivo.py` (si aplica).
**Frontend nuevos:** `src/modules/gastos-operativos/**` (Layout, sidebar, `roles.js`, `api/`, `pages/`, `components/`), `e2e/gastos-operativos.spec.js`.
**Frontend tocados:** `src/App.jsx` (rutas), `src/shell/navItems.js` (switch).
**Docs:** `docs/gastos-operativos/*`, `docs/equipos/contratos/permisos_catalogo.json`, `docs/README.md`, `docs/presupuestos/auth/auth-arquitectura.md`, `CLAUDE.md`, `CHANGELOG.md`, `avances_diarios.md`, `status.md`, `MVP_BREAKDOWN.md`.

## Anexo B — Por qué es un módulo y no una sección de Presupuestos

Tres factores lo justifican: (1) **audiencia distinta** — un rol dedicado que no toca marketing; (2) **superficie propia** — 4 vistas (registro, dashboard, rubros, export) comparables a Equipos; (3) **requisito explícito de aislamiento** — embeberlo en Presupuestos rompería justo lo que se pidió. Meterlo en Presupuestos solo se justificaría si lo usara la misma gente y fuera una sola tabla; no es el caso.
