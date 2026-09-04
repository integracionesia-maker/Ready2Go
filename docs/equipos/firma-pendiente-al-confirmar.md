# Firma pendiente al confirmar un préstamo

> Feature de Control de Equipos, construida con luz verde explícita de Jose (04/09/2026). Complementa `docs/equipos/plan-quirurgico.md` §4.3 y §5 (máquina de estados y API de préstamos).
>
> **Revisión 2 (04/09/2026, mismo día):** retroalimentación de marketing cambió el diseño de fondo — ver "Por qué existe" y el resto del documento. La revisión 1 (descrita en la primera versión de este archivo) nunca llegó a producción; queda reemplazada por completo.
>
> **Titular de la firma (04/09/2026, mismo día, luz verde de Jose):** `firma_entrega` ya no la puede subir cualquiera con `APROBADOR_EQUIPO` — solo el titular del paquete singleton `TITULAR_FIRMA_EQUIPO`, verificado por identidad (ni siquiera superadmin la evade). Antes de que exista una firma real, su nombre también se imprime por default en la responsiva en vez de dejarlo en blanco. Ver §Titular más abajo — reemplaza el diseño original de esta sección, que abría la firma a cualquier `APROBADOR_EQUIPO` y dejó pasar que un superadmin de pruebas firmara sin querer.

## Por qué existe

A la plataforma pueden entrar varios usuarios, y da igual quién llene el formulario del préstamo — lo que importa es a quién le pertenece cada firma:

- **La firma del aprobador** (`firma_entrega`) siempre le pertenece a la misma persona: el titular del paquete singleton `TITULAR_FIRMA_EQUIPO` (Melisa hoy, pero no está cableada a su cuenta — se reasigna sin tocar código si el puesto cambia de dueño). No es "cualquiera con `APROBADOR_EQUIPO`": ver §Titular.
- **La firma del beneficiario** (`firma_responsable`) le pertenece a quien va a usar el equipo — que puede no tener cuenta en GOCreate y puede no coincidir con quien llenó el formulario.

Exigir ambas firmas al confirmar asumía que las tres personas (solicitante, aprobador, beneficiario) coinciden en tiempo y lugar. En la práctica casi nunca es así: alguien arma el préstamo en el sistema, Melisa lo aprueba cuando entra a la app (a veces horas después), y el beneficiario firma cuando el equipo ya está en su poder. Bloquear la reserva del equipo hasta que las tres coincidan no tenía sentido operativo.

## La regla

- **`POST /api/loans/{id}/confirmar` ya no exige ninguna firma.** Solo las fotos de entrega (2 por equipo) son obligatorias — quien crea el préstamo está físicamente con el equipo, esa parte no cambió. El préstamo pasa a `prestado` con **las dos firmas pendientes**, siempre.
- Las firmas **nunca se aceptan en `borrador`** (`acepta_media` las excluye de ese estado por completo) — solo después de confirmar, en `prestado`, `pendiente_confirmacion` o `incompleto`. No hay firmas en el wizard de creación.
- **`firma_entrega` (aprobador) solo la puede subir el titular del paquete singleton `TITULAR_FIRMA_EQUIPO`** — esto es una verificación de **identidad** (`current_user.id == titular.id`), no de permiso: cualquier otra cuenta recibe `403 SIN_PERMISO`, incluido otro `APROBADOR_EQUIPO` que no sea el titular, e incluido superadmin (su bypass `*` no aplica aquí porque no se pasa por `rbac.tiene_permiso()`). Ver §Titular.
- **`firma_responsable` (beneficiario) la puede subir cualquiera con `equipos_prestamos:solicitar`** — no está atada a una cuenta específica, porque el beneficiario mismo puede no tener cuenta en GOCreate; en la práctica la sube quien tenga el equipo enfrente en ese momento (a menudo el propio beneficiario, si tiene acceso a la app, o quien lo atiende).
- **Una firma ya capturada no se puede volver a subir** — es evidencia, igual que las fotos de entrega. El endpoint responde `409 TRANSICION_INVALIDA`.
- Al completarse **cada** firma, la responsiva se regenera (v2 con la primera, v3 si aplicara con la segunda — nunca se sobrescribe una versión anterior) y se dispara un correo de aviso.
- El nombre impreso bajo cada firma en la responsiva es quien realmente la subió (`MediaAsset.created_by_user_id`), no un campo fijo del préstamo — importante porque, a diferencia de la revisión 1, el aprobador ya no es necesariamente quien "entrega" físicamente el equipo.

## Titular (`TITULAR_FIRMA_EQUIPO`)

**Historia real que motivó esto:** el diseño original de esta sección abría `firma_entrega` a cualquiera con el paquete `APROBADOR_EQUIPO`. Al probarlo, entrar como superadministrador dejaba firmar igual — el bypass `*` de superadmin pasa cualquier `rbac.tiene_permiso()`, y ese endpoint validaba por permiso. Una firma que "cualquier admin puede poner" no es una firma. La corrección: `firma_entrega` se verifica por **identidad**, contra un titular único, nunca por el motor de permisos genérico.

- **`TITULAR_FIRMA_EQUIPO` es un paquete aditivo nuevo, kind `singleton`**: solo un usuario a la vez puede tenerlo. Se asigna en `/administracion-sistema` → pestaña "Asignaciones", igual que cualquier otro paquete aditivo — pero al concedérselo a alguien, `crud_rbac.conceder()` se lo revoca automáticamente a quien lo tuviera antes (nunca hay dos titulares vivos). La UI avisa de esto antes de conceder.
- **No concede ningún permiso por sí solo** en el catálogo (`permisos: {}`, deny-by-default) — pero SÍ es, en la práctica, el único requisito real para subir `firma_entrega`: `routers/loans.py::subir_media` compara `current_user.id == crud_rbac.titular_firma_equipo(db).id` directo, **sin pasar por `rbac.tiene_permiso()`** (ese motor tiene el bypass de superadmin integrado). Ni siquiera otro `APROBADOR_EQUIPO` sirve — ese paquete sigue abriendo autorizar entregas/confirmar devoluciones/cerrar incidencias (el resto del flujo de aprobación), pero no firmar. Si nadie tiene el paquete todavía, nadie puede firmar (`403 SIN_PERMISO` con mensaje explícito pidiendo asignarlo primero).
- **Mientras `firma_entrega` no exista**, el nombre impreso en la carta es el del titular actual (mismo `crud_rbac.titular_firma_equipo`, reusado para el relleno de nombre) — la imagen de la firma se queda en blanco y sigue diciendo "(FIRMA PENDIENTE)": esto solo rellena el nombre, nunca inventa una firma.
- **Si el titular cambia después de que ya existe una firma real**, esa firma no se reescribe con efecto retroactivo — `_firmas_de` solo aplica el relleno cuando no hay ningún `MediaAsset` de `firma_entrega` todavía.
- **Si nadie tiene el paquete asignado**, el comportamiento es: nombre vacío + "(FIRMA PENDIENTE)" en la carta, y nadie puede subir `firma_entrega` hasta que se asigne.
- **En el cliente**, `GET /api/loans/titular-firma-equipo` (permiso: `equipos_prestamos:solicitar` o `equipos_aprobacion:autorizar_entrega`, igual que `/media`) devuelve `{user_id, nombre, soy_titular}` — la Ficha del préstamo y Aprobaciones lo usan para pintar el botón "Firmar" del aprobador SOLO a la titular; a cualquier otro `APROBADOR_EQUIPO` le muestran "Solo puede firmar: <nombre>" en vez de un botón que siempre daría 403.
- Pensado para que ni el nombre por default ni quién puede firmar de verdad queden hardcodeados a una persona: si Melisa deja el puesto, se reasigna el paquete a quien la sustituya y tanto el candado como el nombre en las cartas futuras cambian solos, sin tocar código.

### `firmas_completas` — el mismo patrón que `entrega_autorizada`

Igual que la autorización de entrega es ortogonal al estado pero bloquea `completado`, `firmas_completas` (ambas firmas presentes, derivado de `media_asset` — no es una columna nueva) hace lo mismo:

- **No bloquea** `confirmar`, `devolución`, ni llegar a `pendiente_confirmacion` o `incompleto`.
- **Sí bloquea** las dos únicas rutas hacia `completado` — `confirmar-devolucion` (con todo `ok`) y `cerrar-incidencia` — con `409 TRANSICION_INVALIDA` y detalle explícito ("Este préstamo tiene una firma pendiente (del aprobador o del beneficiario)..."). Se rechaza **antes** de escribir nada, mismo criterio que la guarda de autorización: un éxito falso (quedarse en `pendiente_confirmacion` con 200) sería peor que el rechazo.

> Ejemplo: alguien arma un préstamo para un compañero de otra sucursal. Se confirma sin ninguna firma, el equipo queda reservado y viaja normalmente. Melisa entra a la app esa tarde, ve la notificación de "firma pendiente" en Aprobaciones y firma como aprobadora. El beneficiario firma tres días después, cuando por fin tiene el equipo en mano. El préstamo puede devolverse y el aprobador puede tomar la decisión de la devolución en cualquier momento intermedio — pero no puede cerrarse como `completado` hasta que las dos firmas estén, sin importar cuánto tiempo pase.

## En el formulario de préstamo (`/equipos/nuevo`)

- El paso 1 (Datos) ahora pide, además de Área/Marca/Motivo/Fecha, los datos del **Beneficiario** (nombre y correo, texto libre — no un selector de usuarios). "Solicitado por" sigue mostrando la sesión actual, pero es puramente informativo: ya no se asume que el solicitante sea el beneficiario.
- El wizard **ya no tiene un paso de Firmas** — son 3 pasos (Datos, Equipos, Fotos), y "Confirmar préstamo" se habilita en cuanto todas las fotos están, sin pedir ninguna firma.

## En la UI (ficha, listados, aprobaciones)

- Dos badges independientes, no uno: **"Firma del aprobador pendiente"** y **"Firma del beneficiario pendiente"**, derivados de `firma_entrega_pendiente`/`firma_responsable_pendiente` (reemplazan el `firma_pendiente` único de la revisión 1) — visibles en la Ficha del préstamo, Historial, Activos y las colas de Aprobaciones.
- **Aprobaciones** tiene una cola nueva, "Firmas pendientes", además de las tres que ya existían (autorizaciones, devoluciones, incidencias) — lista los préstamos con `firma_entrega_pendiente=true` para quien tenga el paquete `APROBADOR_EQUIPO`.
- El sidebar de Equipos muestra un badge numérico en "Aprobaciones" (mismo patrón que el badge de Presupuestos) contando esos préstamos, visible solo para quien tenga ese paquete.
- Botón para completar cada firma: el de la firma del aprobador solo aparece si el usuario ES el titular (`soy_titular` de `GET /api/loans/titular-firma-equipo`) — no basta con tener `APROBADOR_EQUIPO`; el de la firma del beneficiario aparece para cualquiera con `equipos_prestamos:solicitar`.

## Correos

- El aviso de "préstamo confirmado" menciona explícitamente cuál(es) firma(s) falta(n) — "el aprobador", "el beneficiario", o ambas unidas con "y" — aclarando que la responsiva adjunta las muestra en blanco y se actualiza sola.
- Al completarse cada firma pendiente: correo **"Firma completada"** con la responsiva actualizada adjunta.

## Pruebas que cubren estas reglas

- `backend/tests/equipos/test_loan_state.py`: las firmas nunca se aceptan en `borrador`, sí en `prestado`/`pendiente_confirmacion`/`incompleto`.
- `backend/tests/equipos/test_api_prestamos.py`: confirmar sin ninguna firma procede igual; una firma no se puede subir antes de confirmar; **solo el titular** puede subir `firma_entrega` (otro `APROBADOR_EQUIPO` sin el paquete singleton recibe 403 igual que quien llena el formulario); un aprobador puro (sin `equipos_prestamos:solicitar`, con `APROBADOR_EQUIPO` + `TITULAR_FIRMA_EQUIPO`) no puede subir fotos ni `firma_responsable` pero sí `firma_entrega`; completar las dos firmas genera responsiva v2; no se puede resubir una firma ya capturada; la protección es por `(prestamo, kind)`, no global.
- `backend/tests/equipos/test_aprobacion.py`: `confirmar-devolucion` y `cerrar-incidencia` rechazan con cualquiera de las dos firmas pendiente (incluso con entrega ya autorizada) y no escriben nada; completarlas desbloquea; la bitácora registra el ciclo completo con los dos eventos de firma.
- `backend/tests/equipos/test_responsiva_pdf.py`: el nombre bajo cada firma es quien realmente la subió, no un campo fijo del préstamo; el titular aparece por default antes de que exista una firma real; cambiar de titular después de una firma real no la reescribe con efecto retroactivo.
- `backend/tests/equipos/test_notificaciones.py`: el aviso de confirmación menciona las firmas pendientes; completar cada una avisa por correo con la responsiva actualizada.
- `backend/tests/rbac/test_migracion_y_endpoints.py`: conceder el paquete singleton `TITULAR_FIRMA_EQUIPO` revoca al titular anterior (por CRUD y por API); es idempotente contra el mismo usuario; no afecta paquetes aditivos normales (varios a la vez, ej. `AUDITOR`); `titular_de`/`titular_firma_equipo` devuelven `None` si nadie lo tiene.
- `frontend/e2e/equipos-flujo-completo.spec.js`: el 409 por foto faltante se sigue verificando en cliente y servidor, sin ninguna mención de firmas (ya no aplica); el wizard llega a "Confirmar préstamo" sin pasar por ningún paso de firmas.
