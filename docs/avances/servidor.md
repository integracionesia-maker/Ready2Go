# Avances — carril servidor y datos (Control de Equipos)

Una entrada por dia de trabajo. Que hice, evidencia, bloqueos.

---

## 2026-07-28 — S6 Correo y recordatorios (WP6) + S7 Guardias de contrato

Hecho (S6):

- `backend/app/mailer.py` — `smtplib` de la libreria estandar, STARTTLS,
  `NOTIF_ENABLED` como corta-circuito. **Nunca levanta**: devuelve un resultado.
- `backend/app/plantillas_correo.py` — las 5 plantillas de §7, texto plano, sin
  emojis, funciones puras.
- `backend/app/notificaciones.py` — `encolar`, destinatarios por rol desde la
  base, idempotencia, reintentos.
- `backend/app/routers/notifications.py` — diagnostico.
- `backend/scripts/recordatorios_vencimiento.py` — para el LaunchAgent.
- `backend/app/routers/loans.py` y `approvals.py` — enganches en confirmar,
  devolucion y confirmar-devolucion, todos en `BackgroundTasks`.
- `docs/deploy/recordatorios_launchagent.md` — plist, las 8 variables de entorno
  y el arbol de diagnostico de "no llegan los correos".
- `backend/tests/equipos/test_notificaciones.py` — 35 pruebas.

Hecho (S7):

- `backend/tests/test_contrato_openapi.py` — 37 pruebas.
- `backend/tests/equipos/test_fixture_demo.py` — 10 pruebas.

Evidencia:

```
$ python -m pytest tests -q --ignore=tests/equipos --ignore=tests/rbac
205 passed, 1 skipped        (169 existentes + 37 de la guardia de contrato)

$ python -m pytest tests/rbac -q
80 passed

$ python -m pytest tests/equipos -q
315 passed, 1 skipped
```

**600 passed, 2 skipped** sobre 602 recolectadas. Las 169 existentes siguen
verdes con todo el modulo encima.

En tres bloques y no en una corrida: la suite completa tarda ~15 minutos y las
tareas de fondo de esta sesion se cortaban antes de terminar. Cada bloque recrea
la base por prueba, asi que la cobertura es la misma.

**La suite de este repo no se puede correr en paralelo consigo misma**: todos los
bloques usan `tests/test_auth.db`. Lo aprendi lanzando un spot-check mientras
corria la suite completa y contaminando las dos. Anotado por si alguien intenta
paralelizarla con `-n`.

Corrida real del recordatorio sobre base limpia, dos veces el mismo dia:

```
$ python scripts/recordatorios_vencimiento.py     # x2
  - CE-0007: 8 dia(s) de atraso, 2 aviso(s) por mandar
filas en notification_log: 2      <- no 4
  vencimiento:2026-07-28 -> ana.ruiz@grupo-ortiz.com
  vencimiento:2026-07-28 -> melisa.avendano@grupo-ortiz.com
```

Destinatarios resueltos desde la base, sin el superadmin.

Criterios de cierre:

| Criterio | Prueba | Estado |
|---|---|---|
| Reintentar no duplica correos | `test_encolar_dos_veces_no_duplica`, `test_lo_ya_enviado_no_se_vuelve_a_encolar`, `test_confirmar_dos_veces_no_manda_el_correo_dos_veces` | verde |
| SMTP caido no tumba el registro del prestamo | `test_smtp_caido_no_tumba_el_registro_del_prestamo` — el prestamo queda `prestado`, con folio y responsiva v1, y la notificacion en `fallido` con su motivo | verde |
| `GET /api/loans/{id}` del demo identico al fixture | `test_el_payload_es_identico_al_fixture` — por HTTP, campo por campo | verde |
| Guardia de OpenAPI | `test_contrato_openapi.py` — la comparacion contra el JSON congelado en `skip` con motivo escrito; las 31 rutas de las tablas del contrato si se verifican | verde |

### La colision que hubo que resolver: recordatorio diario contra el UNIQUE

`notification_log` tiene `UNIQUE (loan_id, tipo, destinatario)`, que es lo que
hace que reintentar no duplique el aviso a la aprobadora. Pero §7 pide que el
recordatorio de vencimiento sea **diario**.

Con un `tipo` constante, las dos cosas se pelean y gana la peor: el primer dia
inserta la fila y **todos los dias siguientes chocan con el UNIQUE, se leen como
"ya enviado" y no sale nada**. Sin error, sin log, sin que nadie lo note. El
recordatorio diario se mandaria una sola vez en la vida del prestamo.

Solucion: el tipo lleva el dia civil de CDMX — `vencimiento:2026-07-30`. El
UNIQUE pasa a significar "un aviso por prestamo, por destinatario, **por dia**",
que es exactamente lo que pide §7, y sigue bloqueando la doble corrida del mismo
dia (LaunchAgent disparando al despertar la Mac, o alguien corriendo el script a
mano). El dia sale de `tz.hoy()`, jamas de UTC: despues de las 18:00 CDMX el UTC
ya es el dia siguiente y saldrian dos avisos para el mismo dia civil.

Descartadas: cambiar el UNIQUE (exige migracion y contradice §7), reusar una sola
fila subiendo `intentos` (pierde la historia), y mandar el aviso una sola vez
(contradice §7 en la otra direccion).

Consecuencia a vigilar: `notification_log` crece una fila por prestamo vencido,
por destinatario, por dia. Falta politica de retencion — anotado en el backlog.

### Decisiones

**AI. `routers/notifications.py` esta fuera del contrato.** El contrato v1 no
define ningun endpoint de notificaciones y `permisos_catalogo.json` no tiene un
modulo para ellas. Existe porque la asignacion lo pide de forma explicita en S6 y
la asignacion manda sobre el plan. Protegido con `usuarios:gestionar` —el unico
par del catalogo que encaja, hoy solo del `superadmin`—. Son de diagnostico: no
cambian ningun payload y ningun cliente del contrato los llama. **Hay que darles
su modulo propio en el contrato v2.**

**AJ. `GET /api/notifications/config` jamas devuelve `SMTP_PASSWORD`,** solo si
esta configurada. Y expone `aprobadores_resueltos`, que es el dato mas dificil de
descubrir cuando "no llegan los correos".

**AK. En `RBAC_MODO=legacy` no hay aprobadores y ningun aviso sale.** Los
aditivos no aplican y `equipos_aprobacion` solo lo concede `APROBADOR_EQUIPO`. La
lista vacia se escribe en el log como advertencia, con el modo incluido: escribir
un correo de respaldo en el codigo seria volver al hardcode que §10.20 prohibe.
Ver R-SRV-13.

**AL. Texto plano, no HTML.** Ninguna fuente lo define. Sin CSP que pelear, sin
imagenes remotas que se bloqueen, legible en cualquier cliente. Si marketing
quiere HTML es decision de marca.

**AM. Se notifica a quien tiene el permiso, no a `entregado_por`.** La maqueta
mandaba el correo a quien figuraba como "quien entrega", buscado en una constante
`APPROVERS`. Si `entregado_por` es alguien sin el aditivo, no recibe el correo —
correcto, porque tampoco puede autorizar.

**AN. Las rutas de los enlaces del correo son propuesta.** `APP_PUBLIC_URL` da el
origen, pero `/equipos/aprobaciones` y `/equipos/prestamo/{folio}` no estan en
ninguna fuente: el contrato solo define rutas de `/api/*`. **Sin acuerdo con
quien construye la interfaz, los correos apuntan a paginas que dan 404.**

**AO. La guardia de OpenAPI no se quedo en un `skip` pelado.** El JSON congelado
no existe (§8 del contrato lo dice), asi que esa comparacion esta en `skip` con
el motivo escrito. Pero mientras tanto la prueba verifica lo que **si** esta
congelado en `API_EQUIPOS_v1.md`: que las 31 rutas y metodos de sus tablas
existan con el nombre exacto, que `/dashboard`, `/export` y `/by-folio` no los
absorba la ruta por id, que no haya mount estatico, y que `permisos` siga en
`UserResponse`. Un `skip` solo habria dejado el paquete sin red durante semanas.

**AP. `freeze_time` no se puede usar alrededor de una peticion HTTP.** Freezegun
sustituye `datetime.date` por su propia clase y FastAPI deja de poder analizar los
parametros de fecha de otras rutas ("Invalid args for response field"). La guardia
del fixture fija la fecha parcheando `tz.hoy`, que es lo unico que el calculo de
atraso consulta. Vale para cualquiera que agregue pruebas con reloj congelado.

### Pendientes que no puedo cerrar yo

- **`.env.example` no lo puedo tocar** (esta en la lista fuera de mi carril) y §7
  pide que las 8 variables SMTP entren ahi con placeholders. Documentadas en
  `docs/deploy/recordatorios_launchagent.md`; **hace falta ese parche de la raiz**.
- **Congelar `openapi_equipos_v1.json`.** Ya hay 60 rutas en pie; el comando esta
  en el docstring de `test_contrato_openapi.py`.
- **Aprobar la redaccion de los cinco correos** con marketing: son mensajes de
  cara a personas de Grupo Ortiz.

Bloqueos: ninguno para el codigo. Envio real a una cuenta de prueba pendiente de
credenciales SMTP (§14.6 del plan).

---

## 2026-07-28 — S5 Carta responsiva en PDF (WP5)

Hecho:

- `backend/app/pdf/estilos.py` — tokens de marca de `docs/contratos/tokens_marca.md`.
- `backend/app/pdf/plantilla.py` — estructura del documento y **el texto legal
  literal** de la maqueta. No toca la base: recibe un diccionario.
- `backend/app/pdf/responsiva.py` — reune los datos, escribe el archivo,
  devuelve el sha256.
- `backend/app/routers/responsivas.py` — `GET /api/loans/{id}/responsiva.pdf`.
- `backend/app/main.py` — su include_router.
- `backend/requirements-dev.txt` — `pypdf` (leer el PDF en las pruebas).
- `backend/tests/equipos/test_responsiva_pdf.py` — 27 pruebas.

Criterios de cierre de S5:

| Criterio | Prueba | Estado |
|---|---|---|
| La version 2 no pisa la 1 | `test_la_version_2_no_pisa_la_1` — compara bytes y sha256 de la v1 antes y despues | verde |
| PDF generado con datos reales para revision visual | `backend/uploads/responsivas/CE-0007_v1.pdf`, generado del prestamo demo | hecho |

### El PDF de revision

Generado con `seed_prestamo_demo.py` sobre base limpia. Una hoja, folio CE-0007,
emisora tomada de la tabla `empresa`, los 5 puntos de Situaciones
extraordinarias literales, y las dos firmas con sus leyendas.

**Falta que Jose lo revise a ojo** — esa parte no la puedo cerrar yo. El archivo
esta en `backend/uploads/responsivas/CE-0007_v1.pdf` (gitignored; se regenera
con `python seed_prestamo_demo.py` sobre base limpia).

### Lo que encontre generandolo

**El bloque de firmas se caia solo a la hoja 2.** Con los margenes iniciales
(22/18 mm), una responsiva de **un solo equipo** terminaba con la hoja 1 llena de
texto legal y las dos firmas solas en la hoja 2. Es la peor forma de imprimir una
carta responsiva: nadie sabe si esa hoja 2 pertenece a esa hoja 1. Ajustados
margenes (20/14 mm), alto de firma (14 mm) y el espacio previo (7 mm): el caso
comun cabe en una hoja. Hay prueba que lo afirma.

### Decisiones

**AB. La emisora sale de la tabla y si no hay, no se confirma.** El generador
levanta `EmisoraNoConfigurada` y `POST /confirmar` falla. Es deliberado: no se
entrega equipo sin carta responsiva, y un encabezado a medias en un documento que
alguien firma es peor que no generarlo. Consecuencia operativa: **hay que sembrar
`empresa` antes de poder confirmar el primer prestamo** (`seed_equipos.py` lo
hace). §14.3 del plan ya declaraba esto como dependencia que bloquea WP5.

**AC. La condicion del equipo se congela contra la auditoria vigente a la fecha
de entrega**, no contra la ultima del catalogo. Si no, la v2 de una carta ya
firmada diria una condicion distinta de la v1 sobre los mismos hechos. Limitacion
conocida: no hay columna donde guardar el texto que salio impreso en cada
version; mientras nadie retro-feche una auditoria, dos versiones dicen lo mismo.

**AD. Implemente `?version=` aunque no este en el contrato.** Esta en el plan §5
y es puramente aditivo: no cambia ningun payload y el default sigue siendo la
ultima version. Sin el, el versionado que la base ya sostiene no tiene forma de
consultarse. Reportado para v2, junto con la falta de una forma de **enumerar**
versiones (`responsiva: {version, url}` solo expone la ultima).

**AE. Etiquetas legibles de `cargador_con`.** El PDF no puede imprimir el token
crudo (`responsable`) porque en la carta se lee como una palabra suelta. El mapa
esta en `plantilla.ETIQUETAS_CARGADOR`; el contrato no publica esas etiquetas.

**AF. Pie tecnico con folio, version y fecha de generacion.** No afirma validez
legal —§6 lo prohibe explicito y hay prueba que lo verifica— pero sin marca de
version no hay forma de distinguir dos impresiones del mismo folio.

**AG. Fuentes de respaldo.** Blauer Nue y Conthic son dependencia de WP7 y no
estan en el repo. Se usan Helvetica y Courier, que `tokens_marca.md` autoriza
como respaldo. Queda escrito en `estilos.py`, no elegido en silencio.

**AH. Escapado de XML.** `Paragraph` de reportlab interpreta un subconjunto de
XML: un nombre de equipo con `&` o `<` rompe el documento entero. Hay prueba con
`Camara <A&B>` y marca `R&D`.

### No implementado

- **No hay endpoint de regeneracion.** El contrato v1 no lo tiene, aunque
  `motivo_regeneracion` existe en la tabla y el plan §6 lo pide. Hoy la unica
  generacion es la v1 interna de `POST /confirmar`;
  `crud_loans.generar_responsiva` esta lista para cuando exista la ruta.
- **El PDF no incluye las fotos de entrega.** Ni la maqueta ni el plan §6 las
  listan en el contenido. Conviene confirmarlo con marketing.

Bloqueos: la revision visual de Jose.

---

## 2026-07-28 — S4 API de prestamos, aprobacion y media (WP4)

Hecho:

- `backend/app/loan_state.py` — maquina de estados aislada y pura: no importa
  base de datos ni FastAPI, se prueba sin levantar la app.
- `backend/app/media_manager.py` — magic bytes, 3 MB / 250 KB, sha256,
  miniatura de 96px, reemplazo, `uploads/equipos/`.
- `backend/app/schemas_loans.py`, `crud_loans.py`.
- `backend/app/routers/loans.py` — alta, listado, ficha, by-folio, items, media,
  confirmar, cancelar, devolucion, export CSV.
- `backend/app/routers/approvals.py` — los tres endpoints del §4.
- `backend/app/routers/media.py` — `GET /api/media/{id}` con `?tamano=thumb`.
- `backend/tests/equipos/` — `test_loan_state.py` (47 + 1 skip),
  `test_api_prestamos.py` (41), `test_media.py` (34), `test_aprobacion.py` (25).

Evidencia:

```
$ python -m pytest -q
492 passed, 1 skipped, 1 warning in 503.30s (0:08:23)
```

169 existentes + 323 nuevas. La saltada es un caso parametrizado de la maquina de
estados cuyo destino depende de las decisiones y se cubre en pruebas aparte.

Criterios de cierre de S4:

| Criterio | Prueba | Estado |
|---|---|---|
| Maquina de estados completa **incluidas las transiciones invalidas** | `test_loan_state.py`: 6 estados x 5 acciones = 30 pares, 5 validos y **25 invalidos**, ninguno sin cubrir | verde |
| Un usuario no descarga media de un prestamo ajeno (403) | `test_un_extrano_no_descarga_media_de_un_prestamo_ajeno` | verde |

### La lentitud que resulto ser un bug de las pruebas

`test_aprobacion.py` tardo **2 horas 27 minutos** en su primera corrida, con un
fallo que no se reproducia. Causa: las pruebas escribian los archivos de media en
`backend/uploads/equipos/`, que vive dentro del repo y por lo tanto dentro de la
carpeta sincronizada con Drive. Cada archivo disparaba una sincronizacion; con
348 archivos acumulados la contencion de disco hacia que alguna peticion
devolviera error en vez del payload.

Arreglo: fixture autouse que apunta los directorios de media y responsivas a un
temporal. **48 segundos** y el fallo desaparecio. De paso, la suite ya no deja
basura en el arbol de trabajo. Vale para cualquiera que agregue pruebas de
archivos en este repo.

### Decisiones sobre lo que el contrato no define

**P. "Participante" no esta definido en el contrato**, y se usa cuatro veces
(§3 y §5). Adopte: el id de la sesion aparece en `responsable_user_id`,
`entregado_por_user_id`, `created_by_user_id`, `entrega_autorizada_por_user_id` o
`confirmada_por_user_id`. Es un conjunto que **crece**: quien autoriza entra al
autorizar. Consecuencia verificada en prueba: la aprobadora **no** es
participante antes de autorizar, asi que entra por `ver_global` — que su paquete
aditivo si le da. Sin eso no podria ver lo que tiene que aprobar.

**Q. 403 vs 404.** Prestamo inexistente o borrado: 404. Prestamo que existe y no
es suyo: 403. Riesgo aceptado y declarado: el 403 confirma que ese id existe.

**R. `POST /devolucion` NO escribe `devuelto_at`; `cancelar` y
`confirmar-devolucion` SI.** Es la consecuencia dura de que la disponibilidad se
derive del renglon abierto. Si `/devolucion` lo escribiera, el equipo se
ofreceria como disponible antes de que el aprobador lo revise, y uno marcado
`no_devuelto` (perdido) volveria a ser prestable. Lo que retiene a un equipo con
incidencia es `estado_operativo='revision'`, no el renglon.

**S. Todo `ok` sin autorizacion de entrega → 409 antes de escribir nada.** §4
dice "todas ok -> completado" sin condicion; §3 dice que sin autorizacion no se
llega a `completado`. Manda §3. Las alternativas son peores: guardar las
decisiones y quedarse en `pendiente_confirmacion` con 200 es un exito falso —el
cliente pinta "confirmado" y el prestamo no cerro—; degradar a `incompleto`
dispara "requiere atencion" y el correo de incidencias cuando no hubo ninguna, y
su unica salida esta bloqueada por la misma guarda. La guarda se evalua contra el
estado **destino**: con alguna incidencia el destino es `incompleto` y la
operacion procede sin autorizacion, que es lo que evita el punto muerto.

**T. `autorizar-entrega` se acepta desde `prestado`, `pendiente_confirmacion` e
`incompleto`.** Que `incompleto` entre es lo menos obvio y lo mas importante: sin
eso, un prestamo que llego a incompleto sin autorizacion no se podria cerrar
nunca. Idempotente.

**U. Confirmar exige al menos un equipo.** El contrato no pone minimo, asi que
"2 fotos por equipo" se cumple de forma vacia con cero equipos: se confirmaria un
prestamo sin nada, quemando un folio y generando una responsiva en blanco. La
maqueta si lo exigia ("Selecciona al menos un equipo").

**V. La media solo se sube en el estado que corresponde:** entrega y firmas en
`borrador`, devolucion en `prestado`. El contrato no lo dice. Se aplica porque no
hay flujo legitimo que suba una foto de entrega a un prestamo completado, y
permitirlo deja reescribir la evidencia detras de una responsiva firmada.

**W. Re-subir el mismo `kind` reemplaza** (borra fila y archivo anterior). El
payload expone un solo id por kind, asi que dos filas no tienen representacion, y
"Cambiar foto" es flujo normal en la maqueta.

**X. Se cuentan kinds distintos, no filas,** al validar `/confirmar`. Con
`COUNT(*) = 2` un renglon con dos fotos de frente y cero de atras pasaria: el
indice de media no es unico y la base lo permite.

**Y. Forma de la fila del listado y columnas del CSV.** El contrato define la
ficha pero **nunca** la fila del listado (§3), ni columnas, separador o
codificacion del CSV. Ambas propuestas estan en `schemas_loans.LoanRow` y
`crud_loans.COLUMNAS_CSV` (18 columnas, BOM para que Excel no destroce acentos).
Hay que confirmarlas con el cliente.

**Z. Atraso de un prestamo ya cerrado.** Comparar contra hoy diria "atrasado 90
dias" de algo cerrado hace tres meses. Se compara contra `fecha_regreso_real`; si
el estado es terminal y no hay fecha real, no hay atraso.

**AA. Codigos nuevos fuera del §0:** `EQUIPO_NO_DISPONIBLE` (409, equipo en
revision o baja — `EQUIPO_OCUPADO` diria algo falso) y `VALOR_INVALIDO` (422,
vocabulario o cuerpo mal formado), que ya venia de S3.

### Lo que NO implemente por no improvisar

- **No hay `PUT /api/loans/{id}`.** El contrato no lo tiene. Consecuencia real:
  un borrador no se puede editar despues de creado — el wizard tiene que mandar
  los datos del paso 1 en el `POST /api/loans/`. Si el cliente necesita editar,
  es cambio de contrato. `crud_loans.actualizar` esta escrito y sin exponer,
  esperando esa decision.
- **No hay `?version=` en la responsiva** (el plan §5 lo menciona, el contrato
  no) ni endpoint para regenerarla.
- **No hay endpoint de borrado de prestamo**, aunque `loan.is_deleted` existe en
  el modelo y la formula de disponibilidad lo filtra. O sobra la columna o falta
  el endpoint.
- **No agregue la validacion de participacion en las escrituras.** El contrato
  pide solo el permiso `equipos_prestamos:solicitar` para `POST /items`,
  `POST /media` y `/confirmar`. Tal cual esta escrito, **cualquier
  `colaborador_mkt` puede agregar equipos, subir firmas y confirmar el borrador
  de otra persona.** Es la misma clase de agujero que §10.4. No lo cerre por
  cuenta propia porque endurecer de un solo lado rompe al cliente: ver R-SRV-11.

Bloqueos: ninguno.

---

## 2026-07-28 — S3 API de inventario (WP3)

Hecho:

- `backend/app/schemas_equipment.py`, `crud_equipment.py`,
  `crud_dashboard_equipos.py`.
- `backend/app/routers/equipment.py` — listado con `q`/`categoria`/`condicion`/
  `disponible`/`limit`/`offset`, ficha con auditorias e historial, alta,
  edicion, `POST /auditoria`, `POST /baja`.
- `backend/app/routers/equipos_dashboard.py` — `GET /api/equipment/dashboard`.
- `backend/app/main.py` — los dos include_router, dashboard **antes** de
  inventario.
- `backend/tests/equipos/test_api_inventario.py` — 31 pruebas.

Evidencia:

```
$ python -m pytest -q
345 passed, 1 warning in 385.75s      (169 existentes + 176 nuevas)
```

Criterios de cierre de S3:

| Criterio | Prueba | Estado |
|---|---|---|
| Pruebas de permisos (403) | 4 pruebas de permisos por rol y por aditivo | verde |
| Conflicto 409 en baja con prestamo abierto | `test_baja_de_equipo_con_prestamo_abierto_es_409` | verde |
| `/dashboard` antes de `/{id:int}` | `test_el_dashboard_no_lo_traga_la_ruta_por_id` + `test_el_dashboard_existe_como_ruta_propia_en_el_esquema` | verde |
| `POST /auditoria` registra en `equipment_audit` | `test_la_auditoria_agrega_al_historial_sin_pisar_la_anterior` | verde |

La fila del listado se compara **campo por campo** contra
`docs/contratos/fixtures/equipos.json` para los 7 equipos libres
(`test_la_fila_del_listado_tiene_la_forma_del_fixture`). El equipo 1 tiene su
propia prueba porque en el fixture aparece con prestamo abierto.

### Dos defensas para el mismo error del enrutador

El contrato advierte que `/dashboard` se lo traga `/{id}` si va despues. Puse
las dos: el dashboard es un router aparte incluido primero, **y** las rutas por
id usan `{equipment_id:int}`. Cualquiera de las dos basta; las dos juntas
aguantan que alguien mueva el orden de los `include_router` o quite el `:int`
para aceptar codigos de equipo.

### Decisiones que el contrato no fija

**I. La fila del listado trae mas campos que el ejemplo del §2.** El ejemplo del
contrato omite `condicion`, `estado_fisico`, `comentario_auditoria` y
`fecha_auditoria`, pero `fixtures/equipos.json` **si** los trae. Segui el
fixture: quitar campos que el fixture tiene rompe a un cliente que mockee contra
el; agregarlos no rompe a nadie.

**J. La forma de la ficha (`GET /api/equipment/{id}`) no esta congelada.** El
contrato fija ruta y permiso. Devuelvo la fila del listado + `descripcion`,
`fotos_originales_url`, `auditorias[]` e `historial[]`. Documentado en
`app/schemas_equipment.py`.

**K. `por_estado` del dashboard devuelve siempre las 6 llaves**, con 0 donde no
hay nada. El ejemplo del contrato muestra 4 —justo las que tenian datos—. Un
mapa de llaves variables hace que una grafica de distribucion cambie de forma
sola cuando se cierra el ultimo prestamo de un estado.

**L. Definiciones de los contadores del dashboard.** El contrato da los nombres,
no la definicion. `prestados` = estado `prestado` (no incluye
`pendiente_confirmacion`, que tiene su propio contador). `atrasados` = en
`prestado` con fecha vencida; un prestamo ya devuelto y esperando confirmacion
no cuenta como atrasado, el equipo ya volvio. Escritas en el docstring de
`crud_dashboard_equipos.py`.

**M. `POST /baja` es borrado logico completo**, como pide el plan §5: pone
`estado_operativo='baja'` **y** `is_deleted=True`. Consecuencia: el equipo
desaparece del listado y su ficha responde 404. El registro, sus auditorias y su
historial se conservan en la base. Ver R-SRV-10: si el area necesita consultar la
ficha de un equipo retirado, esto hay que cambiarlo.

**N. `estado_operativo` no es editable por `PUT /api/equipment/{id}`.** Se mueve
solo por sus endpoints (`/baja`, confirmacion de devolucion, cierre de
incidencia). Dejarlo editable permitiria sacar un equipo de `revision` sin
cerrar la incidencia, que es justo el hueco que `cerrar-incidencia` tapa.

**O. Codigo `VALOR_INVALIDO` (422)** para condicion o estado fisico fuera del
vocabulario, y `DUPLICADO` (409) para codigo de equipo repetido. Ninguno esta en
la tabla del contrato §0.

Bloqueos: ninguno.

---

## 2026-07-28 — S2 Modelo de datos de Equipos (WP2)

Hecho:

- `backend/app/models_equipos.py` — las 10 tablas del plan §4.1 + el indice
  unico parcial `ux_loan_item_equipo_abierto` + los vocabularios.
- `backend/app/disponibilidad.py` — formula derivada. No existe
  `equipment.estado = 'prestado'`.
- `backend/app/folio.py` — `CE-0001` transaccional, 3 reintentos.
- `backend/app/tz.py` — America/Mexico_City como zona unica.
- `backend/app/schemas_empresas.py`, `crud_empresas.py`, `routers/empresas.py`.
- `backend/migrate_equipos.py` — idempotente, con precondicion y verificacion
  del indice.
- `backend/seed_equipos.py` — 8 equipos de la auditoria del 10/06/2026 + 3
  razones sociales.
- `backend/seed_prestamo_demo.py` — el prestamo del fixture, con ids fijos y
  archivos de media reales.
- `backend/requirements.txt` — `tzdata`.
- `backend/tests/equipos/` — 65 pruebas.

Evidencia:

```
$ python -m pytest -q
314 passed, 1 warning in 347.66s      (169 existentes + 80 rbac + 65 equipos)
```

Migraciones y seeds de punta a punta sobre una base **limpia** (no la de
desarrollo), corriendo cada script en su propio proceso:

```
seed_auth.py -> migrate_rbac_aditivo.py -> migrate_equipos.py
             -> seed_rbac.py -> seed_equipos.py -> seed_prestamo_demo.py

corrida 1: 10 tablas creadas, indice parcial verificado, 8 equipos,
           3 empresas, prestamo CE-0007 con 4 archivos de media
corrida 2: 0 altas en todo
```

Esa secuencia esta como prueba (`test_la_secuencia_completa_corre_dos_veces_seguidas`),
no solo como corrida manual.

Criterios de cierre de S2:

| Criterio | Prueba | Estado |
|---|---|---|
| Un equipo no puede quedar en dos prestamos abiertos | `test_un_equipo_no_puede_estar_en_dos_prestamos_abiertos` | verde |
| Folio bajo concurrencia no duplica | `test_concurrencia_real_no_produce_folios_repetidos` (6 hilos, sesiones propias) + 3 pruebas de colision determinista | verde |
| Migracion idempotente | `test_la_secuencia_completa_corre_dos_veces_seguidas` | verde |

### Lo que encontre trabajando

**1. El folio se atoraba en el mismo numero al reintentar.** El incremento del
contador estaba **dentro** del SAVEPOINT, asi que el rollback del choque tambien
deshacia el `UPDATE`: los tres reintentos pedian exactamente el mismo numero y
fallaban igual. Movido fuera del savepoint. Lo encontro la prueba de contador
atrasado, no la lectura del codigo.

**2. Tres scripts no arrancaban solos.** `migrate_equipos.py`, `seed_equipos.py`
y `migrate_rbac_aditivo.py` importaban solo los modelos que usaban, sin
`app.models`. Dentro de la suite pasaban —`conftest` ya cargo `app.main` y con
el todos los modelos— y reventaban al ejecutarse de verdad. Por eso ahora hay
una prueba que corre **cada script en un proceso propio**: es la unica que ve
este error.

**3. SQLite crea tablas con FK a tablas que no existen.** Corrida sobre una base
sin `users`, la migracion "funcionaba" y dejaba llaves foraneas apuntando a la
nada; el error salia mucho despues, en el primer INSERT, con un
"no such table: users" que no dice que falto un paso. Las dos migraciones ahora
verifican la precondicion y mandan a `seed_auth.py`.

**4. El indice parcial puede existir mal.** `create_all` no reemplaza un indice
que ya existe con otra definicion. Si una base vieja tuviera
`ux_loan_item_equipo_abierto` **sin** el `WHERE devuelto_at IS NULL`, seria un
unique total sobre `equipment_id`: el equipo no se podria prestar dos veces
nunca. No se nota hasta el segundo prestamo del mismo equipo. La migracion ahora
lee el SQL del indice y falla si no es parcial.

**5. `tzdata` no estaba declarada.** En Windows `zoneinfo` no trae la base IANA;
estaba instalada de transitiva. Un entorno limpio se habria quedado sin zona y
el calculo de atraso —la razon de ser de `tz.py`— habria reventado. Declarada en
`requirements.txt`.

### Contradiccion entre el plan y el contrato (decidida, no improvisada)

**El plan §4.3 dice "un borrador no reserva el equipo" y que los renglones se
insertan al confirmar. El contrato §3 expone `POST /api/loans/{id}/items` sobre
un borrador y exige `409 EQUIPO_OCUPADO` "si el equipo ya esta en otro prestamo
abierto", con el indice unico como arbitro.** Las dos cosas no pueden ser
ciertas: si los renglones existen desde el borrador, reservan.

Segui el **contrato**: esta congelado y hay codigo construyendose contra el.
Consecuencia: un borrador con renglones marca el equipo como no disponible.

Consecuencia operativa que hay que decidir arriba: **un borrador abandonado
bloquea su equipo indefinidamente.** No hay caducidad de borradores en el
contrato. Anotado como riesgo R-SRV-07.

Ademas, la formula de disponibilidad que implemente es la del **contrato §2**
("sin renglon de prestamo abierto"), no la del plan §4.2 (que enumera
`loan.estado IN ('prestado','pendiente_confirmacion')`). Razon: la del contrato
coincide exactamente con la condicion del indice unico. Si la formula fuera mas
laxa que el indice, la pantalla mostraria disponible un equipo que da 409 al
pedirlo.

### Otros huecos de contrato

**E. `POST/PUT | /api/empresas/{id}` (§6).** Un POST a un id que no existe no
tiene sentido. Lo lei como taquigrafia de "los dos verbos de escritura":
`POST /api/empresas/` crea, `PUT /api/empresas/{id}` edita.

**F. Sobre de listado inconsistente.** §0 dice que los listados responden
`{items, total}`, pero `fixtures/empresas.json` es un arreglo pelado mientras
`fixtures/equipos.json` si trae el sobre. Segui los fixtures: empresas devuelve
arreglo, inventario devolvera sobre. Un cliente que mockee contra
`empresas.json` se rompe con el sobre.

**G. No hay codigo de error para razon social duplicada.** Uso 409 con
`codigo: "DUPLICADO"`, que no esta en la tabla del §0. Mantengo la forma del
sobre; el codigo es nuevo. Si molesta, va a v2.

**H. `GET /api/empresas/` pide solo sesion, no `usuarios:gestionar`.** El
contrato dice "autenticado" para GET y `usuarios:gestionar` para escritura; lo
implemente asi. Lo mismo tiene sentido operativo: el wizard de prestamo necesita
la lista para llenar un `<select>` y solo el superadmin tiene `usuarios:*`.

### Nota sobre el seed demo en la base de desarrollo

`seed_prestamo_demo.py` se detiene en `presupuesto.db` porque `melisa` ya existe
con id 2 y el fixture del contrato la fija en id 4. **Es el comportamiento
correcto**: reasignar el id de una cuenta existente para cuadrar un fixture es
peor que no sembrar. El seed corre limpio en base nueva, que es donde importa
(la guardia de contrato de S7 usa la base de pruebas). Anotado como R-SRV-08.

Bloqueos: ninguno.

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
