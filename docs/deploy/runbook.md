# Runbook de Deploy — Mac Mini on-premise (macOS, red local)

> Objetivo: dejar la app corriendo en la Mac Mini (`100.65.26.3`) con HTTPS, arranque automático al boot (launchd), backups y procedimiento de actualización. Sin Docker: para un solo servicio Python + estáticos, lo nativo es más simple y — importante — Docker Desktop en macOS requiere sesión de usuario iniciada, mientras que los LaunchDaemons corren desde el boot sin login.

**Arquitectura final:**

```
Clientes (LAN) ──HTTPS:443──> Caddy (macOS)
                                ├── /api/*  ──> uvicorn 127.0.0.1:8000 (LaunchDaemon)
                                └── /*      ──> frontend/dist (estáticos + fallback SPA)
```

Puntos clave de seguridad de esta topología:
- uvicorn escucha **solo en 127.0.0.1** — nadie en la red le habla directo.
- Caddy **solo** proxya `/api/*`: el mount estático `/uploads` del backend queda inalcanzable desde la red aunque siga montado.
- `ENV=production` activa cookies `Secure` (por eso HTTPS es obligatorio) y oculta `/docs`/`/redoc`.

---

## 0. Decisión previa: cómo obtener HTTPS en una LAN sin dominio público

La IP `100.65.26.3` pertenece al rango `100.64.0.0/10` que usa **Tailscale**. Confirma cuál es tu caso:

| Caso | Estrategia HTTPS |
|---|---|
| **A. La Mac está en un tailnet (Tailscale)** — recomendado si aplica | `tailscale cert` emite certificados Let's Encrypt **válidos** para el nombre MagicDNS de la máquina (ej. `macmini.tu-tailnet.ts.net`). Cero instalación de certificados en los clientes. |
| **B. LAN normal** | Caddy con `tls internal` (CA propia). Funciona igual, pero hay que **instalar la CA raíz de Caddy una vez en cada dispositivo cliente** (paso 6b). |

El runbook usa el hostname `HOSTAPP` como marcador — sustitúyelo por el nombre real (`macmini.tu-tailnet.ts.net` en caso A, o un nombre que resuelva en tu LAN/`/etc/hosts` como `presupuesto.grupo-ortiz.lan` en caso B).

---

## 1. Prerrequisitos en la Mac Mini (una sola vez)

```bash
# Homebrew (si no existe)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.12 node@20 caddy git sqlite

# La Mac no debe dormirse ni quedarse apagada tras un corte de luz
sudo pmset -a sleep 0 autorestart 1
sudo systemsetup -setcomputersleep Never
```

Estructura de directorios:

```bash
sudo mkdir -p /opt/presupuesto /opt/presupuesto/logs /opt/presupuesto/backups
sudo chown -R $(whoami) /opt/presupuesto
```

---

## 2. Llevar el código al servidor

El repo vive hoy solo en tu máquina de desarrollo. Dos opciones:

**Opción recomendada — remoto git privado** (GitHub/Gitea): en tu máquina de dev:
```bash
git remote add origin <url-repo-privado>
git push -u origin dami-branch master
```
En la Mac: `git clone <url-repo-privado> /opt/presupuesto/app`

**Opción sin remoto — git bundle por SSH**: en dev:
```bash
git bundle create presupuesto.bundle --all
scp presupuesto.bundle usuario@100.65.26.3:/opt/presupuesto/
```
En la Mac: `git clone /opt/presupuesto/presupuesto.bundle /opt/presupuesto/app`

> ⚠️ Deploya desde un estado **commiteado y probado** (pytest + `vite build` en verde) y — según tu propia política — desde `master` tras mergear `dami-branch` cuando el trabajo v2 esté listo.

Lo que **nunca** viaja con git (y está bien): `backend/.env`, `backend/presupuesto.db`, `backend/uploads/` — se crean en el servidor en los pasos siguientes.

---

## 3. Backend: venv, dependencias y .env de producción

```bash
cd /opt/presupuesto/app/backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Crear `/opt/presupuesto/app/backend/.env` (permisos restrictivos):

```bash
cat > .env <<EOF
ENV=production
JWT_SECRET_KEY=$( .venv/bin/python -c "import secrets; print(secrets.token_hex(32))" )
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://HOSTAPP
SUPERADMIN_USERNAME=superadmin
SUPERADMIN_EMAIL=superadmin@grupo-ortiz.com
SUPERADMIN_PASSWORD=
EOF
chmod 600 .env
```

- `JWT_SECRET_KEY` **nuevo** — jamás reutilices el de desarrollo.
- `SUPERADMIN_PASSWORD` vacío = el seed genera una contraseña temporal y la imprime **una sola vez** (más seguro que dejarla escrita en el archivo).

---

## 4. Primer arranque de datos (DB nueva + superadmin)

```bash
cd /opt/presupuesto/app/backend
set -a; source .env; set +a         # exporta las vars para el seed
.venv/bin/python seed_auth.py       # crea TODAS las tablas + superadmin
```

Guarda la contraseña temporal impresa. **NO ejecutes `seed.py` ni `seed_demo_year.py`** — son datos demo.

Alta de datos reales (después, ya con la app arriba, como superadmin): marcas y creadores desde Administración; usuarios desde la gestión de usuarios. Si primero cargas creadores y quieres generarles cuentas en lote: `.venv/bin/python seed_auth.py --vincular-creadores` (imprime contraseñas temporales; cada usuario la cambia en su primer login).

> Recordatorio: la cuenta `integraciones.ia` de desarrollo **no existirá aquí**. Recréala desde la UI de usuarios con contraseña fuerte (el seed se rehúsa a crear un segundo superadmin).

---

## 5. Frontend: build de producción

```bash
cd /opt/presupuesto/app/frontend
npm ci
npx vite build          # genera dist/
```

`dist/` lo sirve Caddy directamente — el dev server de Vite y su proxy NO se usan en producción.

---

## 6. Caddy (reverse proxy + HTTPS + cabeceras)

### 6a. Caddyfile

Crear `/opt/homebrew/etc/Caddyfile` (Apple Silicon; en Intel: `/usr/local/etc/Caddyfile`):

```caddyfile
https://HOSTAPP {
	# Caso A (Tailscale): comenta tls internal y usa
	#   tls /ruta/cert.crt /ruta/cert.key   (obtenidos con `tailscale cert HOSTAPP`)
	# Caso B (LAN normal): CA interna de Caddy
	tls internal

	encode gzip

	# API → backend local
	handle /api/* {
		reverse_proxy 127.0.0.1:8000
	}

	# SPA React: estáticos + fallback a index.html (react-router)
	handle {
		root * /opt/presupuesto/app/frontend/dist
		try_files {path} /index.html
		file_server
	}

	header {
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "DENY"
		Referrer-Policy "no-referrer"
		-Server
	}
}

# Redirigir HTTP → HTTPS
http://HOSTAPP {
	redir https://{host}{uri} permanent
}
```

Nota: NO se proxya `/uploads` — los comprobantes solo salen por el endpoint autenticado `/api/tickets/file/{id}`.

```bash
caddy validate --config /opt/homebrew/etc/Caddyfile
brew services start caddy      # lo registra en launchd, arranca al boot
```

(macOS ≥10.14 permite a procesos sin root enlazar los puertos 80/443 — no se necesita sudo.)

### 6b. Solo caso B: confiar la CA de Caddy en los clientes

En la Mac Mini, la CA raíz queda en `~/Library/Application Support/Caddy/pki/authorities/local/root.crt`. Distribúyela e instálala como confiable en cada dispositivo que usará la app (macOS: Acceso a Llaveros → confiar siempre; Windows: certmgr → Entidades raíz de confianza; iOS/Android: instalar perfil). Es **una vez por dispositivo**.

Y que `HOSTAPP` resuelva: entrada DNS en el router, o `/etc/hosts` (`100.65.26.3  HOSTAPP`) en cada cliente. (En caso A, MagicDNS de Tailscale ya resuelve solo.)

---

## 7. Backend como LaunchDaemon (arranca con el boot, sin login)

Crear `/Library/LaunchDaemons/com.grupoortiz.presupuesto.backend.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.grupoortiz.presupuesto.backend</string>
	<key>ProgramArguments</key>
	<array>
		<string>/opt/presupuesto/app/backend/.venv/bin/python</string>
		<string>-m</string>
		<string>uvicorn</string>
		<string>app.main:app</string>
		<string>--env-file</string>
		<string>.env</string>
		<string>--host</string>
		<string>127.0.0.1</string>
		<string>--port</string>
		<string>8000</string>
		<string>--workers</string>
		<string>1</string>
	</array>
	<key>WorkingDirectory</key>
	<string>/opt/presupuesto/app/backend</string>
	<key>UserName</key>
	<string>TU_USUARIO_MAC</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>StandardOutPath</key>
	<string>/opt/presupuesto/logs/backend.log</string>
	<key>StandardErrorPath</key>
	<string>/opt/presupuesto/logs/backend.err.log</string>
</dict>
</plist>
```

Reglas importantes ya reflejadas arriba: **sin `--reload`** (es de desarrollo), **`--workers 1`** obligatorio (SQLite + rate limiting en memoria no toleran multiproceso), `WorkingDirectory = backend/` (las rutas de DB y uploads son relativas al cwd).

```bash
sudo chown root:wheel /Library/LaunchDaemons/com.grupoortiz.presupuesto.backend.plist
sudo chmod 644 /Library/LaunchDaemons/com.grupoortiz.presupuesto.backend.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.grupoortiz.presupuesto.backend.plist
sudo launchctl kickstart -k system/com.grupoortiz.presupuesto.backend   # (re)inicia
```

---

## 8. Backups automáticos (DB + uploads)

Crear `/opt/presupuesto/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail
FECHA=$(date +%F)
DEST=/opt/presupuesto/backups
# Respaldo consistente de SQLite (seguro con la app corriendo)
/opt/homebrew/opt/sqlite/bin/sqlite3 /opt/presupuesto/app/backend/presupuesto.db \
  ".backup '$DEST/presupuesto-$FECHA.db'"
# Comprobantes
tar -czf "$DEST/uploads-$FECHA.tar.gz" -C /opt/presupuesto/app/backend uploads
# Retención: 14 días
find "$DEST" -name '*.db' -mtime +14 -delete
find "$DEST" -name '*.tar.gz' -mtime +14 -delete
```

`chmod +x /opt/presupuesto/backup.sh` y programarlo con un LaunchDaemon (`/Library/LaunchDaemons/com.grupoortiz.presupuesto.backup.plist`) con:

```xml
	<key>ProgramArguments</key>
	<array><string>/opt/presupuesto/backup.sh</string></array>
	<key>StartCalendarInterval</key>
	<dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>17</integer></dict>
```

(mismo esqueleto de plist que el del backend). **El disco de backups no debe ser el mismo disco** idealmente: apunta `DEST` a un disco externo o NAS si existe. Haz una **prueba de restauración** al menos una vez: copiar el `.db` a un entorno limpio y arrancar.

---

## 9. Endurecimiento del macOS

```bash
# Firewall de aplicación activado
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
# SSH solo con llaves (editar /etc/ssh/sshd_config): PasswordAuthentication no
# Actualizaciones de seguridad automáticas: Preferencias → General → Actualización
```

- La sesión gráfica puede quedar **sin usuario logueado** — los LaunchDaemons no la necesitan.
- No expongas 8000 en el firewall; solo 80/443 (Caddy). uvicorn ya escucha solo en loopback.

---

## 10. Verificación end-to-end (checklist de salida)

```bash
curl -k https://HOSTAPP/api/health          # {"status":"ok",...}
curl -k -o /dev/null -w '%{http_code}\n' https://HOSTAPP/api/creators/   # 401 (auth activa)
curl -k -o /dev/null -w '%{http_code}\n' https://HOSTAPP/docs            # 404 (oculto en prod)
curl -k -o /dev/null -w '%{http_code}\n' https://HOSTAPP/uploads/x       # 404 (no proxeado)
curl -k -o /dev/null -w '%{http_code}\n' https://HOSTAPP/transacciones   # 200 (fallback SPA)
```

Desde un cliente de la LAN: abrir `https://HOSTAPP` → sin advertencia de certificado (CA instalada o cert Tailscale) → login superadmin → **cambio de contraseña forzado** → crear marcas/creadores/usuarios → subir un ticket de prueba → verlo en el visor → reiniciar la Mac y confirmar que todo **vuelve solo** (backend + Caddy).

---

## 11. Procedimiento de actualización (cada release)

```bash
cd /opt/presupuesto/app
git pull                                    # o copiar bundle nuevo
cd backend && .venv/bin/pip install -r requirements.txt
cd ../frontend && npm ci && npx vite build
sudo launchctl kickstart -k system/com.grupoortiz.presupuesto.backend
# Caddy solo si cambió el Caddyfile: brew services restart caddy
```

Antes de cada actualización: correr `python -m pytest` en dev y hacer backup manual (`/opt/presupuesto/backup.sh`).

---

## 12. Operación y troubleshooting

| Situación | Comando |
|---|---|
| Ver logs backend | `tail -f /opt/presupuesto/logs/backend.err.log` |
| Reiniciar backend | `sudo launchctl kickstart -k system/com.grupoortiz.presupuesto.backend` |
| Estado del daemon | `sudo launchctl print system/com.grupoortiz.presupuesto.backend` |
| Reiniciar Caddy | `brew services restart caddy` |
| Contraseña de superadmin perdida | `cd /opt/presupuesto/app/backend && set -a; source .env; set +a; .venv/bin/python reset_superadmin_password.py` |
| ¿Quién escucha en 8000/443? | `sudo lsof -iTCP -sTCP:LISTEN -n -P` |

**Limitaciones conocidas de esta configuración** (aceptables en LAN, revisar si algún día sale a internet): SQLite con un solo worker (sin alta concurrencia), rate limiting en memoria (se resetea al reiniciar), sin CSP estricta (agregar en Caddy cuando el frontend esté estable), consultas del dashboard usan `strftime` de SQLite (migrar a Postgres implica reescribirlas).
