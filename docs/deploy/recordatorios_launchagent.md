# Recordatorios de vencimiento — LaunchAgent del Mac mini

> Carril servidor y datos, tarea S6 (WP6). Patron: el mismo que ya usa
> `doc/deploy-runbook.md` para las tareas programadas del Mac mini.
> Diseño de las notificaciones: §7 de `docs/PLAN_QUIRURGICO_EQUIPOS_27_07_26.md`.

## Que hace

`backend/scripts/recordatorios_vencimiento.py` busca los prestamos **entregados**
cuya fecha de regreso ya paso y manda un recordatorio al responsable y a los
aprobadores.

No usa un temporizador dentro de uvicorn a proposito: un cron dentro del proceso
web se dispara una vez por trabajador y se pierde en cada reinicio.

Un prestamo en `pendiente_confirmacion` **no** entra: ya volvio fisicamente y lo
que falta es el visto bueno del aprobador. Mandarle "devuelve el equipo" a esa
persona la confunde.

## Correr a mano

Siempre desde `backend/` — las rutas de base de datos y uploads son relativas al
directorio de trabajo:

```bash
cd backend
python scripts/recordatorios_vencimiento.py            # registra y envia
python scripts/recordatorios_vencimiento.py --simular  # registra, no envia
```

Salida tipica:

```
=== Recordatorios de vencimiento — 2026-07-30 (CDMX) ===
  NOTIF_ENABLED=True SMTP_HOST=smtp.grupo-ortiz.com
  - CE-0007: 3 dia(s) de atraso, 2 aviso(s) por mandar
Listo: 1 prestamo(s) atrasado(s), 2 aviso(s) registrado(s), 2 enviado(s).
```

Correrlo dos veces el mismo dia **no duplica correos**: ver abajo.

## Por que el aviso se puede mandar todos los dias

`notification_log` tiene `UNIQUE (loan_id, tipo, destinatario)`. Ese indice es la
idempotencia: reintentar un envio no duplica el aviso a la aprobadora.

Pero el recordatorio de vencimiento es **diario**, y con un `tipo` constante el
UNIQUE lo mandaria **una sola vez en la vida del prestamo**: el segundo dia la
fila ya existiria, el sistema lo leeria como "ya enviado" y no saldria nada. Sin
error, sin log, sin que nadie lo note.

Por eso el tipo lleva el dia civil de CDMX:

```
vencimiento:2026-07-30
```

Asi el UNIQUE significa "un aviso por prestamo, por destinatario, **por dia**",
que es exactamente lo que pide §7, y sigue bloqueando la doble corrida del mismo
dia (el LaunchAgent disparando al despertar la Mac, o alguien corriendo el script
a mano).

El dia sale de `tz.hoy()`, nunca de UTC: despues de las 18:00 de CDMX el UTC ya
es el dia siguiente y se mandarian dos avisos para el mismo dia civil.

**Consecuencia a vigilar:** `notification_log` crece una fila por prestamo
vencido, por destinatario, por dia. Un prestamo 60 dias vencido con 3
destinatarios deja 180 filas. Falta definir una politica de retencion.

## Variables de entorno

Van en `backend/.env` (jamas al repo).

| Variable | Default | Para que |
|---|---|---|
| `NOTIF_ENABLED` | `false` | Corta-circuito. Con `false` **no se abre socket**: se registra el aviso y no se envia. Es el rollback de §13 y lo que permite probar sin cuenta SMTP |
| `SMTP_HOST` | — | Servidor de correo. Sin el, todo queda registrado y omitido |
| `SMTP_PORT` | `587` | Puerto |
| `SMTP_USER` | — | Usuario. Vacio = sin autenticacion |
| `SMTP_PASSWORD` | — | Contraseña. **Nunca se expone por API** |
| `SMTP_FROM` | — | Remitente. Se manda como `GOCreate — Control de Equipos <SMTP_FROM>` |
| `SMTP_STARTTLS` | `true` | STARTTLS tras conectar |
| `APP_PUBLIC_URL` | `http://127.0.0.1:5173` | Origen de los enlaces del correo |

Ejemplo de bloque para `.env`:

```
NOTIF_ENABLED=true
SMTP_HOST=smtp.grupo-ortiz.com
SMTP_PORT=587
SMTP_USER=gocreate@grupo-ortiz.com
SMTP_PASSWORD=cambiame
SMTP_FROM=gocreate@grupo-ortiz.com
SMTP_STARTTLS=true
APP_PUBLIC_URL=https://gocreate.grupo-ortiz.com
```

> **Pendiente que no puedo resolver yo:** el plan §7 pide que estas ocho
> variables entren tambien a `.env.example` con placeholders. `.env.example` esta
> en la lista de archivos fuera de mi carril
> (`docs/ASIGNACION_EQUIPOS.md`), asi que **hay que pedir ese parche a quien sea
> dueño de la raiz**. Sin esa entrada, quien clone el repo levanta el backend sin
> enterarse de que `NOTIF_ENABLED` existe.

## LaunchAgent

`~/Library/LaunchAgents/com.grupoortiz.gocreate.recordatorios.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.grupoortiz.gocreate.recordatorios</string>

  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>scripts/recordatorios_vencimiento.py</string>
  </array>

  <!-- Obligatorio: las rutas de base y uploads son relativas al cwd. -->
  <key>WorkingDirectory</key>
  <string>/Users/grupoortiz/GOCreate/backend</string>

  <!-- 9:00 todos los dias. -->
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>

  <!-- Si la Mac estaba dormida a las 9:00, corre al despertar. Correr dos
       veces el mismo dia no duplica correos (ver arriba). -->
  <key>RunAtLoad</key>
  <false/>

  <key>StandardOutPath</key>
  <string>/Users/grupoortiz/GOCreate/logs/recordatorios.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/grupoortiz/GOCreate/logs/recordatorios.err</string>
</dict>
</plist>
```

Cargar y comprobar:

```bash
launchctl load  ~/Library/LaunchAgents/com.grupoortiz.gocreate.recordatorios.plist
launchctl list | grep gocreate
launchctl start com.grupoortiz.gocreate.recordatorios   # dispara ya, para probar
tail -f ~/GOCreate/logs/recordatorios.log
```

Descargar:

```bash
launchctl unload ~/Library/LaunchAgents/com.grupoortiz.gocreate.recordatorios.plist
```

## Diagnostico: "no llegan los correos"

En orden, del problema mas frecuente al menos:

1. **`GET /api/notifications/config`** (solo `superadmin`). Devuelve
   `notif_enabled`, el host, el remitente, si hay usuario y contraseña
   configurados — nunca la contraseña — y `aprobadores_resueltos`.
2. **`aprobadores_resueltos: 0`** es la causa mas dificil de descubrir sola: no
   hay nadie con `equipos_aprobacion:autorizar_entrega`, asi que los avisos de
   autorizacion **no se mandan a nadie y no hay error en ningun lado**. Pasa en
   dos casos:
   - Nadie tiene concedido el aditivo `APROBADOR_EQUIPO` (`python seed_rbac.py`).
   - **`RBAC_MODO=legacy`**: el rollback de §13 apaga los paquetes aditivos, y
     `equipos_aprobacion` solo lo concede uno de ellos. El servidor lo escribe en
     el log como advertencia; no hay forma de arreglarlo sin salir de `legacy`.
3. **`GET /api/notifications/`** lista el registro con su `estado`, `intentos` y
   `error`. `fallido` trae el motivo real del servidor SMTP.
4. **`POST /api/notifications/{id}/reintentar`** reintenta **reusando la misma
   fila**: no crea una nueva, para no perder la cuenta de intentos.

> Estos tres endpoints **no estan en el contrato de API v1**. Existen porque la
> asignacion los pide en S6, y van protegidos con `usuarios:gestionar`, que hoy
> solo tiene el `superadmin`. Cuando el contrato v2 defina su propio modulo de
> notificaciones, hay que cambiarles el permiso.

## Limites conocidos

- **Reintentos:** 3 por fila (`notificaciones.MAX_INTENTOS`). Despues queda en
  `fallido` esperando reintento manual. No hay backoff.
- **Estar apagado no gasta intentos:** con `NOTIF_ENABLED=false` la fila se queda
  en `pendiente`, lista para cuando haya cuenta SMTP.
- **Formato:** texto plano UTF-8. Sin CSP que pelear, sin imagenes remotas que se
  bloqueen, legible en cualquier cliente. Si marketing quiere HTML, es decision
  de marca.
- **Las rutas de los enlaces** (`/equipos/aprobaciones`,
  `/equipos/prestamo/{folio}`) son propuesta: el contrato solo define rutas de
  `/api/*`. Hay que confirmarlas con quien construye la interfaz o los correos
  van a apuntar a paginas que dan 404.
- **La redaccion de los cinco correos** es propuesta del servidor. Son mensajes de
  cara a personas de Grupo Ortiz; conviene que marketing los apruebe antes del
  piloto. Estan en `backend/app/plantillas_correo.py`.
