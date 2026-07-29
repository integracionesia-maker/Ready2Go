# Backlog — carril servidor y datos (Control de Equipos)

Mis pendientes. No es el backlog del proyecto.

---

## Tareas del reparto

| ID | Tarea | Estado |
|---|---|---|
| S0 | Costura: enum, re-exports, deps | hecho 2026-07-28 |
| S1 | RBAC aditivo (WP1) | hecho 2026-07-28 |
| S2 | Modelo de datos equipos (WP2) | hecho 2026-07-28 |
| S3 | API inventario (WP3) | hecho 2026-07-28 |
| S4 | API prestamos, aprobacion, media (WP4) | hecho 2026-07-28 |
| S5 | Carta responsiva PDF (WP5) | hecho 2026-07-28, falta revision visual de Jose |
| S6 | Correo y recordatorios (WP6) | hecho 2026-07-28 |
| S7 | Guardias de contrato | hecho 2026-07-28 |

## Pendientes sueltos

- **Congelar `openapi_equipos_v1.json`** (§8 del contrato). Ya hay 60 rutas en
  pie. Mientras no exista, la comparacion de `test_contrato_openapi.py` queda en
  `skip` con el motivo escrito — pero esa prueba **si** verifica las 31 rutas de
  las tablas del contrato, asi que el paquete no esta sin red. El comando para
  generarlo esta en el docstring de la prueba.
- **Parchear `.env.example` con las 8 variables SMTP.** §7 del plan lo pide y ese
  archivo esta fuera de mi carril. Documentadas con sus defaults en
  `docs/deploy/recordatorios_launchagent.md`. Sin esa entrada, quien clone el
  repo levanta el backend sin enterarse de que `NOTIF_ENABLED` existe.
- **Confirmar las rutas de interfaz que usan los correos**
  (`/equipos/aprobaciones`, `/equipos/prestamo/{folio}`). Ver R-SRV-15: si no
  coinciden, cada correo enviado lleva un enlace roto y ya no se puede corregir.
- **Aprobar con marketing la redaccion de los cinco correos**
  (`backend/app/plantillas_correo.py`). Son mensajes de cara a personas de GO.
- **Dar modulo propio a las notificaciones en el contrato v2.** Hoy
  `routers/notifications.py` va protegido con `usuarios:gestionar` porque es el
  unico par del catalogo que encaja.
- **Politica de retencion de `notification_log`.** Ver R-SRV-14.
- **`.gitignore` de la raiz ignora `*.db` pero no `*.db-journal` ni `*.db-wal`.**
  Mientras corre la suite aparecen como archivos sin seguimiento y alguien con
  `git add .` los commitearia. `.gitignore` esta fuera de mi carril: hace falta
  ese parche de dos lineas.
- **Revision visual del PDF de la carta responsiva.** Generado con datos reales
  en `backend/uploads/responsivas/CE-0007_v1.pdf` (gitignored; se regenera con
  `python seed_prestamo_demo.py` sobre base limpia). Le toca a Jose, no a mi.
- **Enumerar versiones de la responsiva.** Implemente `?version=n` (esta en el
  plan §5, no en el contrato), pero el payload solo expone la ultima version:
  el cliente no tiene forma de saber que versiones existen. Falta un listado
  (version, generated_at, motivo_regeneracion, sha256) en el contrato v2.
- **Endpoint de regeneracion de la responsiva.** `motivo_regeneracion` existe en
  la tabla y el plan §6 lo pide, pero el contrato v1 no tiene ruta que produzca
  una version nueva. Hoy la unica generacion es la v1 interna de `/confirmar`.
- **Confirmar si el PDF debe incluir las fotos de entrega.** Ni la maqueta ni el
  plan §6 las listan; hoy no van.

## Peticiones a quien coordina (no las decido yo)

- **Agregar `backend/app/errores.py` a mi lista de rutas.** Archivo nuevo, lo
  cree en S1 porque el sobre de error del contrato §0 es transversal. Detalle en
  `docs/avances/servidor.md`, decision 1.
- **Confirmar la forma del cuerpo de los endpoints del contrato §7.** El
  contrato congela ruta, metodo y permiso, no el payload. Elegi una forma
  (`app/schemas_rbac.py`, documentada en `doc/rbac-aditivo.md`). Si el cliente
  ya codifico contra otra, hay que alinear ahora.
- **Decidir si hace falta administrar el catalogo de paquetes por API.** S1
  pedia "CRUD de paquetes"; el contrato v1 §7 solo tiene `GET /api/roles/`.
  Implemente solo el GET. Si hace falta el resto, es contrato v2.
- **Codigo de error para "paquete no asignable".** Hoy reuso `NO_ENCONTRADO`.
  Si el cliente necesita distinguirlo de "usuario no existe", hace falta un
  codigo nuevo en v2.
- **Resolver la contradiccion borrador/reserva entre el plan §4.3 y el contrato
  §3.** Segui el contrato: un borrador con renglones reserva el equipo.
  Consecuencia sin resolver: un borrador abandonado bloquea su equipo para
  siempre. Ver R-SRV-07 en `docs/riesgos/servidor.md`. Hace falta decidir si hay
  caducidad de borradores.
- **`POST/PUT | /api/empresas/{id}` del contrato §6** se lee como taquigrafia.
  Implemente `POST /api/empresas/` + `PUT /api/empresas/{id}`. Confirmar.
- **Sobre de listado inconsistente entre §0 y los fixtures.** `empresas.json` es
  un arreglo pelado, `equipos.json` trae `{items, total}`. Segui los fixtures.
  Confirmar que es intencional.
- **Tres codigos de error fuera de la tabla del contrato §0.** Lista completa,
  para que se decidan de una sola vez en el v2 (o se me diga que use otros):

  | codigo | HTTP | Donde | Por que no alcanzo el contrato |
  |---|---|---|---|
  | `VALOR_INVALIDO` | 422 | condicion/estado fisico fuera de vocabulario, `kind` de media invalido, `decision` invalida, nota obligatoria faltante, `?tamano=` desconocido | §0 no tiene ningun codigo de validacion de cuerpo. El unico 422 de la tabla es `MEDIA_INVALIDA`, definido solo como "archivo que no pasa magic bytes" |
  | `DUPLICADO` | 409 | razon social repetida, codigo de equipo repetido, mismo equipo dos veces en un prestamo | §0 no tiene codigo de conflicto por unicidad |
  | `EQUIPO_NO_DISPONIBLE` | 409 | `POST /items` con un equipo en `revision` o `baja` | `EQUIPO_OCUPADO` diria "ya esta en un prestamo abierto", que es **falso** en ese caso. Un cliente que ramifique por `codigo` mostraria el mensaje equivocado |

  Preferi tres codigos nuevos y honestos antes que reusar uno que miente. Si el
  criterio es no crecer la tabla, digan cual reusar y lo cambio.
- **Confirmar la razon social emisora** (§14.3 del plan). Hoy
  `crud_empresas.emisora_por_defecto()` usa una heuristica ("la primera activa
  con RFC"). Cuando marketing confirme, se vuelve una columna `es_emisora`
  explicita y deja de adivinar.
- **Datos que faltan del inventario:** `fotos_originales_url` (carpeta de Drive
  de la auditoria del 10/06) quedo en NULL para los 8 equipos — no venia en el
  fixture. Tampoco hay camaras, luces ni tripies (§14.2 del plan).
- **CRITICO — cerrar la escritura en prestamos ajenos.** Ver R-SRV-11. El
  contrato pide solo `equipos_prestamos:solicitar` para agregar equipos, subir
  firmas y confirmar: cualquiera del area puede hacerlo sobre el prestamo de
  otro. Necesita decision de contrato antes de tocarlo.
- **`equipos_prestamos:cancelar` no lo concede ningun paquete** del catalogo
  congelado; solo el comodin de `superadmin`. Como un borrador con renglones ya
  reserva sus equipos, un borrador abandonado solo lo puede liberar el
  superadmin. Arreglo natural: sumar `cancelar` a `colaborador_mkt` y/o `admin`
  en `permisos_catalogo.json`, que es contrato.
- **Falta `PUT /api/loans/{id}`.** Sin el, un borrador no se puede editar despues
  de creado: el wizard tiene que mandar los datos del paso 1 en el POST inicial.
  Confirmar si el cliente lo necesita.
- **Confirmar la forma de la fila del listado de prestamos y las columnas del
  CSV.** Ninguna de las dos esta en el contrato. Propuestas en
  `schemas_loans.LoanRow` y `crud_loans.COLUMNAS_CSV`.
- **Corregir dos ejemplos del contrato que contradicen los fixtures:** §3 dice
  `equipment_id: 3` en el prestamo demo y §2 dice `id: 3` para el iPhone gris
  (Jeziel); los fixtures dicen `1` en los dos casos. Implemente segun los
  fixtures, que son el criterio de aceptacion. Va en el mismo v2.
- **Los tres endpoints del §4 llevan segmentos en español** (`/autorizar-entrega`
  y compañia) aunque el §0 diga "rutas en ingles, sin excepcion". Copie las
  cadenas literales del §4. Asentarlo en `CHANGELOG_CONTRATO.md`.

## Dependencias externas que me bloquean (no las resuelvo yo)

- Razon social emisora de la responsiva sin confirmar (§14.3 del plan). El
  fixture `empresas.json` la marca `PENDIENTE`. Bloquea el cierre de S5, no el
  codigo: la razon social sale de la tabla `empresa`, cambiarla es un UPDATE.
- Credenciales SMTP (§14.6 del plan). Bloquean el envio real de S6, no el
  codigo: `NOTIF_ENABLED=false` deja todo probable sin cuenta.
- Correos GO del area de marketing (§14.1). Bloquean el seed de usuarios reales,
  no el codigo.
