# Contrato de API — Control de Equipos v1 — CONGELADO

> **Congelado 2026-07-27.** Hay codigo construyendose contra este documento en paralelo.
> Cambiarlo requiere version nueva (`v2`), entrada en `CHANGELOG_CONTRATO.md` y aviso el mismo dia.
> **Prohibida la edicion silenciosa.** Si un lado codifica contra un contrato que cambio sin aviso, el error es del que lo cambio.
> Solo lectura para quien implementa. Si algo no alcanza: se reporta, no se improvisa.

---

## 0. Reglas generales

**Idioma de las rutas: ingles, sin excepcion.** `/api/equipment`, `/api/loans`, `/api/media`, `/api/empresas`. Mezclar idiomas en el mismo recurso garantiza un bug de cliente.

**Autenticacion:** cookie `access_token` httpOnly, igual que el resto de la app. Todo endpoint de este contrato exige sesion.

**Fechas y hora:**
- `DATE` → string `"YYYY-MM-DD"`, zona `America/Mexico_City`.
- `DATETIME` → ISO-8601 con offset: `"2026-07-27T17:45:00-06:00"`.
- **El servidor entrega `atrasado` (bool) y `dias_atraso` (int) ya calculados. El cliente NUNCA recalcula atraso.** Hacerlo en el navegador con `toISOString()` marca atrasado un dia antes despues de las 18:00.

**Sobre de error unico.** Todo error responde:
```json
{ "detail": "texto legible para la persona", "codigo": "CODIGO_ESTABLE" }
```

| codigo | HTTP | Significado |
|---|---|---|
| `SIN_PERMISO` | 403 | El usuario no tiene la accion requerida |
| `PERMISOS_NO_DISPONIBLES` | 503 | No se pudieron resolver permisos (fallo de DB). **Jamas se interpreta como sesion invalida. No desloguear.** |
| `EQUIPO_OCUPADO` | 409 | El equipo ya esta en un prestamo abierto |
| `TRANSICION_INVALIDA` | 409 | La operacion no aplica al estado actual del prestamo |
| `MEDIA_INVALIDA` | 422 | Archivo que no pasa validacion por magic bytes |
| `MEDIA_MUY_GRANDE` | 413 | Excede 3 MB (foto) o 250 KB (firma) |
| `NO_ENCONTRADO` | 404 | Incluye recursos con borrado logico |

**Paginacion:** listados aceptan `?limit=` (default 50, max 200) y `?offset=`. Responden `{items: [...], total: N}`.

---

## 1. Permisos

`GET /api/auth/me` — se amplia el endpoint existente. Agrega el campo `permisos`:

```json
{
  "id": 4, "username": "melisa", "email": "melisa.avendano@grupo-ortiz.com",
  "full_name": "Melisa Avendano", "role": "colaborador_mkt",
  "creator_id": null, "is_active": true, "must_change_password": false,
  "permisos": {
    "inicio": ["ver"],
    "perfil": ["ver", "editar_propio"],
    "equipos_inventario": ["ver"],
    "equipos_prestamos": ["solicitar", "ver_propios", "ver_global", "registrar_devolucion"],
    "equipos_aprobacion": ["autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"]
  }
}
```

- `permisos` es `{modulo: [acciones]}`. **Default `{}`** para no romper nada existente (JSON no tiene sets; por eso lista, no set).
- El cliente **solo pinta** con esas claves. Cada endpoint valida por su cuenta. El control jamas vive solo en la UI.
- Catalogo completo de modulos y acciones: `permisos_catalogo.json`. **Renombrar una accion sin cambiar ese archivo hace que la UI esconda botones en silencio, sin error visible.** Por eso es contrato y no codigo.

---

## 2. Inventario

| Metodo | Ruta | Permiso |
|---|---|---|
| GET | `/api/equipment/` | `equipos_inventario:ver` |
| GET | `/api/equipment/dashboard` | `equipos_inventario:ver` |
| GET | `/api/equipment/{id}` | `equipos_inventario:ver` |
| POST | `/api/equipment/` | `equipos_inventario:crear` |
| PUT | `/api/equipment/{id}` | `equipos_inventario:editar` |
| POST | `/api/equipment/{id}/auditoria` | `equipos_inventario:auditar_condicion` |
| POST | `/api/equipment/{id}/baja` | `equipos_inventario:dar_de_baja` |

**`/dashboard` se declara ANTES de `/{id:int}`** o el enrutador se lo traga como id.

`GET /api/equipment/` — query: `q`, `categoria`, `condicion`, `disponible` (bool), `limit`, `offset`.

```json
{ "items": [ {
    "id": 3, "codigo": null,
    "nombre": "Celular para grabaciones — iPhone 17 Pro gris (Jeziel)",
    "categoria": "Celular para grabaciones y videos",
    "marca": null, "modelo": "iPhone 17 Pro", "numero_serie": null,
    "activo_fijo": null, "cuenta_gmail": null,
    "espacio_disponible": "87.43 GB de 256 GB",
    "estado_operativo": "activo",
    "condicion": "bueno",
    "accesorios_tipicos": ["Cargador", "Funda"],
    "disponible": false,
    "tenedor_actual": { "nombre": "Ana Ruiz", "user_id": 12 },
    "fecha_regreso_esperada": "2026-07-30",
    "atrasado": false, "dias_atraso": 0
  } ], "total": 8 }
```

`tenedor_actual`, `fecha_regreso_esperada`, `atrasado` y `dias_atraso` vienen **en la fila del listado**, no en un segundo request: la pantalla de inventario los pinta directo.
`disponible` = `estado_operativo == "activo"` **y** sin renglon de prestamo abierto. **No existe `estado = "prestado"`.**

`POST /api/equipment/{id}/baja` → `409 EQUIPO_OCUPADO` si tiene prestamo abierto.

`GET /api/equipment/dashboard`:
```json
{ "prestados": 3, "atrasados": 1, "pendientes_confirmacion": 2, "disponibles": 4,
  "por_estado": {"prestado": 3, "pendiente_confirmacion": 2, "completado": 11, "incompleto": 1},
  "requiere_atencion": [ {"loan_id": 7, "folio": "CE-0007", "motivo": "atrasado 3 dias",
                          "responsable": "Ana Ruiz", "equipos": ["Osmo DJI 7 (1)"]} ] }
```

---

## 3. Prestamos

| Metodo | Ruta | Permiso |
|---|---|---|
| POST | `/api/loans/` | `equipos_prestamos:solicitar` (crea `borrador`) |
| GET | `/api/loans/` | `ver_propios` / `ver_global` |
| GET | `/api/loans/{id}` | participante o `ver_global` |
| GET | `/api/loans/by-folio/{folio}` | participante o `ver_global` |
| POST | `/api/loans/{id}/items` | `equipos_prestamos:solicitar` |
| DELETE | `/api/loans/{id}/items/{item_id}` | `equipos_prestamos:solicitar` |
| POST | `/api/loans/{id}/media` | `equipos_prestamos:solicitar` |
| POST | `/api/loans/{id}/confirmar` | `equipos_prestamos:solicitar` |
| POST | `/api/loans/{id}/cancelar` | `equipos_prestamos:cancelar` |
| POST | `/api/loans/{id}/devolucion` | `equipos_prestamos:registrar_devolucion` |
| GET | `/api/loans/{id}/responsiva.pdf` | participante o `ver_global` |
| GET | `/api/loans/export` | `equipos_prestamos:exportar` (CSV) |

`GET /api/loans/` — query: `estado`, `mios` (bool), `q`, `desde`, `hasta`, `limit`, `offset`.
**`?estado=borrador&mios=1` es como el wizard recupera un borrador propio** si la persona cerro la pestaña. Sin eso el borrador queda huerfano.

`GET /api/loans/{id}` — este payload es el criterio de aceptacion; su copia literal esta en `fixtures/prestamo_demo.json`:

```json
{
  "id": 7, "folio": "CE-0007",
  "estado": "prestado",
  "responsable": { "user_id": 12, "nombre": "Ana Ruiz", "email": "ana.ruiz@grupo-ortiz.com" },
  "area": "Contenido", "empresa": "MERCASYSTEM SA DE CV",
  "motivo": "Live Plaza Madero",
  "notas_responsiva": null,
  "entregado_por": { "user_id": 4, "nombre": "Melisa Avendano" },
  "fecha_entrega": "2026-07-25",
  "fecha_regreso_esperada": "2026-07-30",
  "fecha_regreso_real": null,
  "atrasado": false, "dias_atraso": 0,
  "entrega_autorizada": false,
  "entrega_autorizada_por": null,
  "fecha_autorizacion_entrega": null,
  "confirmada_por": null, "fecha_confirmacion": null,
  "items": [ {
      "id": 11, "equipment_id": 3,
      "equipo_nombre": "Celular para grabaciones — iPhone 17 Pro gris (Jeziel)",
      "accesorios_seleccionados": ["Cargador", "Funda"],
      "accesorios_otros": null,
      "cargador_con": "responsable",
      "devuelto_at": null, "no_devuelto": false,
      "nota_devolucion": null, "decision": null, "nota_decision": null,
      "media": { "foto_entrega_frente": 41, "foto_entrega_atras": 42,
                 "foto_dev_frente": null, "foto_dev_atras": null }
  } ],
  "firmas": { "firma_entrega": 39, "firma_responsable": 40 },
  "responsiva": { "version": 1, "url": "/api/loans/7/responsiva.pdf" },
  "eventos": [ { "id": 21, "tipo": "creado", "actor": "Ana Ruiz",
                 "detalle": "Prestamo confirmado. Carta responsiva firmada por ambas partes.",
                 "created_at": "2026-07-25T10:14:00-06:00" } ]
}
```

Los valores de `media` son **ids**, no URLs. Se leen por `GET /api/media/{id}`.

### Maquina de estados

```
borrador --confirmar--> prestado --devolucion--> pendiente_confirmacion
   |                                                      |
 cancelar                                        confirmar-devolucion
   v                                                      v
cancelado                                     completado | incompleto
                                                              |
                                                     cerrar-incidencia
                                                              v
                                                         completado
```

Reglas que el servidor hace cumplir y el cliente debe reflejar:

- `POST /confirmar` exige **2 fotos por equipo** (frente y atras) y **las 2 firmas**. Si falta algo: `409 TRANSICION_INVALIDA` con el detalle de que falta. Asigna folio y genera el PDF v1.
- `POST /items` → `409 EQUIPO_OCUPADO` si el equipo ya esta en otro prestamo abierto. Hay indice unico en la base: la carrera entre dos personas pidiendo el mismo equipo se resuelve ahi, no en la UI.
- `POST /devolucion` — por cada equipo: 2 fotos de devolucion, **o** `no_devuelto: true` con `nota_devolucion` obligatoria.
- **`entrega_autorizada` es ORTOGONAL al estado.** Un prestamo puede estar devuelto y seguir sin autorizar. Son dos badges distintos, no uno.
- **Un prestamo con `entrega_autorizada: false` NO puede llegar a `completado`**: `409 TRANSICION_INVALIDA`.
- Cualquier transicion que no este en el diagrama: `409 TRANSICION_INVALIDA`.

---

## 4. Aprobacion

| Metodo | Ruta | Permiso |
|---|---|---|
| POST | `/api/loans/{id}/autorizar-entrega` | `equipos_aprobacion:autorizar_entrega` |
| POST | `/api/loans/{id}/confirmar-devolucion` | `equipos_aprobacion:confirmar_devolucion` |
| POST | `/api/loans/{id}/cerrar-incidencia` | `equipos_aprobacion:cerrar_incidencia` |

`POST /confirmar-devolucion` — body con una decision por equipo:
```json
{ "decisiones": [ { "loan_item_id": 11, "decision": "ok", "nota": null },
                  { "loan_item_id": 12, "decision": "danado", "nota": "Lente rayado" } ] }
```
`decision` ∈ `ok | danado | faltante`. **Nota obligatoria si no es `ok`** (`422`).
Resultado: todas `ok` → `completado`. Alguna distinta → `incompleto`, y esos equipos pasan a `estado_operativo: "revision"`.

`POST /cerrar-incidencia` — body `{ "nota": "..." }`, obligatoria. Devuelve los equipos a `activo` y el prestamo a `completado`.

---

## 5. Media

| Metodo | Ruta | Permiso |
|---|---|---|
| POST | `/api/loans/{id}/media` | `equipos_prestamos:solicitar` |
| GET | `/api/media/{id}` | participante o `ver_global` |
| GET | `/api/media/{id}?tamano=thumb` | igual |

**Multipart, un archivo por request.** Campos: `file`, `kind`, `loan_item_id` (opcional segun `kind`).

`kind` ∈ `foto_entrega_frente | foto_entrega_atras | foto_dev_frente | foto_dev_atras | firma_entrega | firma_responsable`

- Validacion por **magic bytes**, no por `Content-Type`. Solo `image/jpeg` e `image/png`.
- Limites: **3 MB** foto, **250 KB** firma. Excederlos: `413 MEDIA_MUY_GRANDE`.
- El cliente comprime a **900px / calidad 0.72** antes de subir; el servidor re-valida.
- Respuesta: `{ "id": 41, "kind": "foto_entrega_frente", "sha256": "..." }`
- **`?tamano=thumb` devuelve una miniatura de 96px generada en servidor.** Usala en listados: bajar 3 MB para pintar 96px revienta el presupuesto de rendimiento.
- **Nunca hay mount estatico.** Todo pasa por endpoint autenticado con autorizacion por participacion.

---

## 6. Empresas (razones sociales)

| Metodo | Ruta | Permiso |
|---|---|---|
| GET | `/api/empresas/` | autenticado |
| POST/PUT | `/api/empresas/{id}` | `usuarios:gestionar` |

```json
{ "id": 1, "razon_social": "MERCASYSTEM SA DE CV", "direccion": null, "ciudad": null, "rfc": null, "is_active": true }
```
La razon social **emisora** de la carta responsiva sale de esta tabla. **Jamas hardcode en el PDF.**

---

## 7. Roles

| Metodo | Ruta | Permiso |
|---|---|---|
| GET | `/api/roles/` | `usuarios:gestionar_roles` |
| GET | `/api/users/{id}/roles` | `usuarios:gestionar_roles` |
| POST | `/api/users/{id}/roles` | `usuarios:gestionar_roles` (body `{role_name}`) |
| DELETE | `/api/users/{id}/roles/{role_name}` | `usuarios:gestionar_roles` |

Los paquetes aditivos se **suman** al rol base, nunca lo reemplazan.

---

## 8. Pendiente de este contrato

`openapi_equipos_v1.json` todavia no existe. Se genera del servidor en cuanto los primeros endpoints esten en pie, se congela aqui, y hasta entonces la prueba guardia `test_contrato_openapi.py` (tarea S7) queda en `skip` con el motivo escrito. **Este documento manda mientras tanto.**

Archivos que si estan ya: `permisos_catalogo.json`, `auth_me.json`, `tokens_marca.md`, `fixtures/`.
