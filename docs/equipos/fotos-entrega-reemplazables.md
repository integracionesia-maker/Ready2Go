# Fotos de entrega reemplazables en cualquier momento (Control de Equipos)

> Cambio aprobado con luz verde explícita de Jose (15/09/2026). Espeja el sistema de la fecha de regreso esperada (`docs/equipos/firma-pendiente-al-confirmar.md` no toca esto; la regla de firmas quedó igual).

## Por qué existe

En el mundo real, el creador que solicita equipo rara vez lo tiene en la mano en el momento de la solicitud: las fotos de entrega (frente/atrás) se toman después, a veces con prisa, y salen mal o quedan pendientes. Antes de este cambio, `loan_state.acepta_media` solo aceptaba fotos de entrega en `borrador`: una vez confirmado el préstamo, una foto mala era permanente.

Dos hechos que hacen seguro el cambio:

1. **La responsiva NO embebe fotos** (`backend/app/pdf/responsiva.py` solo incluye datos, condiciones y firmas). Reemplazar una foto de entrega no reescribe ningún documento firmado — el "nunca se sobrescribe" del plan (§6) aplica al PDF y a las firmas, no a las fotos.
2. La prohibición anterior no venía del contrato (`docs/equipos/contratos/API_EQUIPOS_v1.md` no la escribe): era una derivación del equipo, reportada como tal. La maqueta original incluso traía botón "Cambiar foto" en cada slot de foto.

## La regla

- **Solo las fotos de ENTREGA** (`foto_entrega_frente`, `foto_entrega_atras`) son reemplazables. Las de **devolución** (`foto_dev_*`) conservan su ventana de estado (`prestado` únicamente) y las **firmas** siguen siendo irreemplazables (409 si ya fueron capturadas). Esto lo garantiza el backend por kind, no solo la UI.
- **Ventana — espejo exacto de la fecha de regreso esperada** (`PATCH /api/loans/{id}/fecha-regreso-esperada`): no aplica en un préstamo terminal (`completado`/`cancelado`) ni una vez que el equipo ya volvió (`fecha_regreso_real` seteada). En la práctica la ventana efectiva es `borrador` (wizard, como siempre) + `prestado` (lo nuevo), porque `fecha_regreso_real` se escribe al registrar la devolución.
- **Permiso — misma puerta que ver la ficha**: `equipos_prestamos:ver_propios` (el beneficiario sobre su préstamo, p. ej. el creador que solicitó) o `equipos_prestamos:ver_global` (custodios, aprobadores, marketing_equipos/admin, superadmin). Sin permiso nuevo a propósito, igual que la fecha. Consecuencia aceptada del espejo: un `AUDITOR` (`ver_global`, "cero escritura") queda técnicamente habilitado para reemplazar fotos — igual que ya lo estaba para la fecha. La puerta del endpoint (`subir_media`) ahora es `ver_propios`/`ver_global`/`autorizar_entrega`; devolución y `firma_responsable` siguen exigiendo `solicitar` por dentro, y `firma_entrega` sigue siendo identidad del titular `TITULAR_FIRMA_EQUIPO` (nada de esto cambió).
- El reemplazo usa `media_manager.reemplazar` tal cual: borra la fila y el archivo viejos y crea una fila nueva (id y sha nuevos). No hay historial de fotos en `media_asset` — la constancia queda en la bitácora y la auditoría.

## Trazabilidad

Al subir/reemplazar una foto de entrega en un estado distinto de `borrador` (en `borrador` el wizard sube fotos como rutina y no se escribe nada, igual que no hay evento de fecha ahí):

- **Bitácora del préstamo** (`loan_event`): evento `foto_entrega_modificada` con detalle `Foto de entrega '{kind}' reemplazada (sha_anterior[:12] | 'sin foto previa' -> sha_nuevo[:12]).`
- **Auditoría** (`audit_log`): acción `loan.update_foto_entrega` con los shas completos `{folio}:{kind}:{sha_anterior|'null'}->{sha_nuevo}` en `details`.

## En la UI

- En la Ficha del préstamo, cada miniatura "Frente antes"/"Atrás antes" tiene un enlace **"Cambiar"** (o **"Subir foto"** si no tiene) — mismo estilo que el "Modificar" de la fecha, visible con la misma condición de ventana (`puedeCambiarFotos` en `FichaPrestamoPage.jsx`). Las miniaturas "después" no tienen ninguna acción.
- Abre `CambiarFotoEntregaModal` (`frontend/src/modules/equipos/components/CambiarFotoEntregaModal.jsx`), que reutiliza `PhotoCapture` (compresión 900px/0.72, "Volver a tomar"/"Elegir otro archivo"). La subida es inmediata; al éxito muestra el toast "Foto reemplazada" y recarga la ficha.

## Mock

`frontend/src/modules/equipos/api/mock/media.js` espeja la ventana (`TRANSICION_INVALIDA` en terminales o con `fecha_regreso_real`), empuja el evento `foto_entrega_modificada` y purga la entrada vieja del Map de media (espejo del borrado del servidor).

## Archivos clave

- `backend/app/loan_state.py::acepta_media` — ventana por estado (entrega: no terminal).
- `backend/app/routers/loans.py::subir_media` — puerta por kind, guard de cierre (`fecha_regreso_real`/terminales), evento + auditoría.
- `backend/app/models_equipos.py::TipoEvento.FOTO_ENTREGA_MODIFICADA`.
- `frontend/src/modules/equipos/pages/FichaPrestamoPage.jsx` — botones "Cambiar" y gate compartido con la fecha.
- `frontend/src/modules/equipos/components/CambiarFotoEntregaModal.jsx` — el modal.
- Tests: `backend/tests/equipos/test_loan_state.py` y `test_media.py` (sección "Reemplazo de fotos de entrega").
