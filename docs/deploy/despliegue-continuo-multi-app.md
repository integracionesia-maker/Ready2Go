# Despliegue continuo multi-app en la Mac mini (GOCreate + Requisiciones)

> Objetivo: varios proyectos corriendo en la misma Mac mini (`100.65.10.16`), cada uno **clonado en su propia carpeta** y 100% aislado de los demás, con un mecanismo de actualización continuo: `sudo /opt/go/bin/deploy-app.sh <app>` jala de GitHub, construye y activa la versión nueva con rollback automático.
>
> Estado verificado el 01/09/2026: GOCreate ya sirve producción desde la Mac (patrón de releases, pero **sin tubería de actualización**: `repo/` vacío, único `.git` en detached HEAD). Requisiciones quedó a medias: plists registrados (puerto 8003, túnel `fff1c228-…`), código llegó como tarball (`incoming/requis_repo.tgz`) y `repo/` ya no existe — su servicio está en crash-loop. Este documento deja ambas apps en el mismo modelo operativo.
>
> El script vive en el repo: `docs/deploy/deploy-app.sh`. Quien corre los pasos necesita `sudo` en la Mac mini.

---

## 1. El modelo en una imagen

```
/opt/go/<app>/                     ← carpeta raíz de CADA proyecto (separadas siempre)
├── repo/                          ← EL clon git (rama master/main). De aquí se jala.
├── releases/<timestamp>/          ← versiones desplegadas (inmutables, con su venv)
├── shared/data/                   ← DB y uploads reales (sobreviven a cada release)
├── shared/env/.env                ← configuración real (un solo .env por app)
├── backups/                       ← respaldo automático en cada deploy
├── deploy/                        ← app.conf + copias de respaldo del plist
├── logs/                          ← logs del backend, del túnel y del deploy
└── home_<app>/                    ← HOME del usuario de servicio (caches npm/pip)
```

- El **repo** (`repo/`) es la fuente de actualización: `git pull` (fast-forward) sobre la rama configurada.
- Una **release** es una instantánea inmutable del repo con su propio `venv`; los datos se enlazan por symlink desde `shared/`. La app en producción **nunca** se toca durante un build: si algo falla, queda corriendo la release anterior.
- Cada app tiene su **usuario de servicio** (`_gocreate`, `_requis`), su **puerto** (8000, 8003), su **LaunchDaemon** y su **túnel** propios. Ningún proceso comparte nada con otro proyecto.

## 2. Reglas de aislamiento (lo que garantiza que nunca se afecten)

| Qué | Regla |
|---|---|
| Usuario | un usuario de servicio por app; la carpeta `/opt/go/<app>` es `700` de ese usuario |
| Código | un clon git por app, en `/opt/go/<app>/repo` |
| Python | un venv **por release**, creado desde cero en cada deploy |
| Node | `node_modules` vive en el repo de cada app; el build corre en el repo, no en la release |
| Datos | DB/uploads/.env por app, en `shared/`, enlazados solo a sus releases |
| Red | backend escucha solo `127.0.0.1` en su propio puerto; cada app tiene su túnel cloudflared |
| Procesos | un LaunchDaemon por app (`com.go.<app>.api`); el script reinicia **solo** el de la app que despliega |
| Script | valida el nombre de app contra `^[a-z0-9_-]+$` y no escribe nada fuera de `/opt/go/<app>/` y su plist; jamás toca túneles |

## 3. Prerrequisitos (ya verificados en la Mac)

- Homebrew con `python@3.12` (3.12.14) y `node@22` — las rutas están fijas en el script.
- `rsync` y `/usr/libexec/PlistBuddy` — incluidos en macOS.
- Usuarios `_gocreate` y `_requis` — ya existen.
- Requisiciones es repo **privado**: necesita su deploy key SSH registrada en GitHub (§6, paso 1). GOCreate es público y usa HTTPS sin llave.

## 4. Instalación única del script

```bash
# En la Mac mini, como usuario con sudo (integraciones):
sudo cp /Users/integraciones/Downloads/deploy-app.sh /opt/go/bin/deploy-app.sh
sudo chown root:wheel /opt/go/bin/deploy-app.sh
sudo chmod 755 /opt/go/bin/deploy-app.sh
```

(Alternativa: copiarlo desde la máquina de desarrollo con `scp docs/deploy/deploy-app.sh integraciones@100.65.10.16:~/Downloads/`.)

## 5. Configuración de GOCreate

```bash
sudo mkdir -p /opt/go/gocreate/deploy
sudo tee /opt/go/gocreate/deploy/app.conf > /dev/null <<'CONF'
APP_NAME=gocreate
SERVICE_USER=_gocreate
SERVICE_LABEL=com.go.gocreate.api
REPO_URL=https://github.com/integracionesia-maker/Ready2Go.git
BRANCH=master
# GIT_SSH_KEY=                 # repo público: sin llave
PORT=8000
HEALTH_PATH=/api/health
PYTHON_BIN=/opt/homebrew/opt/python@3.12/bin/python3.12
BACKEND_SUBDIR=backend
REQUIREMENTS=backend/requirements.txt
FRONTEND_DIR=frontend
NPM_BUILD_CMD="npm run build"
ENV_FILE=backend/.env
DATA_LINKS=("backend/presupuesto.db:shared/data/presupuesto.db"
            "backend/uploads:shared/data/uploads")
KEEP_RELEASES=3
BACKUP_KEEP=7
CONF
sudo chown root:wheel /opt/go/gocreate/deploy/app.conf
```

### Bootstrap de GOCreate (una sola vez)

La app ya corre desde `releases/20260831-150253/`. Solo falta el clon y registrar qué commit está desplegado:

```bash
# 1. Clonar el repo en repo/ (rama master, LF estricto)
sudo mkdir -p /opt/go/gocreate/repo
sudo chown _gocreate:_gocreate /opt/go/gocreate/repo
sudo -u _gocreate env HOME=/opt/go/gocreate/home_gocreate \
  git clone -c core.autocrlf=input --branch master \
  https://github.com/integracionesia-maker/Ready2Go.git /opt/go/gocreate/repo

# 2. Registrar el commit que YA está desplegado (6ebcb56 == master hoy),
#    para que el primer run del script no corte una release idéntica
sudo -u _gocreate git -C /opt/go/gocreate/repo rev-parse HEAD \
  | sudo tee /opt/go/gocreate/deploy/current.sha > /dev/null
sudo chown _gocreate:_gocreate /opt/go/gocreate/deploy/current.sha

# 3. Mover el .env a shared/env/ (deja de vivir dentro de la release)
sudo mkdir -p /opt/go/gocreate/shared/env
sudo cp /opt/go/gocreate/releases/20260831-150253/backend/.env /opt/go/gocreate/shared/env/.env
sudo chown _gocreate:_gocreate /opt/go/gocreate/shared/env/.env
sudo chmod 600 /opt/go/gocreate/shared/env/.env

# 4. Prueba en seco (no debe cortar nada):
sudo /opt/go/bin/deploy-app.sh gocreate
#    → "Sin commits nuevos (6ebcb56…) y la app responde; no hay nada que hacer."
```

> El `.env` de la release vieja puede quedarse; el de verdad pasa a ser `shared/env/.env` y cada release nueva lo recibe por symlink. **No** se toca el `ENV=production`.

## 6. Configuración de Requisiciones

### Paso 0 — la deploy key ya existe; solo verificar que autentica

La llave de solo lectura **ya está registrada en GitHub** (`/opt/go/requis/.ssh/id_ed25519_deploy`, owner `_requis`, configurada en el repo vía `core.sshCommand`). **No se crea ninguna segunda llave** — el pipeline reutiliza esta misma (el `GIT_SSH_KEY` del `app.conf` apunta a ella y el script arma el `GIT_SSH_COMMAND` equivalente).

Verificación rápida antes del primer deploy:

```bash
sudo -u _requis env HOME=/opt/go/requis/home_requis \
  ssh -i /opt/go/requis/.ssh/id_ed25519_deploy \
  -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -T git@github.com
```

- `Hi <repo>! You've successfully authenticated…` → todo listo, seguir con el paso 1.
- `Permission denied` → la llave perdió el registro en GitHub; re-agregar **esta misma** llave pública (`id_ed25519_deploy.pub`) como Deploy key de solo lectura, no generar una nueva.

### Paso 1 — configurar

```bash
sudo tee /opt/go/requis/deploy/app.conf > /dev/null <<'CONF'
APP_NAME=requis
SERVICE_USER=_requis
SERVICE_LABEL=com.go.requis.api
REPO_URL=git@github.com:gerardoaguilar-ing/automatizacion_requisiciones.git
BRANCH=main
GIT_SSH_KEY=/opt/go/requis/.ssh/id_ed25519_deploy
PORT=8003
HEALTH_PATH=/api/health          # AJUSTAR si la app expone otra ruta
PYTHON_BIN=/opt/homebrew/opt/python@3.12/bin/python3.12
BACKEND_SUBDIR=.
REQUIREMENTS=requirements.txt
FRONTEND_DIR=frontend
NPM_BUILD_CMD="npm run build"
ENV_FILE=.env                    # AJUSTAR según dónde lo lea la app
DATA_LINKS=()                    # COMPLETAR tras ubicar su DB y uploads (§7)
KEEP_RELEASES=3
BACKUP_KEEP=7
CONF
sudo chown root:wheel /opt/go/requis/deploy/app.conf
```

### Paso 2 — ubicar sus datos (DB, uploads, .env)

Antes del primer deploy hay que saber dónde guarda sus datos la app y declararlo en `DATA_LINKS`. Diagnóstico rápido:

```bash
sudo -u _requis grep -rn "sqlite3.connect\|\.db\b" /opt/go/requis/repo --include="*.py" 2>/dev/null | head
sudo -u _requis grep -rn "uploads\|UPLOAD" /opt/go/requis/repo --include="*.py" 2>/dev/null | head
```

- Si la DB es `algo.db` en la raíz del repo → moverla a `shared/data/` y declarar `DATA_LINKS=("algo.db:shared/data/algo.db")`.
- Mismo trato para `uploads/` y para su `.env` (→ `shared/env/.env`, `ENV_FILE=.env`).
- Las variables que requiere su `.env` están fuera del alcance de este doc — confirmarlas con el autor del proyecto (Gerardo) o leyendo su `.env.example`.
- La contraseña, el tarball `incoming/requis_repo.tgz` (7 MB) queda como archivo histórico; **la fuente de verdad pasa a ser `git@github.com:…`, no el tarball**.

### Paso 3 — primer deploy

```bash
# El script clona solo si falta repo/ (hoy falta), corta la release 1,
# apunta la plist (que hoy apunta a /opt/go/requis/repo) y reinicia.
sudo /opt/go/bin/deploy-app.sh requis

# Verificar:
curl -s http://127.0.0.1:8003/api/health        # o la HEALTH_PATH real
launchctl print system/com.go.requis.api | grep -E "state|pid"
```

> La plist actual usa `/opt/go/requis/repo/venv`; tras este paso usa `releases/<ts>/venv`. El venv viejo dentro de `repo/` (si reaparece al clonar) queda obsoleto — el script excluye `venv` de las releases. Si algo falla, el script hace rollback automático a lo que la plist apuntaba antes.

## 7. Flujo de actualización continua (el día a día)

```bash
sudo /opt/go/bin/deploy-app.sh gocreate     # actualiza GOCreate
sudo /opt/go/bin/deploy-app.sh requis       # actualiza Requisiciones
```

Qué hace por dentro (idempotente, repetible sin miedo):

1. `git fetch` + fast-forward de la rama (si el repo tiene cambios locales → **aborta**, nunca fuerza).
2. Si no hay commits nuevos y la app responde → termina sin tocar nada.
3. Respaldo consistente de la DB (API de sqlite, aplica el WAL) y tar de uploads.
4. `npm install && npm run build` en el repo (si falla, la app en producción queda intacta).
5. Corta `releases/<ts>/` con venv nuevo y `pip install` (si falla, descarta la release).
6. Apunta el LaunchDaemon a la release nueva, `launchctl kickstart -k`.
7. Health check en `127.0.0.1:<puerto><HEALTH_PATH>` — si falla, **rollback automático** a la release anterior.
8. Poda: conserva las últimas 3 releases y los últimos 7 respaldos.

Requisitos para que "actualiza la app" siga significando lo mismo que antes:

- **Mergear a master/main primero** (GOCreate: `dami-branch` → `master`; Requis: su flujo → `main`). El deploy jala de la rama principal, igual que el droplet.
- Los túneles de cloudflared **no** se reinician en un deploy normal: solo si cambia el `config.yml` del túnel.

Si hace falta redeployar la misma versión (p. ej. la app se cayó): `sudo /opt/go/bin/deploy-app.sh <app> --force`.

## 8. Rollback manual (si el automático no alcanzara)

```bash
# Ver qué apunta la plist y qué releases existen:
/usr/libexec/PlistBuddy -c "Print :WorkingDirectory" /Library/LaunchDaemons/com.go.gocreate.api.plist
ls -1 /opt/go/gocreate/releases

# Volver a una release anterior:
sudo /usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 /opt/go/gocreate/releases/20260831-150253/backend/venv/bin/python" /Library/LaunchDaemons/com.go.gocreate.api.plist
sudo /usr/libexec/PlistBuddy -c "Set :WorkingDirectory /opt/go/gocreate/releases/20260831-150253/backend" /Library/LaunchDaemons/com.go.gocreate.api.plist
sudo launchctl kickstart -k system/com.go.gocreate.api
```

## 9. Agregar una tercera app (checklist)

1. Crear su usuario de servicio y su carpeta `/opt/go/<app>` (carril HOST, con Gerardo).
2. Clonar su repo en `/opt/go/<app>/repo` (con deploy key si es privado).
3. Crear `/opt/go/<app>/deploy/app.conf` (copiar §5 o §6 y ajustar puerto, subdirs, datos).
4. Registrar sus LaunchDaemons `com.go.<app>.api` y `.tunnel` (misma forma que los existentes).
5. `sudo /opt/go/bin/deploy-app.sh <app>` — el script hace el resto.

## 10. Lecciones que este diseño incorpora

- **CRLF/LF**: Requisiciones vivió el "todo el repo aparece modificado" por line endings. El script clona con `core.autocrlf=input` y lo re-aplica en cada sync.
- **WAL de SQLite**: copiar solo el `.db` pierde días de datos; el respaldo usa `sqlite3.Connection.backup()`, que aplica el WAL.
- **Un solo worker** (`--workers 1`): lo fija la plist de cada app; el script no la altera.
- **Rutas relativas al cwd**: el plist lleva `WorkingDirectory` a la release; el script lo actualiza en cada corte.
- **Nunca `git pull --force`/`reset` en el repo de deploy**: si hay cambios locales, el script aborta y pide revisión manual.
- **El túnel corre en una sola máquina**: los deploys nunca tocan los servicios `.tunnel`.

## 11. Pendientes por confirmar

| Pendiente | Quién |
|---|---|
| `HEALTH_PATH`, variables de `.env` y ubicación de DB/uploads de Requisiciones (§6 paso 2) | Autor de Requis (Gerardo) / Damián |
| ~~Deploy key de Requis en GitHub~~ ✅ ya registrada (solo lectura, `id_ed25519_deploy`); reutilizarla, no crear otra | — |
| Coordinar la ejecución del bootstrap con el carril HOST | Gerardo |
| Confirmar que `node@22` es la versión que usa el build de Requis | Autor de Requis |

---

> Este documento sustituye el §11.5 del runbook de migración (`migracion-macmini.md`), que describía un flujo de actualización en sitio que nunca se construyó. El script `deploy-app.sh` es ahora la fuente de verdad del despliegue continuo.
