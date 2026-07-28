# Backlog — carril servidor y datos (Control de Equipos)

Mis pendientes. No es el backlog del proyecto.

---

## Tareas del reparto

| ID | Tarea | Estado |
|---|---|---|
| S0 | Costura: enum, re-exports, deps | hecho 2026-07-28 |
| S1 | RBAC aditivo (WP1) | pendiente |
| S2 | Modelo de datos equipos (WP2) | pendiente |
| S3 | API inventario (WP3) | pendiente |
| S4 | API prestamos, aprobacion, media (WP4) | pendiente |
| S5 | Carta responsiva PDF (WP5) | pendiente |
| S6 | Correo y recordatorios (WP6) | pendiente |
| S7 | Guardias de contrato | pendiente |

## Pendientes sueltos

- `openapi_equipos_v1.json` no existe todavia (§8 del contrato). La guardia
  `test_contrato_openapi.py` de S7 queda en `skip` con motivo escrito hasta que
  se congele. Hay que pedir que se genere y congele en cuanto S3-S6 esten en pie.

## Dependencias externas que me bloquean (no las resuelvo yo)

- Razon social emisora de la responsiva sin confirmar (§14.3 del plan). El
  fixture `empresas.json` la marca `PENDIENTE`. Bloquea el cierre de S5, no el
  codigo: la razon social sale de la tabla `empresa`, cambiarla es un UPDATE.
- Credenciales SMTP (§14.6 del plan). Bloquean el envio real de S6, no el
  codigo: `NOTIF_ENABLED=false` deja todo probable sin cuenta.
- Correos GO del area de marketing (§14.1). Bloquean el seed de usuarios reales,
  no el codigo.
