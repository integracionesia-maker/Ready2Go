# Changelog del contrato de API

## v1 — 2026-07-27
Version inicial congelada. Inventario, prestamos, aprobacion, media, empresas, roles y permisos.

Decisiones que se apartan del plan quirurgico y quedan asentadas aqui:
- Rutas unificadas en ingles (`/api/equipment/dashboard`, no `/api/equipos/dashboard`).
- `GET /api/media/{id}?tamano=thumb` (miniatura 96px en servidor) entra al contrato aunque el plan no la especificaba: sin ella el inventario baja 3 MB por cada thumb.
- `GET /api/loans/?estado=borrador&mios=1` para recuperar un borrador propio: el wizard crea borrador en servidor y el plan no daba forma de recuperarlo si se cierra la pestaña.
- `GET /api/loans/by-folio/{folio}` porque la ruta de la ficha es `/equipos/prestamo/:folio`.
- El listado de inventario incluye `tenedor_actual`, `fecha_regreso_esperada`, `atrasado` y `dias_atraso` en la propia fila.
- `openapi_equipos_v1.json` pendiente: se genera del servidor y se congela cuando existan los primeros endpoints.

## 2026-10-19 — Paquete ADMIN_USUARIOS (aditivo, sin cambios para Equipos)
`permisos_catalogo.json`: el modulo `usuarios` suma las acciones `administrar_cuentas` y `ver_roles`, y aparece el paquete aditivo `ADMIN_USUARIOS` (solo concedible a rol base `admin`). Nada de Equipos cambia: ni rutas, ni codigos de error, ni los permisos existentes. `usuarios:gestionar` y `usuarios:gestionar_roles` siguen siendo exclusivos de superadmin.
