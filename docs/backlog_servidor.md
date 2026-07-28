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
| S4 | API prestamos, aprobacion, media (WP4) | pendiente |
| S5 | Carta responsiva PDF (WP5) | pendiente |
| S6 | Correo y recordatorios (WP6) | pendiente |
| S7 | Guardias de contrato | pendiente |

## Pendientes sueltos

- `openapi_equipos_v1.json` no existe todavia (§8 del contrato). La guardia
  `test_contrato_openapi.py` de S7 queda en `skip` con motivo escrito hasta que
  se congele. Hay que pedir que se genere y congele en cuanto S3-S6 esten en pie.
- Subir el piso de `reportlab` en `requirements.txt` a la version exacta contra
  la que compile el PDF de S5. Hoy dice `>=4.2.0` y `pip` instalo 5.0.0. Ver
  R-SRV-02 en `docs/riesgos/servidor.md`.

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
- **Codigo `DUPLICADO` (409) para razon social repetida** no esta en la tabla
  del contrato §0. Confirmar o cambiar en v2.
- **Confirmar la razon social emisora** (§14.3 del plan). Hoy
  `crud_empresas.emisora_por_defecto()` usa una heuristica ("la primera activa
  con RFC"). Cuando marketing confirme, se vuelve una columna `es_emisora`
  explicita y deja de adivinar.
- **Datos que faltan del inventario:** `fotos_originales_url` (carpeta de Drive
  de la auditoria del 10/06) quedo en NULL para los 8 equipos — no venia en el
  fixture. Tampoco hay camaras, luces ni tripies (§14.2 del plan).

## Dependencias externas que me bloquean (no las resuelvo yo)

- Razon social emisora de la responsiva sin confirmar (§14.3 del plan). El
  fixture `empresas.json` la marca `PENDIENTE`. Bloquea el cierre de S5, no el
  codigo: la razon social sale de la tabla `empresa`, cambiarla es un UPDATE.
- Credenciales SMTP (§14.6 del plan). Bloquean el envio real de S6, no el
  codigo: `NOTIF_ENABLED=false` deja todo probable sin cuenta.
- Correos GO del area de marketing (§14.1). Bloquean el seed de usuarios reales,
  no el codigo.
