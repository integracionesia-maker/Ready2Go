# PLAN QUIRURGICO — GOCreate: integracion de Control de Prestamo de Equipo

> Fase 3.5 del framework (Planeacion Quirurgica). Estado: **PLAN — sin construir**. Requiere luz verde de Jose.
> Fecha: 27/07/2026 (lunes) · Rama: `jose-branch` · Repo: `github.com/integracionesia-maker/Ready2Go`
> Conexiones: [[CLAUDE]] | [[context]] | [[status]] | [[BACKLOG]] | [[RISKS]] | [[MVP_BREAKDOWN]] | [[DESIGN_SYSTEM]] | [[docs/presupuestos/auth/auth-arquitectura]] | [[docs/presupuestos/presupuestos-y-validacion]]

---

## Capa ejecutiva (3 lineas)

1. **Que paso:** marketing (Emily, Betzabet) pidio plataforma para controlar el prestamo de equipo de grabacion (celulares, micros, estabilizadores) con carta responsiva firmada y aprobacion de Melisa. Traian una maqueta HTML con localStorage.
2. **Que significa para el negocio:** el equipo de marketing hoy no tiene control real de quien tiene que equipo ni responsiva digital; el proyecto de presupuestos ya tiene auth, roles y deploy runbook, asi que absorber Equipos ahi cuesta menos que un sistema nuevo. El repo pasa a llamarse **Ready2Go** y queda como la plataforma de marketing (Presupuestos + Equipos). (Renombrado nuevamente a **GOCreate** el 04/08/2026; el repo de GitHub sigue en `Ready2Go`.)
3. **Que se necesita de direccion:** (a) luz verde para construir, (b) tabla de nombres+correos GO del area de marketing, (c) inventario de camaras/luces/tripies, (d) nombre de dominio y aprobacion firmada de Melisa para el costo (~11 USD/ano, va al presupuesto del departamento).

---

## 1. CONTEXTO

### 1.1 Por que

Reunion 27/07/2026 (Emily Vianney Perez Morales, Betzabet Fuentes Ramos, Jose Aguilar, Josue Benitez). Pedido literal del area:

| Pedido en la llamada | Traduccion tecnica |
|---|---|
| "llevar el debido control y las responsivas" | Modulo de prestamos con carta responsiva por folio |
| "que la plataforma se vea como algo asi... quien esta con el iPhone 17 Pro y cuando es su fecha de regreso" | Dashboard: tenedor actual por equipo + fecha de regreso + atrasos |
| "grafica de cuales estan prestados, pendientes aprobacion, completados, incompletos" | Distribucion de estados |
| "si llegara un equipo nuevo, que aqui se pueda registrar y se quede guardando" | Inventario CRUD autoservicio (no consola) |
| "buscador... y dice las especificaciones... comentarios, ya tenia el equipo desgastado pero funciona bien" | Busqueda + ficha de equipo + historial de auditorias de condicion |
| "que se genere la carta responsiva... que les llegue a ellos en PDF y a Melisa" | PDF servidor + correo a responsable y aprobador |
| "Melisa es quien va a estar autorizando si se presta o si se regreso bien" | Rol aprobador: autoriza entrega y confirma devolucion |
| "fotos de como tienen el equipo ahorita, por los dos lados" | Foto frente + atras obligatorias por equipo, en entrega y devolucion |
| "la funda, los cargadores, porque tambien se los llevan" | Accesorios por equipo + "quien se queda con el cargador" |
| "que tenga la firma" | Firma digital de quien entrega y quien recibe |
| "notificacion al correo o WhatsApp de Melisa" | Correo (decidido: SMTP GO; WhatsApp descartado por costo de API de Meta) |
| "para aprobaciones unicamente Melisa; de pedir equipo, todo el area de marketing" | Roles aditivos: aprobador unico + base colaborador para el area |
| "acoplar a la identidad de marca" | context_desing_go obligatorio |

### 1.2 Decisiones tomadas (Jose, 27/07)

| Decision | Elegido | Descartado y por que |
|---|---|---|
| Alcance visual | **Toda la app, shell nuevo liquid glass**; se migran las vistas de Presupuestos | Solo-Equipos: dejaria la app partida en dos design systems |
| Arquitectura | **Misma app FastAPI, misma DB SQLite, tablas nuevas** | DB aparte (rompe joins/backups); servicio aparte (mas piezas que operar) |
| Notificaciones | **Correo SMTP GO** | Telegram (bot extra que administrar); Resend (API key y cuenta nueva); WhatsApp (API de Meta, costo) |
| Responsiva firmada | **PDF generado en servidor + adjunto al correo** | PDF en cliente (depende del navegador, sin copia servidor); + Drive (requiere service account y dueno de carpeta) |
| Nombre del proyecto | **Ready2Go** (repo renombrado 27/07), renombrado nuevamente a **GOCreate** el 04/08/2026 | — |

### 1.3 Problema tecnico de la maqueta (no se porta tal cual)

`CONTROL_DE_EQUIPOS.htm` (1554 lineas, un solo archivo) es una maqueta valida como **especificacion funcional**, pero su implementacion no es portable:

- Estado completo en `localStorage` (`go_equipos_control_v1`) — cuota ~5 MB, y las fotos van como dataURL base64 dentro del JSON. Con 2 fotos por equipo por entrega y devolucion, la cuota se agota en decenas de prestamos.
- `APPROVERS` y las razones sociales estan hardcodeados en el JS.
- Notificaciones por `mailto:` — abre el cliente de correo del usuario, no envia nada; no hay registro de si se aviso.
- `loan.responsivaHtml` guarda **HTML renderizado** en el estado. Eso es a la vez fuga de presentacion al modelo de datos y superficie de XSS al reimportar un respaldo.
- Pestana "Respaldo" con importar JSON + "Zona de riesgo / borrar todo": en una plataforma multiusuario eso es sobrescritura arbitraria de datos de otros. No se porta.
- Sin auth: cualquiera aprueba en nombre de Melisa escribiendo su nombre en un `<select>`.

**Lo que si se porta:** el modelo funcional (7 vistas, maquina de estados, campos de la responsiva, texto legal de situaciones extraordinarias, los 8 equipos ya auditados el 10/06 con sus comentarios y links de Drive, y las 2 razones sociales).

---

## 2. ARQUITECTURA OBJETIVO

```
GOCreate (un repo, un login, un deploy, un dominio)
├── backend/  FastAPI + SQLAlchemy + SQLite
│   ├── app/routers/  auth users creators brands tickets dashboard general_expenses
│   │                 + equipment loans approvals notifications          <- NUEVOS
│   ├── app/rbac.py   motor de permisos aditivos                        <- NUEVO
│   ├── app/pdf/      generador de carta responsiva (reportlab)         <- NUEVO
│   └── app/mailer.py SMTP + cola + log + reintentos                    <- NUEVO
└── frontend/ Vite 6 + React 18.3.1 + Tailwind 3
    ├── src/design/   tokens + primitivas liquid glass                  <- NUEVO
    ├── src/modules/presupuestos/   (migracion de components/ actuales)
    └── src/modules/equipos/        7 vistas                            <- NUEVO
```

Dos modulos de negocio, un shell. La navegacion superior separa **Presupuestos** y **Equipos**; el usuario solo ve los modulos que sus permisos abren.

---

## 3. RBAC ADITIVO (patron Bruckner, adaptado)

### 3.1 Por que aditivo

Melisa aprueba equipo, pero puede o no administrar presupuestos. Emily pide equipo y podria ademas custodiar el inventario. Con rol unico (hoy: `superadmin`/`admin`/`creador`) cada combinacion obliga a inventar un rol nuevo. El patron de Bruckner (`rol` base + paquetes aditivos, union de permisos, deny-by-default) ya esta probado en produccion ahi.

### 3.2 Esquema

Se **conserva** `users.role` como rol base (no se migra a nada, cero riesgo para lo existente) y se agregan:

```sql
-- catalogo de paquetes (base y aditivos)
CREATE TABLE roles (
  name TEXT PRIMARY KEY,            -- 'superadmin','admin','creador','colaborador_mkt',
                                    -- 'APROBADOR_EQUIPO','CUSTODIO_EQUIPO','AUDITOR','_PISO'
  kind TEXT NOT NULL,               -- 'base' | 'aditivo' | 'piso'
  descripcion TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
);

-- que abre cada paquete: (modulo, accion). Sin fila = sin permiso.
CREATE TABLE role_permissions (
  role_name TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
  modulo    TEXT NOT NULL,
  accion    TEXT NOT NULL,
  PRIMARY KEY (role_name, modulo, accion)
);

-- paquetes aditivos concedidos a un usuario (0..n)
CREATE TABLE user_role_grants (
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_name   TEXT NOT NULL REFERENCES roles(name) ON DELETE RESTRICT,
  granted_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
  granted_at  DATETIME NOT NULL,
  PRIMARY KEY (user_id, role_name)
);
```

Permisos efectivos = `UNION` de los paquetes de `['_PISO', users.role, *grants]`.

- `_PISO` concede lo minimo a cualquier autenticado: `inicio:ver`, `perfil:ver`, `perfil:editar_propio`.
- Un paquete aditivo **solo** abre los `(modulo, accion)` que tiene listados. Nunca sustituye ni amplia el rol base en otro modulo.
- `superadmin` sigue siendo absoluto e inmutable por API (regla ya vigente, no se toca).

### 3.3 Catalogo de permisos

| modulo | acciones |
|---|---|
| `inicio` | `ver` |
| `perfil` | `ver`, `editar_propio` |
| `presupuestos` | `ver_global`, `ver_propio`, `subir_ticket`, `validar_ticket`, `borrar_ticket`, `gestionar_ciclos`, `gastos_generales`, `exportar` |
| `equipos_inventario` | `ver`, `crear`, `editar`, `auditar_condicion`, `dar_de_baja` |
| `equipos_prestamos` | `solicitar`, `ver_propios`, `ver_global`, `registrar_devolucion`, `cancelar`, `exportar` |
| `equipos_aprobacion` | `autorizar_entrega`, `confirmar_devolucion`, `cerrar_incidencia` |
| `usuarios` | `gestionar`, `gestionar_roles` |

### 3.4 Paquetes

| Paquete | kind | Permisos |
|---|---|---|
| `_PISO` | piso | `inicio:ver`, `perfil:ver`, `perfil:editar_propio` |
| `superadmin` | base | todo (bypass explicito en el motor, ademas de sus filas) |
| `admin` | base | todo `presupuestos:*` + `equipos_inventario:ver` + `equipos_prestamos:{solicitar,ver_propios,ver_global,registrar_devolucion,exportar}`. **Sin** `usuarios:*` (regla R4 vigente). **Sin** `equipos_aprobacion:*` |
| `creador` | base | `presupuestos:{ver_propio,subir_ticket}` |
| `colaborador_mkt` | base | `equipos_prestamos:{solicitar,ver_propios,registrar_devolucion}` + `equipos_inventario:ver`. **Nada** de presupuestos |
| `APROBADOR_EQUIPO` | aditivo | `equipos_aprobacion:{autorizar_entrega,confirmar_devolucion,cerrar_incidencia}` + `equipos_prestamos:ver_global` |
| `CUSTODIO_EQUIPO` | aditivo | `equipos_inventario:{crear,editar,auditar_condicion,dar_de_baja}` + `equipos_prestamos:ver_global` |
| `AUDITOR` | aditivo | solo lecturas globales (`*:ver*`), cero escritura |

Asignacion inicial acordada: **Melisa = base `colaborador_mkt` + aditivo `APROBADOR_EQUIPO`**. Emily/Betzabet = `colaborador_mkt` (+ `CUSTODIO_EQUIPO` si el area lo pide). Resto del area = `colaborador_mkt`. Damian/Jose = `superadmin`/`admin` como hoy.

**Regla dura:** `APROBADOR_EQUIPO` no concede un solo permiso de `presupuestos`. Hay un test que lo afirma por enumeracion, no por lectura de codigo.

### 3.5 Motor (`backend/app/rbac.py`)

```python
def permisos_efectivos(db, user) -> dict[str, set[str]]   # {modulo: {accion,...}}
def require_perm(modulo: str, accion: str)                # dependencia FastAPI -> 403
class PermisosNoDisponibles(Exception)                    # -> 503, nunca {} silencioso
```

- Resolucion cacheada por request (no por proceso: un cambio de rol debe aplicar al siguiente request).
- Si la DB falla al resolver permisos, se lanza `PermisosNoDisponibles` → **503**. Nunca devolver `{}`: un dict vacio produce 403 masivo que se lee como politica y desloguea a todos (leccion de Bruckner, CRITICO-2).
- El frontend recibe los permisos efectivos en `/api/auth/me` y los usa **solo para pintar**. Cada endpoint valida por su cuenta. El control jamas vive solo en la UI.

### 3.6 Migracion

`backend/migrate_rbac_aditivo.py`: crea las 3 tablas, siembra `roles` + `role_permissions`, y **no toca** ninguna fila de `users`. Idempotente (re-ejecutable). Rollback: `DROP` de las 3 tablas; `require_role(...)` sigue existiendo mientras dure la transicion, asi que el sistema viejo funciona sin ellas.

---

## 4. MODELO DE DATOS — EQUIPOS

### 4.1 Tablas nuevas

```sql
equipment
  id, codigo UNIQUE NULL, nombre, categoria, descripcion,
  marca, modelo, numero_serie, activo_fijo, cuenta_gmail, espacio_disponible,
  estado_operativo TEXT NOT NULL DEFAULT 'activo',   -- activo | revision | baja
  accesorios_tipicos TEXT,                           -- JSON array
  fotos_originales_url TEXT,                          -- carpeta Drive de la auditoria 10/06
  is_deleted, deleted_at, deleted_by_user_id,
  created_at, updated_at

equipment_audit                  -- historial de condicion (la maqueta solo guardaba el ultimo)
  id, equipment_id FK, condicion,        -- bueno | atencion | danado
  estado_fisico,                          -- nuevo | usado
  espacio_disponible, comentario, fecha, actor_user_id, created_at

loan
  id, folio UNIQUE,                       -- CE-0001
  responsable_user_id FK NULL, responsable_nombre, responsable_email,
  area, empresa, motivo, notas_responsiva,
  entregado_por_user_id FK,
  fecha_entrega DATE, fecha_regreso_esperada DATE NULL, fecha_regreso_real DATE NULL,
  estado TEXT NOT NULL,                   -- ver 4.3
  entrega_autorizada INTEGER NOT NULL DEFAULT 0,
  entrega_autorizada_por_user_id FK NULL, fecha_autorizacion_entrega DATETIME NULL,
  confirmada_por_user_id FK NULL, fecha_confirmacion DATETIME NULL,
  created_by_user_id FK, created_at, updated_at,
  is_deleted, deleted_at, deleted_by_user_id

loan_item
  id, loan_id FK, equipment_id FK,
  accesorios_seleccionados TEXT,          -- JSON array
  accesorios_otros, cargador_con,
  devuelto_at DATETIME NULL,              -- NULL = renglon abierto (ver 4.2)
  no_devuelto INTEGER NOT NULL DEFAULT 0, nota_devolucion,
  decision TEXT NULL,                     -- ok | danado | faltante
  nota_decision,
  UNIQUE (loan_id, equipment_id)

media_asset                               -- fotos y firmas: en disco, nunca base64 en DB
  id, loan_id FK NULL, loan_item_id FK NULL,
  kind TEXT NOT NULL,                     -- foto_entrega_frente | foto_entrega_atras |
                                          -- foto_dev_frente | foto_dev_atras |
                                          -- firma_entrega | firma_responsable
  file_name, file_path, mime_type, size_bytes, sha256,
  created_by_user_id, created_at

responsiva_doc                            -- PDF versionado, nunca se sobrescribe
  id, loan_id FK, version INTEGER NOT NULL, file_path, sha256,
  generated_by_user_id, generated_at, motivo_regeneracion NULL,
  UNIQUE (loan_id, version)

loan_event                                -- bitacora (reemplaza loan.log de la maqueta)
  id, loan_id FK, actor_user_id FK NULL, tipo, detalle, created_at

notification_log
  id, loan_id FK NULL, canal,             -- 'email'
  destinatario, asunto, tipo,             -- idempotencia: (loan_id, tipo, destinatario)
  estado,                                 -- pendiente | enviado | fallido
  intentos INTEGER NOT NULL DEFAULT 0, error TEXT NULL,
  created_at, sent_at NULL,
  UNIQUE (loan_id, tipo, destinatario)

empresa                                   -- razones sociales, editable en UI (no hardcode)
  id, razon_social UNIQUE, direccion, ciudad, rfc, is_active

folio_counter
  scope TEXT PRIMARY KEY,                 -- 'CE'
  last_value INTEGER NOT NULL
```

Seed inicial: los **8 equipos** de la auditoria del 10/06/2026 con sus comentarios reales, condicion y link de Drive (el cable tipo C fallado de los RODE queda como `condicion='atencion'`), y las **2 razones sociales** (MERCASYSTEM SA DE CV; DISTRIBUCION Y COMERCIALIZACION DE PRODUCTOS INNOVADORES INNOVA SA DE CV). Datos de `empresa` para la responsiva: SERVICIOS CORPORATIVOS QUANTUM DE OCCIDENTE, S.C. — Belisario Dominguez No. 30 Col. Centro, Morelia, Michoacan, RFC SCQ1212149P0 (tal como en la maqueta; **pendiente que marketing confirme** que esa es la razon social emisora correcta).

### 4.2 Disponibilidad: una sola fuente de verdad

La maqueta guarda `equipment.estado='prestado'` **y** la lista `loan.equipos`. Dos fuentes para el mismo hecho: si un prestamo se borra o falla a medias, el equipo queda prestado para siempre y desaparece del inventario disponible.

Decision: **no existe `equipment.estado='prestado'`.**

```
disponible(equipo) = estado_operativo == 'activo'
                     AND NOT EXISTS (loan_item abierto: devuelto_at IS NULL
                                     AND loan.estado IN ('prestado','pendiente_confirmacion')
                                     AND loan.is_deleted = 0)
```

`estado_operativo` solo guarda lo que **no** se deduce de prestamos: `activo`, `revision` (volvio danado/faltante), `baja`.

Invariante reforzada en DB, no solo en codigo:

```sql
CREATE UNIQUE INDEX ux_loan_item_equipo_abierto
  ON loan_item(equipment_id) WHERE devuelto_at IS NULL;
```

Un equipo no puede estar en dos prestamos abiertos ni con dos personas. La maqueta solo lo evitaba filtrando en el render.

### 4.3 Maquina de estados del prestamo

```
                 (firmas + fotos completas)
   borrador ──────────────────────────────▶ prestado ──▶ pendiente_confirmacion
      │                                        │                    │
      │ cancelar (libera equipos)               │ vence: overdue     │ confirma aprobador
      ▼                                        ▼  (flag, no estado)  ▼
   cancelado                              [ATRASADO]        completado | incompleto
                                                                          │
                                                              cerrar_incidencia
                                                                          ▼
                                                                    completado
```

Reglas:

- `borrador` es servidor, no cliente: el prestamo se crea al abrir el formulario para poder subir fotos/firmas por partes sin perderlas. Un borrador **no** reserva el equipo (`loan_item` se inserta al confirmar).
- `entrega_autorizada` es **ortogonal** al estado (Melisa puede autorizar antes o despues de que el equipo vuelva) pero **bloquea el cierre**: un prestamo no llega a `completado` con `entrega_autorizada=0`. En la maqueta un prestamo podia recorrer todo el flujo sin que nadie autorizara la responsiva — hueco de trazabilidad.
- `incompleto` tiene salida (`cerrar_incidencia` con nota obligatoria). En la maqueta era terminal: un equipo danado quedaba en `revision` para siempre.
- Atraso se calcula **en servidor** con fecha de `America/Mexico_City`. La maqueta compara strings ISO generados con `toISOString()` (UTC): entre 18:00 y 24:00 CDMX marca atrasado un dia antes.

---

## 5. API NUEVA

| Metodo | Ruta | Permiso | Notas |
|---|---|---|---|
| GET | `/api/equipment/` | `equipos_inventario:ver` | Busqueda `q`, filtro por categoria/condicion/disponibilidad; excluye `is_deleted` |
| POST | `/api/equipment/` | `equipos_inventario:crear` | |
| PUT | `/api/equipment/{id}` | `equipos_inventario:editar` | |
| POST | `/api/equipment/{id}/auditoria` | `equipos_inventario:auditar_condicion` | Alta en `equipment_audit` |
| POST | `/api/equipment/{id}/baja` | `equipos_inventario:dar_de_baja` | Soft delete; 409 si tiene prestamo abierto |
| GET | `/api/equipment/{id}` | `equipos_inventario:ver` | Ficha + auditorias + historial de prestamos |
| POST | `/api/loans/` | `equipos_prestamos:solicitar` | Crea `borrador` |
| POST | `/api/loans/{id}/items` | `equipos_prestamos:solicitar` | Valida disponibilidad (409 si ocupado) |
| POST | `/api/loans/{id}/media` | `equipos_prestamos:solicitar` | Multipart, una foto/firma por request |
| POST | `/api/loans/{id}/confirmar` | `equipos_prestamos:solicitar` | `borrador → prestado`: valida 2 fotos por equipo + 2 firmas, asigna folio, genera PDF v1, dispara correos |
| POST | `/api/loans/{id}/cancelar` | `equipos_prestamos:cancelar` | Solo desde `borrador`/`prestado` sin devolucion |
| POST | `/api/loans/{id}/devolucion` | `equipos_prestamos:registrar_devolucion` | `prestado → pendiente_confirmacion`; fotos de devolucion o `no_devuelto` + nota obligatoria |
| POST | `/api/loans/{id}/autorizar-entrega` | `equipos_aprobacion:autorizar_entrega` | Melisa |
| POST | `/api/loans/{id}/confirmar-devolucion` | `equipos_aprobacion:confirmar_devolucion` | Decision por equipo (`ok`/`danado`/`faltante`) → `completado`/`incompleto` |
| POST | `/api/loans/{id}/cerrar-incidencia` | `equipos_aprobacion:cerrar_incidencia` | Nota obligatoria |
| GET | `/api/loans/` | `ver_propios` / `ver_global` | Scoping server-side por `responsable_user_id` |
| GET | `/api/loans/{id}` | `ver_propios` / `ver_global` | 403 si no es suyo y no tiene global |
| GET | `/api/loans/{id}/responsiva.pdf` | participante o `ver_global` | Ultima version; `?version=` para historicas |
| GET | `/api/media/{id}` | participante o `ver_global` | **Nunca** mount estatico (mismo IDOR que ya se corrigio en tickets) |
| GET | `/api/loans/export` | `equipos_prestamos:exportar` | CSV |
| GET | `/api/equipos/dashboard` | `equipos_inventario:ver` | KPIs + distribucion de estados + "requiere atencion" |
| GET/POST/PUT | `/api/empresas/` | `usuarios:gestionar` | Razones sociales (autoservicio, no `.env`) |
| GET/POST/DELETE | `/api/users/{id}/roles` | `usuarios:gestionar_roles` | Solo superadmin; concede/revoca aditivos |

Validacion de subidas (aplica a `/media`): allowlist `image/jpeg`+`image/png` verificada por **magic bytes**, no por `Content-Type`; max 3 MB por foto, 250 KB por firma; dimensiones maximas; se recomprime en cliente antes de subir (patron `compressImage` de la maqueta, 900px/0.72) y se re-valida en servidor. `sha256` guardado para deteccion de duplicados y para el peritaje de la responsiva.

---

## 6. PDF DE LA RESPONSIVA

- Generador servidor con **reportlab** (python puro; WeasyPrint exige cairo/pango en el Mac mini — dependencia de sistema que no vale el riesgo).
- Contenido: folio, ciudad+fecha en texto, datos de la razon social emisora, parrafo de recepcion (area + empresa del colaborador), bloque por equipo (serie, activo fijo, marca, modelo, Gmail, condiciones, accesorios, quien se queda con el cargador), notas, el texto legal completo de **Situaciones extraordinarias** (dano / robo / perdida / entrega al termino de contrato / opcion de compra del celular) tal como esta redactado en la maqueta, y las dos firmas con nombre.
- Se guarda en `uploads/responsivas/{folio}_v{n}.pdf` con `sha256`. **Nunca se sobrescribe:** regenerar crea `version+1` con `motivo_regeneracion`. Un documento firmado es evidencia; sobrescribirlo destruye el rastro.
- Honestidad tecnica: una firma en canvas **no es firma electronica avanzada**. Es evidencia razonable (firma + fotos + hash + bitacora + copia por correo a ambas partes), no prueba legal irrefutable. Si RH necesita valor legal pleno, eso es otro proyecto (e.firma/PSC) y no esta en este alcance.

---

## 7. NOTIFICACIONES (SMTP GO)

| Disparador | Para | Contenido |
|---|---|---|
| Prestamo confirmado | aprobadores (`APROBADOR_EQUIPO`, resueltos de DB) | Folio, responsable, area, motivo, equipos, fecha; PDF adjunto; link a Autorizaciones |
| Prestamo confirmado | responsable | Su copia del PDF |
| Devolucion registrada | aprobadores | Equipos, fecha de regreso, link para revisar fotos |
| Devolucion confirmada | responsable | Resultado (buen estado / incidencias) |
| Vencimiento | responsable + aprobadores | Recordatorio diario para prestamos atrasados |

- Envio en `BackgroundTasks` — un SMTP caido **jamas** tumba el registro del prestamo.
- `notification_log` con `UNIQUE (loan_id, tipo, destinatario)`: reintentar no duplica correos.
- Destinatarios **resueltos por rol desde la DB**, no de una constante (la maqueta hardcodea `melisa.avendano@grupo-ortiz.com`). Si Melisa cambia de puesto, se revoca el aditivo y ya.
- Env nuevas: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `NOTIF_ENABLED`, `APP_PUBLIC_URL`. Van en `.env` (jamas al repo) y a `.env.example` con placeholders.
- Recordatorios: `scripts/recordatorios_vencimiento.py` en LaunchAgent del Mac mini (mismo patron ya documentado en `docs/deploy/runbook.md`), no un cron dentro de uvicorn.

---

## 8. FRONTEND — 100% REACT, LIQUID GLASS

### 8.1 Direccion de diseno

**Concepto:** "vitrina de equipo" — superficies de cristal oscuro sobre un fondo con profundidad, donde el equipo (fotos reales) es lo unico saturado de color. Naranja GO `#FB670B` como unico acento; el cristal aporta jerarquia, no decoracion.

Dark-first (regla del framework), claro via `[data-theme="light"]` — el selector actual **no** se toca (el PDF de Presupuestos depende de que no tenga `:root`).

Tipografia: se resuelve el pendiente #7 del BACKLOG. **Blauer Nue** (display/UI) + **Conthic** (cuerpo) autohospedadas en woff2 desde `context_desing_go`, **JetBrains Mono** para folios, series y cifras. Space Grotesk/Inter salen.

### 8.2 Receta liquid glass (y sus limites reales)

Tres capas, en este orden:

```css
.glass {
  background: linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.04));
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.25),      /* highlight superior */
    inset 0 0 0 1px rgba(255,255,255,.08),    /* rim hairline */
    0 24px 48px -12px rgba(0,0,0,.55);        /* sombra externa */
  border-radius: 20px;
}
```

Refraccion real (borde que dobla la luz) con filtro SVG `feImage` + `feDisplacementMap` (+ `feSpecularLighting` para el brillo especular) aplicado como `backdrop-filter: url(#glass)`.

**Limite que hay que respetar, no esconder:** SVG como `backdrop-filter` **solo funciona en Chromium**. Safari y Firefox lo ignoran. Por eso:

- La refraccion SVG se aplica **solo** al shell (nav + hero) detras de `@supports`; el resto usa la receta CSS de arriba, que si es cross-browser.
- **Prohibido** cristal en filas de tabla, listas largas o contenedores con scroll: cada instancia reserva GPU y compositing, y el Mac mini de produccion mas un iPhone en la mano de un creador no tienen ese presupuesto. Maximo 3-4 superficies de cristal simultaneas en pantalla.
- Contraste: todo texto sobre cristal lleva un velo solido detras (min 4.5:1 medido, no estimado). El cristal es el enemigo natural de la legibilidad; se verifica con contraste real, no a ojo.

### 8.3 Animacion

`motion` (sucesor de framer-motion) para: entrada escalonada de KPIs/cards, transicion de layout compartido card → modal de ficha, indicador de nav tipo pildora magnetica, `AnimatePresence` en modales y toasts, contadores animados en KPIs. Micro-interacciones CSS puras (hover, focus, press) para no montar JS donde no hace falta.

Todo dentro de `@media (prefers-reduced-motion: reduce)` → sin movimiento, solo opacidad. Inspiracion de patrones: uiverse.io (glassmorphism, loaders, botones), mas las recetas de refraccion citadas al final.

### 8.4 Componentes nuevos (`src/design/`)

`GlassPanel` · `GlassNav` (pildora magnetica) · `GlassModal` (layout compartido, focus trap, Esc) · `KpiTile` (contador animado) · `StatusDonut` · `EquipmentCard` (tilt 3D solo en puntero fino) · `SignaturePad` (Pointer Events, alta densidad, deshacer, `isBlank` real) · `PhotoCapture` (`capture="environment"`, compresion en cliente, frente+atras obligatorias, preview) · `Timeline` (bitacora) · `CommandPalette` (Cmd+K) · `Toast` · `SkeletonShimmer` · `EmptyState` · `RoleBadge`.

### 8.5 Vistas del modulo Equipos

| Vista | Ruta | Contenido |
|---|---|---|
| Inicio | `/equipos` | KPIs (prestados, atrasados, pendientes, disponibles), "Requiere atencion", prestamos en curso, distribucion de estados |
| Inventario | `/equipos/inventario` | Busqueda, filtros, tarjetas/tabla, ficha, alta/edicion, auditoria de condicion |
| Nuevo prestamo | `/equipos/nuevo` | Wizard 4 pasos: datos → equipos → fotos+accesorios → firmas; validacion por paso |
| Prestamos activos | `/equipos/activos` | Tabla con atraso, registrar devolucion, ver responsiva |
| Aprobaciones | `/equipos/aprobaciones` | Autorizaciones de entrega + devoluciones por confirmar (solo `APROBADOR_EQUIPO`) |
| Historial | `/equipos/historial` | Filtros por estado/persona/fecha, exportar CSV |
| Ficha de prestamo | `/equipos/prestamo/:folio` | Responsiva, fotos antes/despues lado a lado, bitacora completa |

La pestana "Respaldo" de la maqueta **no se porta**. El respaldo es responsabilidad del servidor (dump de DB por superadmin en el runbook de deploy), no un boton de "borrar todo" en la UI.

### 8.6 Presupuestos (migracion visual)

Mismo shell, mismos tokens, mismas primitivas. La logica de negocio **no se toca** (ciclos, validacion, borrado, gastos generales quedan intactos). Solo cambia la piel y la navegacion. Se conserva `useMobile`, `RowActions` y `go-table-scroll` (reglas vigentes de responsividad movil) y ApexCharts con su tema (con los `undefined` prohibidos de `apexTheme.js` intactos).

### 8.7 Presupuesto de rendimiento

Bundle inicial < 250 KB gz. Code splitting por ruta (`equipos`, `presupuestos`, PDF). `jspdf`/`html2canvas` siguen con `import()` dinamico. ApexCharts diferido. Fotos servidas con `Cache-Control` privado y miniaturas generadas en servidor (no mandar 3 MB al navegador para una miniatura de 96px).

---

## 9. QUE NO SE TOCA

| Archivo / area | Por que |
|---|---|
| `backend/app/crud.py` — `approve_ticket`, ciclos | Regla de negocio explicita: los ciclos nunca bloquean por fondos; `budget_cycle_id` se fija al subir y no se recalcula |
| Filtro `is_deleted == False` en queries de tickets/gastos | Regla dura vigente; el modulo nuevo la replica, no la modifica |
| `require_role(...)` | Se conserva funcionando mientras el RBAC nuevo entra modulo por modulo. Se retira solo cuando todos los endpoints migraron y hay tests verdes |
| Inmutabilidad de `superadmin` por API | Regla vigente |
| `[data-theme="light"]` sin `:root` en `index.css` | Lo necesita la plantilla off-screen del PDF de Presupuestos |
| Ausencia de alias manuales de `react`/`react-dom` en `vite.config.js` | Causo el bug "Invalid hook call" (15/07) |
| `apexTheme.js` / `createApexOptions` | Nunca asignar `stroke`/`fill`/`plotOptions`/`responsive` como `undefined` |
| React 18.3.1 | No se salta a React 19 en esta entrega: `react-apexcharts` y el historico de hook-call no justifican el riesgo. "100% React" = cero HTML/JS suelto, no version nueva |
| `presupuesto.db` en produccion | Toda migracion corre con respaldo previo (runbook) |

---

## 10. REVISION ADVERSARIAL — hallazgos ANTES de escribir codigo

> Nota de proceso: el framework (0.3.2) pide 3 agentes adversariales en paralelo. Esta sesion tiene el fan-out de agentes deshabilitado, asi que la pasada adversarial la hizo el agente principal por enumeracion explicita sobre la maqueta y sobre el codigo existente. Se declara para que quede claro que **no** hubo tres contextos independientes: si quieres el cruce real, se lanza en la sesion de build.

| # | Sev | Hallazgo | Mitigacion en este plan |
|---|---|---|---|
| 1 | CRIT | Doble fuente de verdad de disponibilidad (`equipment.estado` + `loan.equipos`): un prestamo borrado deja el equipo prestado para siempre | §4.2 — disponibilidad derivada; no existe `estado='prestado'` |
| 2 | CRIT | Un equipo puede quedar en dos prestamos abiertos (la maqueta solo filtra al pintar) | Indice unico parcial `ux_loan_item_equipo_abierto` |
| 3 | CRIT | IDOR en fotos y PDF: quien tenga el id descarga la responsiva de otro (ya paso una vez con `tickets/file/{id}`) | Todo por `/api/media/{id}` y `/loans/{id}/responsiva.pdf` con autorizacion por participacion o rol; sin mount estatico |
| 4 | CRIT | Firma sin auth: en la maqueta cualquiera elige "Melisa" en un `<select>` y aprueba | Autorizacion por `APROBADOR_EQUIPO` verificada en servidor; se registra `user_id` real, no un nombre escrito |
| 5 | CRIT | Colision de folio (contador en el estado, sin unicidad) | `folio_counter` + `UNIQUE(folio)` + asignacion dentro de transaccion con reintento (3) |
| 6 | ALTO | Fallo al resolver permisos → `{}` → 403 masivo que parece politica | `PermisosNoDisponibles` → 503 explicito (leccion Bruckner) |
| 7 | ALTO | Creep de privilegio del aditivo: `APROBADOR_EQUIPO` no debe abrir presupuestos | Paquetes por `(modulo, accion)`, deny-by-default + test que enumera el set efectivo de cada combinacion |
| 8 | ALTO | Fotos base64 en el estado: cuota de 5 MB, DB inflada, imposible de auditar | Archivos en disco + `sha256` + limites + magic bytes + miniaturas |
| 9 | ALTO | `loan.responsivaHtml` guarda HTML renderizado → XSS al reimportar y presentacion dentro del modelo | Nunca se guarda HTML; el PDF se genera de los datos |
| 10 | ALTO | "Importar respaldo" + "Zona de riesgo/borrar todo" en la UI: sobrescritura arbitraria multiusuario | No se portan. Respaldo/restore = servidor, superadmin, runbook |
| 11 | ALTO | Cierre del prestamo sin autorizacion de entrega: hueco de trazabilidad | `entrega_autorizada=0` bloquea `completado` |
| 12 | MED | `incompleto` terminal: equipo en `revision` para siempre | `cerrar_incidencia` con nota obligatoria |
| 13 | MED | Atraso calculado con `toISOString()` (UTC) → marca atrasado un dia antes despues de las 18:00 CDMX | Fecha de servidor en `America/Mexico_City`, columnas `DATE` |
| 14 | MED | Equipo en `revision` seleccionable para un prestamo nuevo (validado solo en un render) | Validacion server-side en `POST /loans/{id}/items` → 409 |
| 15 | MED | SMTP caido tumba el registro del prestamo si el envio es sincrono | `BackgroundTasks` + `notification_log` + reintentos |
| 16 | MED | Reintento de envio duplica correos a Melisa | `UNIQUE (loan_id, tipo, destinatario)` |
| 17 | MED | Baja/borrado de equipo con historial rompe la responsiva ya firmada | FK `RESTRICT` + solo soft delete + 409 si tiene prestamo abierto |
| 18 | MED | Cristal en tablas/scroll: jank en Mac mini y movil; SVG backdrop-filter solo Chromium | Presupuesto de 3-4 superficies, `@supports`, prohibido en scroll |
| 19 | MED | Texto sobre cristal ilegible (falla clasica de glassmorphism) | Velo solido detras del texto, contraste 4.5:1 medido |
| 20 | BAJO | Aprobador hardcodeado (`melisa.avendano@`) | Resuelto por rol desde DB |
| 21 | BAJO | Razones sociales hardcodeadas en un `<select>` | Tabla `empresa` editable en UI |
| 22 | BAJO | La maqueta pide 2 fotos por equipo pero permite guardar sin accesorios declarados; luego reclama por cargadores | Accesorios explicitos por equipo + `cargador_con` obligatorio si el equipo declara cargador |

---

## 11. PLAN DE TRABAJO (paquetes atomicos)

Orden estricto. Ningun paquete se cierra sin su verificacion.

| WP | Contenido | Verificacion de cierre |
|---|---|---|
| **WP0** | Este plan + docs de framework actualizados + rama `jose-branch` | Plan revisado por Jose (luz verde) |
| **WP1** | RBAC aditivo: 3 tablas, motor `rbac.py`, `require_perm`, `/auth/me` con permisos, migracion idempotente | `pytest` nuevo: set efectivo por combinacion de roles + 503 en fallo de DB + 167 pruebas existentes siguen verdes |
| **WP2** | Modelo Equipos: tablas, indice unico parcial, seeds (8 equipos + 2 razones sociales), `empresa`, `folio_counter` | Migracion aplica y revierte en DB de prueba; test de invariante "un equipo no en dos prestamos abiertos" |
| **WP3** | API inventario + auditorias de condicion + ficha | Tests de permisos (403/409) + CRUD |
| **WP4** | API prestamos: borrador, items, media, confirmar, devolucion, autorizar, confirmar-devolucion, cerrar-incidencia, historial, export | Test de la maquina de estados completa, incluidas transiciones invalidas |
| **WP5** | PDF responsiva (reportlab) + versionado + hash | PDF generado con datos reales de un prestamo de prueba, revisado a ojo por Jose; test de que v2 no sobrescribe v1 |
| **WP6** | Mailer SMTP + `notification_log` + reintentos + recordatorio de vencimiento | Envio real a una cuenta de prueba; test de idempotencia y de que SMTP caido no rompe el prestamo |
| **WP7** | Shell liquid glass + tokens + fuentes de marca + migracion visual de Presupuestos | Pantallazos desktop+movil; contraste medido; sin regresion en los e2e de Presupuestos |
| **WP8** | Modulo Equipos frontend: 7 vistas + firma + camara + dashboard | e2e Playwright del flujo completo: solicitar → firmar → autorizar → devolver → confirmar |
| **WP9** | Fase 6: `/cyber-neo` + hardening (HTTPS, CSP, HSTS, CORS) + dominio + deploy Mac mini | Reporte de auditoria sin criticos abiertos; app accesible por dominio con TLS |

Fase 7 (piloto) con Emily, Betzabet y Melisa sobre datos reales; Fase 8 produccion.

---

## 12. VERIFICACION

```bash
# Backend
cd backend && python -m pytest                      # 167 actuales + nuevos, todos verdes
cd backend && python migrate_rbac_aditivo.py        # idempotente: correr dos veces no falla
cd backend && python migrate_equipos.py

# Invariantes que se prueban explicitamente
#  - un equipo no puede quedar en dos prestamos abiertos
#  - APROBADOR_EQUIPO no abre ningun permiso de presupuestos
#  - fallo de DB al resolver permisos -> 503, no 403
#  - loan no llega a 'completado' con entrega_autorizada=0
#  - responsiva v2 no sobrescribe v1

# Frontend
cd frontend && npm run build                        # bundle inicial < 250 KB gz
cd frontend && npx playwright test e2e/equipos-flujo-completo.spec.js
cd frontend && npx playwright test e2e/presupuesto-flujo-completo.spec.js   # sin regresion
```

Verificacion en pantalla obligatoria (regla del pool: DOM lleno no es pantalla pintada) — captura real de cada vista en desktop y 390px antes de declarar WP7/WP8 cerrados.

---

## 13. ROLLBACK

| Escenario | Accion |
|---|---|
| RBAC nuevo rompe accesos | `RBAC_MODO=legacy` (env): los endpoints vuelven a `require_role`. Las 3 tablas quedan pero no se consultan |
| Migracion de equipos falla | `DROP` de las tablas nuevas; nada de Presupuestos las referencia |
| Shell visual rompe Presupuestos | Rutas de Presupuestos vuelven a los componentes actuales (se conservan en `modules/presupuestos/` sin borrar hasta que los e2e pasen) |
| Correos disparados por error | `NOTIF_ENABLED=false` corta el envio sin tocar codigo |
| Rollback total | `git revert` del merge del paquete; DB restaurada del respaldo previo a la migracion |

---

## 14. DEPENDENCIAS EXTERNAS (bloquean fases, no el plan)

| # | Pendiente | De quien | Bloquea |
|---|---|---|---|
| 1 | Tabla nombres + correos GO del area de marketing | Emily | WP1 (alta de usuarios) / Fase 7 |
| 2 | Inventario de camaras, luces, tripies (nombres completos) | Emily / Betzabet | WP2 (seed) — no bloquea el codigo |
| 3 | Confirmar razon social emisora de la responsiva (Quantum de Occidente vs otra) | Marketing / RH | WP5 |
| 4 | Nombre de dominio deseado | Emily / Melisa | WP9 |
| 5 | Aprobacion firmada de Melisa para el gasto de dominio (~11 USD/ano, va al presupuesto del depto) | Melisa | WP9 |
| 6 | Credenciales de la cuenta SMTP emisora | Jose / Sistemas | WP6 |
| 7 | Fuentes Blauer Nue / Conthic en woff2 | `context_desing_go` | WP7 |

---

## 15. FUENTES CONSULTADAS (tecnica de liquid glass)

- [Liquid Glass in the Browser: Refraction with CSS and SVG — kube.io](https://kube.io/blog/liquid-glass-css-svg/) (receta `feImage` + `feDisplacementMap`, limite Chromium)
- [How to create Liquid Glass effects with CSS and SVG — LogRocket](https://blog.logrocket.com/how-create-liquid-glass-effects-css-and-svg/)
- [LiquidGlass: Shimmering Glass Effect for React — Loopspeed](https://blog.loopspeed.co.uk/liquid-glass)
- [Create Apple Liquid Glass UI with Pure CSS & SVG Filter — CSS Script](https://www.cssscript.com/liquid-glass-ui/) (`feTurbulence` + `feSpecularLighting`)
- [CSS Liquid Glass effects — freefrontend](https://freefrontend.com/css-liquid-glass/)
- [Uiverse — glassmorphism UI elements](https://uiverse.io/tags/glassmorphism) (patrones de cards, botones, loaders)
