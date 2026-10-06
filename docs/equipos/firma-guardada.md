# Firma predeterminada del perfil

> Feature de Control de Equipos (con toque en Perfil/auth), construida con luz verde de Jose (06/10/2026). Complementa `docs/equipos/firma-pendiente-al-confirmar.md` — las reglas de **quién** puede firmar y **cuándo** no cambian; esto solo cambia **de dónde sale la imagen** de la firma.

## Qué resuelve

Creadores y aprobadores tenían que dibujar su firma de nuevo en cada préstamo. Ahora cualquier usuario guarda **una** firma predeterminada en su Perfil y, donde le toca firmar, elige entre usar la guardada (un botón) o dibujar ahí mismo.

## Reglas

- **Una firma por usuario, privada.** Solo su dueño la ve, la guarda y la borra: `/api/auth/me/signature` no lleva `{user_id}`, así que ni siquiera un superadmin puede leer la de otro por esa ruta. Cualquier usuario autenticado puede tener una, sin importar sus permisos de Equipos.
- **Mismas reglas de archivo que una firma de préstamo** (`media_manager.validar`): PNG/JPEG por magic bytes, máximo 250 KB, dimensiones máximas. Lo guardado en el perfil siempre es aceptable después como evidencia. Un archivo inválido no pisa la firma anterior.
- **Firmar con la guardada no manda imagen desde el cliente.** `POST /api/loans/{id}/media` acepta `usar_firma_guardada=true` **en lugar de** `file`: el servidor toma la firma del usuario logueado y la **copia** a un `MediaAsset` del préstamo. Nadie puede estampar la firma de otra persona.
- **La copia es evidencia independiente.** Cambiar o borrar la firma del perfil después no toca ningún préstamo ya firmado (archivo y fila distintos).
- **No abre ninguna puerta nueva** — todo lo de `firma-pendiente-al-confirmar.md` sigue valiendo:
  - `firma_entrega` sigue siendo identidad del titular de `TITULAR_FIRMA_EQUIPO`. Tener firma guardada no sirve de nada si no eres el titular (403 `SIN_PERMISO`).
  - Una firma ya capturada no se re-sube (409 `TRANSICION_INVALIDA`), tampoco con la guardada.
  - Nunca en `borrador`; solo en `prestado`, `pendiente_confirmacion` o `incompleto`.
  - Cada firma regenera la responsiva de inmediato, deja evento `firma_completada` y audit `loan.signature_completed` (con sufijo `:guardada` en `details` cuando se usó la guardada).
- **`firma_responsable` con firma guardada: solo si quien firma ES el beneficiario** (`loan.responsable_user_id == current_user.id`; los creadores ya se autoasignan). Quien tiene el equipo enfrente y firma **por** otra persona puede dibujarla, como siempre, pero no estampar su propia firma guardada por ella → 403 `SIN_PERMISO`.
- **Guardar al dibujar:** `guardar_como_predeterminada=true` (junto con `file`) guarda lo recién dibujado en el perfil, *después* de que la firma del préstamo ya quedó firme. Si guardarla en el perfil fallara, el firmado no se deshace (se loguea una advertencia).
- Parámetros inválidos → 422 `VALOR_INVALIDO`: archivo y `usar_firma_guardada` a la vez (o ninguno de los dos); cualquiera de los dos flags con un kind que no sea firma; `guardar_como_predeterminada` junto con `usar_firma_guardada`. Pedir la guardada sin tenerla → 404 `NO_ENCONTRADO`.

## API

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/auth/me/signature` | Imagen de **mi** firma (404 si no hay). `Cache-Control: private`, `ETag` = sha256. |
| `PUT` | `/api/auth/me/signature` | Multipart `file`: crea o reemplaza (borra el archivo anterior). Audit `user.signature_saved`. |
| `DELETE` | `/api/auth/me/signature` | Borra la mía (404 si no hay). Audit `user.signature_deleted`. |
| `GET` | `/api/auth/me` | Ahora incluye `tiene_firma_guardada: bool`. |
| `POST` | `/api/loans/{id}/media` | `file` ahora opcional; nuevos `usar_firma_guardada` y `guardar_como_predeterminada`. |

Almacenamiento: tabla `user_signature` (una fila por usuario, `user_id` único con `ON DELETE CASCADE`) + archivo en `uploads/firmas_usuario/` (relativo al cwd del backend, igual que el resto de uploads). Nunca base64 en la base. La tabla la crea `Base.metadata.create_all` al arrancar — **no hay script de migración que correr**. Código: `backend/app/user_signature.py`, `backend/app/routers/firma_guardada.py`, `routers/loans.py::subir_media`.

## En la UI

- **Perfil → "Mi firma"** (`ProfilePage.jsx::MiFirmaPanel`, oculto mientras hay cambio de contraseña forzado): sin firma muestra el pad + "Guardar firma"; con firma muestra la vista previa + "Cambiar firma" / "Eliminar".
- **`CompletarFirmaModal`** (Ficha del préstamo y Aprobaciones): si el usuario tiene firma guardada y `permiteFirmaGuardada`, abre con la vista previa y el botón **"Firmar con mi firma guardada"** + "Dibujar otra". Si no tiene, abre el pad de siempre con la casilla "Guardar como mi firma predeterminada" (o "Reemplazar mi firma predeterminada con esta" si ya tenía).
- `permiteFirmaGuardada` lo decide el padre: siempre en la firma del aprobador (el servidor ya exige ser el titular); en la del beneficiario solo si `loan.responsable.user_id === user.id`. Si firmas por otra persona, no se ofrece la guardada ni la casilla (lo que dibujas no es tu firma).
- El wizard de préstamo no tiene firmas (ver `firma-pendiente-al-confirmar.md`), así que no cambia.

## Pruebas

- `backend/tests/equipos/test_firma_guardada.py` (19): guardar/leer/borrar, una por usuario y reemplazo borra el archivo viejo, archivo inválido no pisa la anterior, 413 por tamaño, aislamiento entre usuarios, 401 sin sesión; el beneficiario y el titular firman con la guardada; **tener firma guardada no abre `firma_entrega`**; no se estampa por otro beneficiario (pero sí dibujada); 404 sin firma guardada; la copia es independiente del perfil; no se re-sube una firma ya capturada ni en `borrador`; combinaciones inválidas de parámetros; casilla de guardar al dibujar (y que un rechazo no cuela nada al perfil).
- `frontend/e2e/firma-guardada.spec.js`: flujo completo con servidor real (guardar en Perfil, firmar con un botón, "Dibujar otra" + reemplazar, eliminar). Necesita `E2E_SUPERADMIN_PASSWORD` y 3 equipos libres.
