# Migración de GOCreate: droplet Ubuntu → Mac mini

> **Estado:** preparado, **no ejecutado**. Inventario verificado contra el servidor en vivo el **27/08/2026**.
> **Para quién:** el agente o la persona que ejecute la migración. Está escrito para seguirse de arriba abajo sin conocimiento previo del proyecto.
> **Ventana:** fuera de horario laboral. Indisponibilidad real estimada: **20-40 minutos** (solo ~8 MB de datos; el resto es arranque y verificación).
> **Reglas del proyecto:** [[../../CLAUDE]] · Deploy previo, parcialmente obsoleto (ver §2): [[runbook]] · Recordatorios: [[recordatorios_launchagent]]

---

## 0. Resumen de la operación

Se mueven **tres cosas** y una **no se toca**:

| | Qué | Cómo |
|---|---|---|
| 1 | **Código** | `git clone` del repo en la Mac + build del frontend |
| 2 | **Datos** | `presupuesto.db` (con su WAL), `backend/uploads/` y `backend/.env` por SSH |
| 3 | **Túnel** | Copiar 1 archivo de credenciales y arrancar `cloudflared` en la Mac |
| — | **DNS de `gocreate.mx`** | **NO SE TOCA.** Ver §3 |

El dominio sigue funcionando porque los registros DNS no apuntan a una IP: apuntan al **túnel**. El túnel es una identidad portátil que vive en un archivo de credenciales. Se mueve el archivo, se mueve el túnel, y `gocreate.mx` sale por donde corra `cloudflared` — sin tocar Cloudflare y sin esperar propagación de DNS.

---

## 1. Estado de origen (verificado 27/08/2026)

### Servidor actual

| Dato | Valor |
|---|---|
| Host | `gocreate` — droplet DigitalOcean |
| Acceso | `ssh root@100.99.205.35` (**Tailscale SSH**, tailnet `tailfa5bb1.ts.net`) |
| SO | Ubuntu 24.04.4 LTS, x86_64, kernel 6.8 |
| Repo | `/root/Ready2Go`, rama **`master`**, remoto `https://github.com/integracionesia-maker/Ready2Go` |
| Python | 3.12.3 (venv en `/root/Ready2Go/backend/venv`) |
| Node / npm | v20.20.2 / 10.8.2 |
| cloudflared | 2026.8.2 |
| `sqlite3` CLI | **NO instalado** — los respaldos se hacen con la API de backup de Python (§5.1) |

### Servicios (systemd)

| Unit | Qué hace |
|---|---|
| `gocreate-backend.service` | `uvicorn app.main:app --host 127.0.0.1 --port 8000`, `WorkingDirectory=/root/Ready2Go/backend`, `Restart=always`, log en `/var/log/gocreate-backend.log` |
| `cloudflared-gocreate.service` | `cloudflared tunnel --config /root/.cloudflared/config.yml run gocreate-produccion`, log en `/var/log/cloudflared-gocreate.log` |

No hay nginx, no hay Caddy, no hay Docker y no hay cron (`crontab -l` vacío).

### Volumen de datos

| Artefacto | Tamaño |
|---|---|
| `backend/presupuesto.db` | 3.1 MB |
| `backend/presupuesto.db-wal` | **4.1 MB** ← leer §5.1, es la trampa principal |
| `backend/uploads/tickets` (13 archivos) | 5.0 MB |
| `backend/uploads/equipos` (2 archivos) | 116 KB |
| `backend/uploads/responsivas` | no existe todavía (0 responsivas emitidas) |
| **Total a transferir** | **~8 MB** |

23 tablas. Al momento del inventario: 27 usuarios, 7 creadores, 26 tickets, 18 gastos generales, 9 equipos, 2 préstamos, 3 razones sociales, 6235 filas de auditoría.

---

## 2. Arquitectura

### Hoy (droplet)

```
Internet ──HTTPS──> Cloudflare (edge, termina TLS)
                         │  túnel gocreate-produccion (4 conexiones QUIC salientes)
                         ▼
                   cloudflared (droplet)
                         │  http://127.0.0.1:8000
                         ▼
                   uvicorn / FastAPI ──┬── /api/*  → la API
                                       └── /*      → frontend/dist (estáticos + fallback SPA)
```

### Destino (Mac mini) — idéntica, solo cambia el sistema de arranque

```
Internet ──HTTPS──> Cloudflare (edge, termina TLS)     ← sin cambios
                         │  MISMO túnel, MISMO UUID
                         ▼
                   cloudflared (Mac mini, LaunchDaemon)
                         │  http://127.0.0.1:8000
                         ▼
                   uvicorn / FastAPI (LaunchDaemon)
```

> ⚠️ **`docs/deploy/runbook.md` es anterior a esta arquitectura y su §6 (Caddy) NO aplica.**
> Ese documento se escribió para una Mac en LAN sin dominio público, con Caddy como reverse proxy y certificados de Tailscale. Hoy **no hace falta Caddy ni ningún certificado local**: Cloudflare termina el TLS en su edge y `cloudflared` habla en claro contra `127.0.0.1:8000`. FastAPI ya sirve los estáticos del frontend por sí mismo (`app/main.py`, ruta catch-all `serve_frontend`).
> Lo que **sí** sigue vigente de ese runbook: los plists de launchd (§7), el script de backup (§8), el endurecimiento de macOS (§9) y el `pmset` para que la Mac no duerma (§1).

---

## 3. Cómo se conserva `gocreate.mx` — la parte crítica

### Datos del túnel

| Dato | Valor |
|---|---|
| Nombre | `gocreate-produccion` |
| UUID | `2bb84bef-c493-4682-aa1e-4f2abc8e5164` |
| Tipo | *Locally-managed* (la configuración vive en `config.yml`, no en el dashboard) |
| Hostnames | `gocreate.mx` y `www.gocreate.mx` → `http://127.0.0.1:8000`; el resto → 404 |
| Zona DNS | `gocreate.mx` en Cloudflare (nameservers `huxley.ns.cloudflare.com`), registros **proxied** |

### Los archivos que mueven el túnel

Están en `/root/.cloudflared/` del droplet:

| Archivo | ¿Necesario para correr? | Qué es |
|---|---|---|
| `2bb84bef-c493-4682-aa1e-4f2abc8e5164.json` | **SÍ** | Credencial del túnel. **Esto es el túnel.** 175 bytes, permisos `400` |
| `config.yml` | **SÍ** | Ingress: qué hostname va a qué servicio local |
| `cert.pem` | **NO** | Certificado de **cuenta** de Cloudflare. Ver la advertencia de abajo |
| `cert.pem.bak_040826`, `cert.pem.pre_login_040826` | NO | Respaldos viejos. No copiar |

### 🔒 No copies `cert.pem` a la Mac mini

`cert.pem` **no hace falta para correr un túnel que ya existe** — solo para comandos de gestión (`tunnel create`, `delete`, `route dns`, `list`).

Y es una credencial de **toda la cuenta de Cloudflare**, no de esta app. Esa cuenta tiene hoy **8 túneles** de otros proyectos (`bruckner-os`, `crece`, `go-assist`, `go-marketintel`, `go-observe`, `go-vision-lab`, `gopulse-tunnel`). Copiar `cert.pem` a la Mac le daría a esa máquina —y a cualquiera con acceso a ella— capacidad de crear, borrar y reapuntar el DNS de los túneles de las otras aplicaciones de marketing.

Si en algún momento hace falta un comando de gestión, se corre desde el droplet mientras siga vivo, o se hace desde el dashboard de Cloudflare.

### ⚠️⚠️ Nunca corras el mismo túnel en dos máquinas a la vez

Cloudflare **soporta** varias réplicas del mismo túnel y **balancea las peticiones entre ellas**. Es una función de alta disponibilidad, y aquí sería un desastre: cada máquina tiene su **propio SQLite**. Con el droplet y la Mac corriendo el túnel al mismo tiempo, los usuarios caerían aleatoriamente en una base o en la otra —verían datos distintos según la petición— y las escrituras se repartirían entre dos bases que después no se pueden reconciliar.

**Regla dura de la ventana: `cloudflared` se detiene en el droplet ANTES de arrancarlo en la Mac.** Nunca al revés, nunca solapado.

> Para no confundirse al leer `cloudflared tunnel list`: el túnel muestra `1xewr01, 1xewr07, 1xewr11, 1xewr16`. Son las **4 conexiones QUIC** que una sola instancia de `cloudflared` abre al edge, no 4 réplicas.

---

## 4. Artefactos a transferir

Lo que `git` **no** trae (está en `.gitignore`) y por lo tanto se copia a mano:

| Origen (droplet) | Destino (Mac mini) | Notas |
|---|---|---|
| `backend/presupuesto.db` **+ WAL** | `backend/presupuesto.db` | Con el método de §5.1, **nunca `cp` a secas** |
| `backend/uploads/` (árbol completo) | `backend/uploads/` | Preservar `tickets/`, `equipos/`, `responsivas/` |
| `backend/.env` | `backend/.env` | `chmod 600`. Ver §5.4 sobre `JWT_SECRET_KEY` |
| `/root/.cloudflared/2bb84bef-….json` | `~/.cloudflared/2bb84bef-….json` | `chmod 400` |
| `/root/.cloudflared/config.yml` | `~/.cloudflared/config.yml` | Ajustar la ruta de `credentials-file` (paso 7) |

Lo que **sí** trae git y no hay que copiar: todo `backend/app/`, `frontend/src/`, los scripts de seed y la documentación.

Lo que **se genera** en la Mac: `backend/venv/` (con `python3.12 -m venv`), `frontend/node_modules/` (`npm ci`) y `frontend/dist/` (`npx vite build` — está en `.gitignore`, no viaja por git).

**No copiar:** los `presupuesto.db.bak_deploy_*` del droplet (6 respaldos históricos), `/root/backups/`, ni el `.env` de la raíz del droplet (§5.5).

---

## 5. Trampas de este proyecto — leer antes de ejecutar

### 5.1 🔴 El WAL contiene datos que el `.db` no tiene

La base corre en modo **WAL** (`PRAGMA journal_mode = WAL`, `app/database.py`). Al momento del inventario:

```
presupuesto.db      3.1 MB   modificado Aug 25 17:58
presupuesto.db-wal  4.1 MB   modificado Aug 27 19:47   ← dos días de escrituras viven AQUÍ
```

**Copiar solo `presupuesto.db` pierde en silencio todo lo que esté en el WAL.** No hay error ni aviso: la app arranca con datos viejos y nadie lo nota hasta que alguien reclama un ticket que desapareció.

Hay dos formas correctas. Usa la primera:

**A. Respaldo consistente con la API de backup de SQLite** (funciona incluso con el servicio corriendo, y aplica el WAL):

```bash
# En el droplet
/root/Ready2Go/backend/venv/bin/python - <<'PY'
import sqlite3
src = sqlite3.connect("/root/Ready2Go/backend/presupuesto.db")
dst = sqlite3.connect("/root/migracion_presupuesto.db")
with dst:
    src.backup(dst)
dst.close(); src.close()
print("listo")
PY
```

El resultado es **un solo archivo autocontenido**, sin `-wal` ni `-shm`. Ese es el que se transfiere.

**B. Copiar los tres archivos juntos** (`.db`, `.db-wal`, `.db-shm`) con el servicio **detenido**. Válido, pero más fácil de arruinar: si se olvida el `-wal`, se pierden datos.

> Verificación obligatoria tras transferir y **antes** de exponer el sitio: comparar conteos de filas entre origen y destino (§8, paso 8).

### 5.2 🔴 Las rutas son relativas al directorio de trabajo

`app/database.py` usa `sqlite:///./presupuesto.db`, y los tres directorios de subidas están hardcodeados como rutas relativas:

```
app/upload_manager.py:10   UPLOAD_DIR             = Path("./uploads/tickets")
app/media_manager.py:55    DIRECTORIO             = Path("./uploads/equipos")
app/crud_loans.py:71       DIRECTORIO_RESPONSIVAS = Path("./uploads/responsivas")
```

**El proceso de uvicorn TIENE que arrancar con `cwd = backend/`.** En launchd eso es `WorkingDirectory`. Si falta o apunta a otro lado, la app crea una base vacía en otra carpeta y arranca **como si fuera una instalación nueva** — sin error visible, y con un login que rechaza a todos los usuarios reales.

### 5.3 🔴 Un solo worker

`--workers 1` es obligatorio, no una preferencia:

- SQLite tolera un escritor a la vez.
- El rate limit de login vive en un dict en memoria del proceso (`app/security.py`): con N workers cada uno llevaría su propia cuenta.

### 5.4 `JWT_SECRET_KEY`: cópialo tal cual

Si se genera uno nuevo, **todas las sesiones activas se invalidan** y todos los usuarios aparecen deslogueados. Como la migración es fuera de horario el impacto es bajo, pero no hay razón para provocarlo: copia `.env` completo y sin editar.

Lo único que podría querer revisión es `CORS_ORIGINS`, y aquí **no cambia** porque el dominio es el mismo:

```
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://gocreate.mx,https://www.gocreate.mx
ENV=production
```

`ENV=production` es lo que activa el flag `Secure` de las cookies y oculta `/docs` y `/redoc`. **No lo bajes a `development` "para probar"**: sin `Secure` y con el dominio en HTTPS la sesión se comporta de forma confusa, y `/docs` queda expuesto en internet.

### 5.5 Variables de entorno que NO hacen nada

El `.env` de producción trae tres variables inertes. Saberlo evita perder una hora:

| Variable | Realidad |
|---|---|
| `UPLOAD_DIR=./uploads` | **Inerte.** El código no la lee; las rutas están hardcodeadas (§5.2). Cambiarla no mueve nada |
| `HOST=127.0.0.1` | **Inerte.** El host lo pasa el `ExecStart`/plist con `--host` |
| `PORT=8000` | **Inerte.** Ídem, con `--port` |
| `DATABASE_URL` | **Sí se lee.** Pero es relativa (`sqlite:///./presupuesto.db`), así que depende del cwd de todos modos |

Además, el droplet tiene un **`.env` en la raíz del repo** (`/root/Ready2Go/.env`) desactualizado que **no se carga**: `app/main.py` carga explícitamente `backend/.env`. No lo copies; y si lo copias, no lo edites creyendo que sirve.

### 5.6 `frontend/dist` no viaja por git

Está en `.gitignore`. Hay que construirlo en la Mac con Node 20 (`npm ci && npx vite build`). Si no existe, FastAPI **no monta la ruta catch-all** y `https://gocreate.mx/` devuelve 404 mientras `/api/health` responde 200 — el síntoma exacto de "falta el build".

### 5.7 No corras `seed_equipos.py` ni ningún seed completo

Producción ya tiene datos reales. `python seed_equipos.py` ejecuta su `main()`, que inserta los 8 equipos del fixture con **ids explícitos** — y producción tiene 9 equipos reales. Lo mismo con `seed_demo_completo.py`, que mete creadores, marcas y razones sociales inventadas.

La migración **no siembra nada**: los datos llegan por copia de la base.

### 5.8 Las notificaciones por correo están apagadas

El `.env` de producción **no define ninguna variable `NOTIF_*` ni `SMTP_*`**, así que `NOTIF_ENABLED` toma su default `false`: los avisos se registran en `notification_log` y no se envía ningún correo. Eso se conserva tal cual tras la migración — **no es un fallo que reportar**. Si algún día se activa, ver [[recordatorios_launchagent]] §Variables de entorno.

---

## 6. Fase A — Preparación en la Mac mini (días antes, sin downtime)

Nada de esta fase afecta al servicio en producción. Complétala antes de la ventana.

### A.1 Acceso y red

1. Instalar **Tailscale** en la Mac mini y unirla al tailnet `tailfa5bb1.ts.net` (el mismo del droplet).
2. Activar **Tailscale SSH** en la Mac, para que el agente de migración entre igual que al droplet.
3. Anotar su IP `100.x.y.z` y su nombre MagicDNS en la tabla de §12.

> El tailnet ya tiene equipos macOS (`mac-studio`, `macbook-pro-de-jose`), así que el flujo está probado. La Mac mini es un nodo nuevo: no reutilices las credenciales de otro equipo.

### A.2 Que la Mac no se duerma ni se quede apagada

```bash
sudo pmset -a sleep 0 disksleep 0 autorestart 1
sudo systemsetup -setcomputersleep Never
```

Una Mac mini que duerme tumba el túnel. `autorestart 1` la reenciende tras un corte de luz.

### A.3 Dependencias

```bash
# Homebrew, si no está
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.12 node@20 git cloudflared sqlite
```

Anota en §12 si el Homebrew es de **Apple Silicon** (`/opt/homebrew`) o **Intel** (`/usr/local`) — las rutas de los plists dependen de eso.

Verifica versiones equivalentes al origen: Python 3.12.x, Node 20.x.

### A.4 Estructura y clon del repo

```bash
sudo mkdir -p /opt/gocreate/logs /opt/gocreate/backups
sudo chown -R $(whoami) /opt/gocreate

git clone https://github.com/integracionesia-maker/Ready2Go.git /opt/gocreate/app
cd /opt/gocreate/app
git checkout master
git log --oneline -1     # debe coincidir con el HEAD del droplet
```

> Se usa `/opt/gocreate` en vez del `/opt/presupuesto` del runbook viejo, para que la ruta corresponda al nombre actual del proyecto. Si prefieres otra, cámbiala **en todos** los plists y en §12.

### A.5 Backend: venv y dependencias

```bash
cd /opt/gocreate/app/backend
python3.12 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

`reportlab` y `pillow` tienen ruedas para arm64; si alguna compilara desde fuente, `xcode-select --install` resuelve el toolchain.

### A.6 Frontend: build

```bash
cd /opt/gocreate/app/frontend
npm ci
npx vite build
ls -la dist/index.html   # debe existir
```

### A.7 Los plists de launchd

Se crean ahora y se cargan en la ventana. Sustituye `USUARIO_MAC` y la ruta de Homebrew según §12.

**Backend** — `/Library/LaunchDaemons/com.grupoortiz.gocreate.backend.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.grupoortiz.gocreate.backend</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/gocreate/app/backend/venv/bin/python</string>
    <string>-m</string>
    <string>uvicorn</string>
    <string>app.main:app</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>8000</string>
    <string>--workers</string>
    <string>1</string>
  </array>
  <!-- OBLIGATORIO: las rutas de base y uploads son relativas al cwd (§5.2). -->
  <key>WorkingDirectory</key>
  <string>/opt/gocreate/app/backend</string>
  <key>UserName</key>
  <string>USUARIO_MAC</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/opt/gocreate/logs/backend.log</string>
  <key>StandardErrorPath</key>
  <string>/opt/gocreate/logs/backend.log</string>
</dict>
</plist>
```

Sin `--reload` (es de desarrollo) y con `--workers 1` (§5.3). No hace falta `--env-file`: `app/main.py` carga `backend/.env` por su cuenta.

**Túnel** — `/Library/LaunchDaemons/com.grupoortiz.gocreate.cloudflared.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.grupoortiz.gocreate.cloudflared</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/cloudflared</string>
    <string>tunnel</string>
    <string>--config</string>
    <string>/Users/USUARIO_MAC/.cloudflared/config.yml</string>
    <string>run</string>
    <string>gocreate-produccion</string>
  </array>
  <key>UserName</key>
  <string>USUARIO_MAC</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/opt/gocreate/logs/cloudflared.log</string>
  <key>StandardErrorPath</key>
  <string>/opt/gocreate/logs/cloudflared.log</string>
</dict>
</plist>
```

Permisos, para los dos:

```bash
sudo chown root:wheel /Library/LaunchDaemons/com.grupoortiz.gocreate.*.plist
sudo chmod 644 /Library/LaunchDaemons/com.grupoortiz.gocreate.*.plist
```

> Son **LaunchDaemons** (no Agents) a propósito: arrancan con el boot sin que nadie inicie sesión gráfica. Un LaunchAgent o `brew services` exigiría sesión abierta, y una Mac mini sin monitor tras un reinicio se quedaría con el sitio caído.

---

## 7. Fase B — Ensayo en seco (sin downtime, muy recomendado)

Sirve para descubrir problemas de dependencias, permisos y rutas **antes** de la ventana, con el droplet sirviendo con normalidad.

1. Saca una copia de la base con el método de §5.1 (se puede con el servicio corriendo) y transfiérela junto con `uploads/` y `.env`.
2. Carga **solo** el daemon del backend, **nunca** el del túnel:

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/com.grupoortiz.gocreate.backend.plist
```

3. Prueba en loopback, sin túnel:

```bash
curl -s http://127.0.0.1:8000/api/health                                      # {"status":"ok",...}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/               # 200 (build presente)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/creators/  # 401 (auth activa)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/docs           # 404 (ENV=production)
```

4. Verifica que los datos llegaron (script del paso 8).
5. **Descarga el daemon y borra los datos del ensayo** — en la ventana se transfiere un snapshot fresco:

```bash
sudo launchctl bootout system/com.grupoortiz.gocreate.backend
rm /opt/gocreate/app/backend/presupuesto.db
rm -rf /opt/gocreate/app/backend/uploads
```

> Los datos del ensayo **tienen que borrarse**. Si sobreviven, la Mac arranca en la ventana con una base de hace días y todo lo capturado en el intermedio se pierde.

---

## 8. Fase C — Ventana de migración (con downtime)

Ejecutar en orden. El downtime empieza en el paso 3 y termina en el paso 10.

### Paso 1 — Confirmar que no hay nadie trabajando

```bash
ssh root@100.99.205.35 'cd /root/Ready2Go/backend && venv/bin/python -c "
import sqlite3
c = sqlite3.connect(\"presupuesto.db\").cursor()
print(\"ultima actividad:\", c.execute(\"SELECT MAX(created_at) FROM audit_log\").fetchone()[0])"'
```

Si la última actividad es de hace minutos, espera. Esa marca está en **UTC**.

### Paso 2 — Respaldo de seguridad en el droplet

Independiente de la migración, por si algo se corrompe:

```bash
ssh root@100.99.205.35 '/root/Ready2Go/backend/venv/bin/python - <<PY
import sqlite3
src = sqlite3.connect("/root/Ready2Go/backend/presupuesto.db")
dst = sqlite3.connect("/root/backups/pre_migracion_macmini.db")
with dst: src.backup(dst)
dst.close(); src.close(); print("ok")
PY
tar -czf /root/backups/uploads_pre_migracion.tgz -C /root/Ready2Go/backend uploads'
```

### Paso 3 — 🔴 DETENER EL TÚNEL DEL DROPLET

Aquí empieza el downtime, y aquí se garantiza que no habrá dos réplicas (§3):

```bash
ssh root@100.99.205.35 'systemctl stop cloudflared-gocreate.service; systemctl is-active cloudflared-gocreate.service'
```

Debe imprimir `inactive`. `gocreate.mx` empieza a dar el error 1033 de Cloudflare. **Es lo esperado.**

### Paso 4 — Detener el backend del droplet

Congela las escrituras: desde aquí la base ya no cambia.

```bash
ssh root@100.99.205.35 'systemctl stop gocreate-backend.service; systemctl is-active gocreate-backend.service'
```

### Paso 5 — Desactivar el arranque automático del droplet

Si la máquina se reinicia sola durante o después de la migración, no debe volver a levantar el túnel y competir con la Mac:

```bash
ssh root@100.99.205.35 'systemctl disable cloudflared-gocreate.service gocreate-backend.service'
```

### Paso 6 — Snapshot final de los datos

```bash
ssh root@100.99.205.35 '/root/Ready2Go/backend/venv/bin/python - <<PY
import sqlite3
src = sqlite3.connect("/root/Ready2Go/backend/presupuesto.db")
dst = sqlite3.connect("/root/migracion_final.db")
with dst: src.backup(dst)
dst.close(); src.close(); print("db lista")
PY
tar -czf /root/migracion_uploads.tgz -C /root/Ready2Go/backend uploads
ls -la /root/migracion_final.db /root/migracion_uploads.tgz'
```

### Paso 7 — Transferir

Desde la Mac mini:

```bash
cd /opt/gocreate/app/backend

scp root@100.99.205.35:/root/migracion_final.db     ./presupuesto.db
scp root@100.99.205.35:/root/migracion_uploads.tgz  /tmp/
tar -xzf /tmp/migracion_uploads.tgz -C .            # crea ./uploads/

scp root@100.99.205.35:/root/Ready2Go/backend/.env  ./.env
chmod 600 .env

mkdir -p ~/.cloudflared
scp root@100.99.205.35:/root/.cloudflared/config.yml ~/.cloudflared/
scp root@100.99.205.35:/root/.cloudflared/2bb84bef-c493-4682-aa1e-4f2abc8e5164.json ~/.cloudflared/
chmod 400 ~/.cloudflared/2bb84bef-c493-4682-aa1e-4f2abc8e5164.json
```

Recuerda: **`cert.pem` no se copia** (§3).

`config.yml` referencia el `credentials-file` con la ruta del droplet, así que hay que **ajustarla** a la de la Mac. Debe quedar así:

```yaml
tunnel: 2bb84bef-c493-4682-aa1e-4f2abc8e5164
credentials-file: /Users/USUARIO_MAC/.cloudflared/2bb84bef-c493-4682-aa1e-4f2abc8e5164.json

ingress:
  - hostname: gocreate.mx
    service: http://127.0.0.1:8000
  - hostname: www.gocreate.mx
    service: http://127.0.0.1:8000
  - service: http_status:404
```

### Paso 8 — Verificar los datos ANTES de exponer el sitio

```bash
cd /opt/gocreate/app/backend && venv/bin/python - <<'PY'
import sqlite3
c = sqlite3.connect("presupuesto.db").cursor()
for t in ["users","creators","brands","tickets","general_expenses","operational_expenses",
          "expense_rubros","equipment","loan","loan_item","empresa","audit_log",
          "budget_cycles","user_role_grants","media_asset","responsiva_doc"]:
    print("%-24s %s" % (t, c.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]))
print("ultima auditoria:", c.execute("SELECT MAX(created_at) FROM audit_log").fetchone()[0])
PY
find uploads -type f | wc -l
```

Compara **cada número** con el mismo script corrido en el droplet. Si algo no cuadra, **detente** y repite los pasos 6-7. No sigas.

### Paso 9 — Arrancar el backend en la Mac y probar en loopback

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/com.grupoortiz.gocreate.backend.plist
sleep 3
curl -s http://127.0.0.1:8000/api/health
curl -s -o /dev/null -w 'raiz: %{http_code}\n' http://127.0.0.1:8000/
tail -20 /opt/gocreate/logs/backend.log
```

### Paso 10 — Arrancar el túnel (aquí termina el downtime)

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/com.grupoortiz.gocreate.cloudflared.plist
sleep 10
tail -30 /opt/gocreate/logs/cloudflared.log     # debe registrar 4 conexiones al edge
curl -s https://gocreate.mx/api/health
```

---

## 9. Verificación de salida

### Automática

```bash
curl -s https://gocreate.mx/api/health                                         # {"status":"ok","version":"1.0.0"}
curl -s -o /dev/null -w '%{http_code}\n' https://gocreate.mx/                  # 200  (SPA)
curl -s -o /dev/null -w '%{http_code}\n' https://www.gocreate.mx/api/health    # 200  (segundo hostname)
curl -s -o /dev/null -w '%{http_code}\n' https://gocreate.mx/api/creators/     # 401  (auth activa)
curl -s -o /dev/null -w '%{http_code}\n' https://gocreate.mx/docs              # 404  (ENV=production)
curl -s -o /dev/null -w '%{http_code}\n' https://gocreate.mx/transacciones     # 200  (fallback SPA)
```

### Manual, desde un navegador

- [ ] Login con una cuenta real de superadmin
- [ ] Los tres módulos aparecen según el rol: Presupuestos, Equipos, Gastos Operativos
- [ ] El dashboard de Presupuestos pinta cifras y gráficos
- [ ] Abrir un ticket existente y **ver su comprobante** (prueba que `uploads/tickets/` llegó y que las rutas relativas resuelven)
- [ ] Subir un ticket nuevo con imagen y verlo en el visor (prueba de escritura en disco)
- [ ] El inventario de Equipos lista los 9 equipos
- [ ] **Confirmar un préstamo de prueba y descargar su carta responsiva** (prueba el PDF, la emisora y `uploads/responsivas/`) — y cancelarlo después
- [ ] Gastos Operativos: catálogo de rubros visible

### Prueba de reinicio (no la omitas)

```bash
sudo reboot
```

Tras el arranque, **sin iniciar sesión gráfica**, `https://gocreate.mx/api/health` debe responder 200 solo. Si no, los plists no están bien cargados o falta `RunAtLoad`.

---

## 10. Rollback

Mientras el droplet siga intacto, volver cuesta ~2 minutos y **no requiere tocar DNS**:

```bash
# 1. Apagar la Mac como origen del túnel (primero, para no solapar réplicas)
sudo launchctl bootout system/com.grupoortiz.gocreate.cloudflared
sudo launchctl bootout system/com.grupoortiz.gocreate.backend

# 2. Revivir el droplet
ssh root@100.99.205.35 'systemctl enable --now gocreate-backend.service cloudflared-gocreate.service'
ssh root@100.99.205.35 'systemctl is-active gocreate-backend.service cloudflared-gocreate.service'

# 3. Verificar
curl -s https://gocreate.mx/api/health
```

**La ventana de reversibilidad se cierra cuando alguien escribe datos en la Mac.** A partir del primer ticket, gasto o préstamo creado ahí, un rollback pierde esa información: el droplet tiene el snapshot del paso 6, no lo posterior. Por eso la verificación de §9 va **inmediatamente** después del cutover, no al día siguiente.

Si hay que revertir cuando ya hubo escrituras, la base de la Mac es la buena: hay que traerla de vuelta al droplet con el método de §5.1, en sentido inverso.

---

## 11. Post-migración

### 11.1 Backups automáticos — cerrar el riesgo #1 del proyecto

`RISKS.md` #3 lleva abierto desde julio: **no hay backups de la base ni de `uploads/`**, y `uploads/` guarda cartas responsivas firmadas, que son evidencia. El droplet solo tiene respaldos manuales de despliegue. La migración es el momento natural para resolverlo.

Crear `/opt/gocreate/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail
FECHA=$(date +%F-%H%M)
DEST=/opt/gocreate/backups
APP=/opt/gocreate/app/backend

# Respaldo consistente incluso con la app corriendo (aplica el WAL, §5.1)
"$APP/venv/bin/python" - "$DEST/presupuesto-$FECHA.db" <<'PY'
import sqlite3, sys
src = sqlite3.connect("/opt/gocreate/app/backend/presupuesto.db")
dst = sqlite3.connect(sys.argv[1])
with dst:
    src.backup(dst)
dst.close(); src.close()
PY

tar -czf "$DEST/uploads-$FECHA.tar.gz" -C "$APP" uploads

# Retención 30 días
find "$DEST" -name 'presupuesto-*.db' -mtime +30 -delete
find "$DEST" -name 'uploads-*.tar.gz' -mtime +30 -delete
```

`chmod +x`, y un tercer LaunchDaemon con `StartCalendarInterval` (mismo esqueleto que §A.7, hora 3:17).

**Idealmente `DEST` apunta a un disco externo o NAS, no al disco del sistema** — un respaldo en el mismo disco no protege del fallo más probable. Y haz **una prueba de restauración** antes de dar la migración por cerrada.

### 11.2 Recordatorios de vencimiento (opcional)

Ver [[recordatorios_launchagent]]. Hoy no aplica: sin variables `SMTP_*` el script registra y no envía (§5.8). El plist de ese documento usa rutas `/Users/grupoortiz/GOCreate/…` — ajústalas a `/opt/gocreate/app/backend`.

### 11.3 Retirar el droplet

**No lo destruyas el mismo día.** Deja pasar al menos **7 días** de operación normal en la Mac. Mientras tanto queda como rollback y como copia de los datos previos al corte.

Cuando se decida apagarlo, en este orden:

1. Confirmar que los backups de la Mac corren y que una restauración funciona.
2. Bajar una copia final de `/root/backups/` a un lugar seguro.
3. Destruir el droplet.
4. **No** corras `cloudflared tunnel delete gocreate-produccion`: el túnel es el mismo y sigue vivo en la Mac. Borrarlo mataría el sitio.

### 11.4 Actualizar la documentación

Al cerrar la migración, corregir en el repo:

- `CLAUDE.md`, `README.md` y `status.md` — siguen afirmando "No desplegado, corre local en `127.0.0.1`". Ya era falso con el droplet.
- `RISKS.md` #7 y #9 (HTTPS y dominio) — resueltos por Cloudflare desde agosto.
- `docs/deploy/runbook.md` — marcar su §6 (Caddy) como no aplicable, o fusionarlo con este documento.

### 11.5 Procedimiento de actualización en la Mac (releases futuros)

```bash
cd /opt/gocreate/app
/opt/gocreate/backup.sh                       # respaldo antes de tocar nada
git pull
cd backend && venv/bin/pip install -r requirements.txt
cd ../frontend && npm ci && npx vite build
sudo launchctl kickstart -k system/com.grupoortiz.gocreate.backend
curl -s https://gocreate.mx/api/health
```

`cloudflared` **no** se reinicia en un release normal: solo si cambia `config.yml`.

---

## 12. Datos que faltan — llenar antes de ejecutar

| Dato | Valor | Quién lo tiene |
|---|---|---|
| Usuario de la Mac mini (`USUARIO_MAC`) | | Damián |
| IP Tailscale / MagicDNS de la Mac mini | | Se obtiene al unirla al tailnet (§A.1) |
| Credenciales SSH a la Mac mini | | Damián — **pendiente**, es lo único que bloquea la ejecución |
| Arquitectura (Apple Silicon / Intel) | | Define `/opt/homebrew` vs `/usr/local` en los plists |
| ¿Disco externo o NAS para backups? | | Damián / IT |
| Fecha y hora de la ventana | | Damián |
| ¿Se avisa a los usuarios? | | Damián |

Todo lo demás de este documento está verificado contra el servidor en vivo y no depende de esos datos.

---

## 13. Resumen para el operador — la versión de una pantalla

```
ANTES (sin downtime)
  Mac: Tailscale + no dormir + brew(python@3.12 node@20 git cloudflared sqlite)
  Mac: clone repo → venv + pip install → npm ci + vite build → plists creados
  Mac: ensayo en seco con copia de datos → BORRAR esa copia

VENTANA
   1. Verificar que nadie trabaja (MAX(created_at) de audit_log)
   2. Respaldo en el droplet
   3. systemctl stop cloudflared-gocreate      ← empieza el downtime
   4. systemctl stop gocreate-backend
   5. systemctl disable ambos
   6. Snapshot: sqlite backup + tar de uploads
   7. scp: db, uploads, .env, config.yml, <UUID>.json   (NUNCA cert.pem)
   8. Comparar conteos de filas               ← si no cuadra, PARAR
   9. launchctl bootstrap backend → probar en 127.0.0.1:8000
  10. launchctl bootstrap cloudflared          ← termina el downtime
  11. Verificación §9 completa, incluido un reboot

REGLAS DURAS
  · El túnel NUNCA corre en dos máquinas a la vez
  · Copiar el .db sin su WAL pierde días de datos
  · WorkingDirectory = backend/ o la app arranca vacía
  · --workers 1
  · ENV=production
  · No sembrar nada
  · cert.pem se queda en el droplet
```
