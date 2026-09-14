# Acceso y referencia rápida para desplegar GOCreate

> Complementa `docs/deploy/despliegue-continuo-multi-app.md` (el diseño del
> pipeline en sí, `deploy-app.sh`). Este documento es el resumen de "cómo
> llego yo (Claude, o quien sea) a poder correr un deploy sin fricción" —
> configurado el 14/09/2026, primera vez que se documentó este proceso
> completo de punta a punta.

## 1. Dónde vive todo (resumen de un vistazo)

| Qué | Valor |
|---|---|
| Host de producción | Mac mini de marketing (mkt) — **no** el droplet viejo (offline, decomisionado) |
| SSH (máquina de desarrollo → prod) | `ssh gocreate-prod` (alias en `~/.ssh/config`, mismo host que `crece-nueva`) |
| IP / Tailscale | `100.65.10.16`, tag `mac-mini-mkt` |
| Usuario SSH | `integraciones` (grupo `admin` de macOS, sudo requiere contraseña salvo las reglas de abajo) |
| Carpeta de GOCreate | `/opt/go/gocreate/` — aislada de `crece/` y `requis_*` (otros proyectos del mismo host) |
| Usuario de servicio | `_gocreate` (dueño real de `repo/`, `releases/`, `shared/`) |
| Rama que se despliega | `master` (siempre — alinear ramas primero, ver §3) |
| URL pública | `https://gocreate.mx` |
| `.env` real | `/opt/go/gocreate/shared/env/.env` (symlink a cada release; **no** vive en `repo/` ni en la release) |

## 2. Acceso ya configurado — no hay que rehacer esto

`/etc/sudoers.d/integraciones-claude` en la Mac mini ya tiene estas reglas (autorizadas explícitamente por Damian/integraciones.ia, dueño de la cuenta, el 14/09/2026):

```
integraciones ALL=(ALL) NOPASSWD: /bin/launchctl kickstart -k system/com.go.gocreate.api
integraciones ALL=(ALL) NOPASSWD: /bin/launchctl kickstart -k system/com.go.gocreate.tunnel
integraciones ALL=(ALL) NOPASSWD: /bin/launchctl print system/com.go.gocreate.api
integraciones ALL=(ALL) NOPASSWD: /bin/launchctl print system/com.go.gocreate.tunnel
integraciones ALL=(_gocreate) NOPASSWD: ALL
integraciones ALL=(ALL) NOPASSWD: /opt/go/bin/deploy-app.sh gocreate, /opt/go/bin/deploy-app.sh gocreate --force
```

Qué permite cada una, y por qué está acotada así (principio de mínimo privilegio — nunca se pidió sudo general):

- Las dos de `launchctl`: reiniciar/inspeccionar **solo** los dos demonios de GOCreate. No puede tocar el de `crece` ni el de `requis`.
- `ALL=(_gocreate) NOPASSWD: ALL`: actuar **como el usuario de servicio** `_gocreate` — que por diseño del host solo tiene acceso a `/opt/go/gocreate/`, nada de otros proyectos. Esto es lo que permite leer/editar `shared/env/.env`, hacer `git status`, etc. sin pedir contraseña.
- La de `deploy-app.sh`: correr el script oficial de deploy, pero con el argumento fijo `gocreate` (con o sin `--force`) — no puede desplegar `requis` con esta regla.

**Si esto algún día no funciona** (`sudo: a password is required`), es porque el archivo se editó/perdió — repetir el proceso con `sudo EDITOR=nano visudo -f /etc/sudoers.d/integraciones-claude` y pegar las 6 líneas de arriba. Verificar SIEMPRE con `visudo` (nunca editar el archivo a mano con otro editor) para no romper el `sudo` de todo el sistema.

## 3. Flujo completo de un deploy, de punta a punta

### 3.1 Alinear ramas (siempre primero — el deploy jala de `master`)

Desde la máquina de desarrollo, con `dami-branch` como fuente:

```bash
git stash push -u -m "..."           # si hay WIP sin commitear, apartarlo primero
git checkout master
git merge --no-ff dami-branch -m "merge: integra dami-branch en master (...)"
git push origin master

git checkout jose-branch && git merge master && git push origin jose-branch
git checkout BeniBranch  && git merge master && git push origin BeniBranch

git checkout dami-branch
git stash pop                        # si se apartó algo
```

En la práctica esto siempre ha sido un fast-forward limpio (jose-branch/BeniBranch no traen commits propios) — si algún día SÍ hay conflicto real, no resolverlo a ciegas: parar y preguntar (regla general de este proyecto).

### 3.2 El deploy en sí — un solo comando

```bash
ssh gocreate-prod "sudo -n /opt/go/bin/deploy-app.sh gocreate"
```

Es idempotente: si no hay commits nuevos y la app responde, no toca nada. Hace backup de DB/uploads, build del frontend, venv nuevo, corte de release, swap del LaunchDaemon, health check con **rollback automático** si algo falla. Todo queda en `/opt/go/gocreate/logs/deploy.log`.

### 3.3 Editar el `.env` de producción (agregar/cambiar variables)

Nunca sobreescribir el archivo entero — solo agregar, y siempre vía `_gocreate` (nunca como root directo, para no romper el dueño del archivo):

```bash
# Ver qué hay (nombres de variable, no valores, para no imprimir secretos sin querer):
ssh gocreate-prod "sudo -n -u _gocreate cat /opt/go/gocreate/shared/env/.env | sed 's/=.*/=.../'"

# Agregar variables nuevas (mandar el bloque por stdin, evita líos de comillas anidadas SSH):
cat bloque_nuevo.txt | ssh gocreate-prod "sudo -n -u _gocreate tee -a /opt/go/gocreate/shared/env/.env >/dev/null"
```

Un cambio de `.env` no requiere un deploy completo para tomar efecto — basta un restart:

```bash
ssh gocreate-prod "sudo -n /bin/launchctl kickstart -k system/com.go.gocreate.api"
```

### 3.4 Verificar que quedó bien, sin adivinar

```bash
# Health real:
ssh gocreate-prod "curl -s http://127.0.0.1:8000/api/health"

# Que el commit desplegado sea el esperado:
ssh gocreate-prod "cat /opt/go/gocreate/deploy/current.sha"

# Config de correo cargando bien, SIN mandar nada (lee el .env real, no envía):
ssh gocreate-prod "sudo -n -u _gocreate /opt/go/gocreate/releases/\$(ls -t /opt/go/gocreate/releases | head -1)/backend/venv/bin/python -c \"
import sys; sys.path.insert(0, '/opt/go/gocreate/releases/CAMBIAR/backend')
from dotenv import load_dotenv; load_dotenv('/opt/go/gocreate/shared/env/.env')
from app import mailer
cfg = mailer.config()
print(cfg.habilitado, cfg.host, cfg.remitente, cfg.bcc)
\""
```

## 4. Gotchas encontrados armando esto (14/09/2026)

- **Tailscale debe estar corriendo** en la máquina de desarrollo — si el host aparece "offline" en `tailscale status`, revisar ahí antes de asumir que el servidor está caído.
- **`gocreate-prod` (alias viejo) apuntaba al droplet decomisionado** — quedó corregido en `~/.ssh/config` (ver §1), pero si alguna vez vuelve a fallar la conexión, confirmar que el alias sigue apuntando a `100.65.10.16`, no a `100.99.205.35`.
- **Pertenecer al grupo `_gocreate` NO da permiso de escritura** — los directorios son `755` (solo lectura+ejecución de grupo). Hace falta `sudo -u _gocreate` para escribir de verdad, no basta con la membresía del grupo.
- **`sed` con backreferencias (`\1`) se comporta distinto en BSD/macOS que en GNU/Linux** — al redactar secretos en un output, verificar que sí se ocultó antes de compartirlo; no asumir que el patrón funcionó igual que en Linux.
- **Las reglas de `sudoers` exigen coincidencia exacta del comando** (incluidos los argumentos) — `sudo -n /opt/go/bin/deploy-app.sh` (sin el argumento `gocreate`) pide contraseña aunque la regla exista, porque el string no calza exacto. Siempre incluir los argumentos tal cual están en la regla.
