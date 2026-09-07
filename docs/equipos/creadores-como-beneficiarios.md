# Creadores como beneficiarios de Equipos (I9)

> Feature de Control de Equipos, construida con luz verde explícita de Jose (07/09/2026). Complementa `docs/equipos/plan-quirurgico.md` §3.4 (RBAC aditivo) y `docs/equipos/firma-pendiente-al-confirmar.md` (firmas).

## Por qué existe

Los beneficiarios reales de un préstamo de equipo son, en la práctica, los mismos creadores de contenido de Presupuestos — la misma persona que ya tiene cuenta en GOCreate para subir sus tickets. Hasta este cambio, el rol base `creador` no tenía **ningún** acceso a Equipos, y el formulario de préstamo pedía el nombre/correo del beneficiario a mano (texto libre) porque se asumía que podía no tener cuenta en el sistema.

Esto generaba dos problemas: (1) un creador no podía entrar a Equipos para pedir ni consultar sus propios préstamos, y (2) quien llenaba el formulario por él tenía que escribir su nombre/correo a mano en vez de simplemente elegirlo — con el riesgo de errores de captura y sin ningún vínculo real con su cuenta.

## La regla

- **El rol base `creador` gana acceso a Equipos**, con el mismo set de permisos que ya tenía `colaborador_mkt` (`rbac_catalog.py`): `equipos_inventario:ver` + `equipos_prestamos:{solicitar, ver_propios, registrar_devolucion}`. Aplica automáticamente a todo creador (actual y futuro) en cuanto corre `migrate_rbac_aditivo.py` — no hay que asignar nada por persona.
- **Nunca `equipos_aprobacion`** ni el resto de `equipos_inventario` (`crear`/`editar`/`auditar_condicion`/`dar_de_baja`) — un creador ve el inventario pero no lo administra, y no puede autorizar entregas, confirmar devoluciones ni cerrar incidencias.
- **`ver_propios` ya filtraba por `responsable_user_id`** (quién es el beneficiario), no por quién llenó el formulario — no hizo falta tocar esa lógica: un préstamo que otra persona arma para un creador (eligiéndolo del selector) ya aparece en el Historial de ese creador sin cambios adicionales.
- **Un creador siempre es su propio beneficiario.** El formulario de préstamo (`/equipos/nuevo`) no le muestra ningún selector ni campo de beneficiario — se autoasigna con su propio nombre/correo, de solo lectura. Esto se refuerza también en el servidor (`crud_loans.crear()`): si la sesión es de un `creador`, el `responsable_user_id`/`nombre`/`email` que mande el cliente se ignoran y se fuerza al de la propia sesión — no es solo una restricción de interfaz, una llamada directa a la API tampoco puede ponerlo a nombre de otro creador.
- **Cualquier otro rol elige un beneficiario de una lista de creadores** en vez de escribirlo a mano — con una opción "Otro (no es creador)" que conserva el texto libre original, por si el beneficiario de verdad no tiene cuenta en GOCreate (el caso real que motivó el diseño original).

## El selector de beneficiario

- **Fuente de datos: `GET /api/creators/`**, extendido con dos campos nuevos en `CreatorResponse` — `user_id` y `email` — resueltos en `crud.creator_to_response()` buscando el `User` vinculado (`User.creator_id == creator.id`, uno por creador, índice parcial único). No se creó ningún endpoint nuevo: este ya era accesible a cualquier sesión autenticada (sin permiso RBAC) y ya se autofiltraba a "solo tú mismo" cuando quien llama es un creador.
- `responsable_user_id` de un préstamo apunta a `users.id`, **nunca** a `creators.id` — son entidades distintas (`Creator` no tiene columna de correo; vive en el `User` vinculado).
- El wizard (`NuevoPrestamoPage.jsx`) manda siempre los tres campos completos (`responsable_user_id`, `responsable_nombre`, `responsable_email`) tomados directamente del creador elegido (o de la sesión, si es un creador) — nunca depende de que el servidor adivine el nombre/correo a partir de un id suelto.
- Un creador **sin** cuenta vinculada todavía (dato histórico o de transición) aparece en la lista pero deshabilitado, con la leyenda "sin cuenta vinculada" — no se puede elegir como beneficiario hasta que tenga usuario.

## En el menú de Equipos

Los creadores ven **4 vistas**, no las 7 completas: Inicio, Inventario, Nuevo préstamo, Historial. **Sin** Dashboard, Activos ni Aprobaciones.

- Dashboard comparte el mismo permiso que Inicio (`equipos_inventario:ver`), y Activos comparte el mismo permiso que Historial (`equipos_prestamos:ver_propios`) — la regla no es expresable solo con permisos sin partirlos en acciones más finas (decisión explícita: no vale la pena el riesgo de tocar lo que ya funciona para los demás roles solo para esto). En vez de eso, `EquiposSidebar.jsx` esconde esos dos items **por rol** (`ocultoParaRoles: ["creador"]`), encima del chequeo de permiso normal.
- **Consecuencia real:** como un creador no tiene la pestaña "Activos", tampoco tenía dónde registrar su propia devolución. Se agregó el botón "Registrar devolución" directo a la Ficha del préstamo (`FichaPrestamoPage.jsx`, visible si `estado === "prestado"` y el usuario tiene el permiso) — reutiliza `RegistrarDevolucionModal` tal cual, sin cambios. Esto beneficia a cualquier rol, no solo a creadores: ahora también se puede registrar una devolución desde la Ficha además de desde Activos.
- Inventario para un creador es de **solo lectura**: ya estaba gateado botón por botón (`RequierePermiso`/`puede()` en `InventarioPage.jsx`), así que no hizo falta tocar nada ahí — con solo `equipos_inventario:ver`, los botones de alta/editar/auditar simplemente no aparecen.
- La firma del beneficiario (`firma_responsable`) y el registro de devolución **ya funcionaban** con el mismo permiso `equipos_prestamos:solicitar`/`registrar_devolucion` que un creador acaba de ganar — no hizo falta tocar ese código.

## Pruebas que cubren estas reglas

- `backend/tests/rbac/test_permisos_efectivos.py` / `test_catalogo_contrato.py`: el set efectivo de `creador` incluye exactamente `equipos_inventario:{ver}` + `equipos_prestamos:{solicitar,ver_propios,registrar_devolucion}`, nunca `equipos_aprobacion` ni el resto de `equipos_inventario`.
- `backend/tests/equipos/test_api_prestamos.py`: un creador puede crear su propio préstamo; no puede poner a otro creador como beneficiario ni mandando `responsable_user_id` directo por API; completa un flujo entero (crear → confirmar → aparecer en su listado → firmar su parte → registrar su devolución) con el rol base solo, sin ningún paquete aditivo.
- `backend/tests/equipos/test_api_inventario.py`: un creador ve el inventario pero no puede crear equipos.
- `backend/tests/test_permissions.py` (`TestCreatorsPermissions`): `GET /api/creators/` trae `user_id`/`email` del usuario vinculado; un creador sin cuenta vinculada no rompe, solo viene con esos dos campos en `None`.
- `frontend/e2e/equipos-creador.spec.js` (servidor real): el menú muestra solo las 4 vistas; Inventario no ofrece el botón de alta; el wizard autoasigna el beneficiario sin mostrar ningún selector; el flujo completo (crear, fotos, confirmar, firmar, Historial, registrar devolución desde la Ficha) funciona de principio a fin.
