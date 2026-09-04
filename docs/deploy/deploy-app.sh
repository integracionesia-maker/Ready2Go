#!/bin/bash
# =============================================================================
# deploy-app.sh — despliegue continuo por releases para las apps de /opt/go
#
# Uso:      sudo /opt/go/bin/deploy-app.sh <app> [--force]
# Ejemplos: sudo /opt/go/bin/deploy-app.sh gocreate
#           sudo /opt/go/bin/deploy-app.sh requis
#
# Modelo: cada app vive aislada en /opt/go/<app> con su propio usuario de
# servicio, repo clonado, venv, node_modules, puerto y LaunchDaemon. El script
# solo toca /opt/go/<app>/ y el plist de ESA app — nunca los túneles de
# cloudflared ni otras apps — así que los proyectos no se afectan entre sí.
#
# Flujo (idempotente: si no hay commits nuevos y la app está sana, no toca nada):
#   1. clone (primera vez) o fetch + fast-forward de la rama configurada
#   2. respaldo de datos: sqlite .backup (aplica el WAL) + tar de uploads
#   3. build del frontend (npm) en el repo — si falla, se aborta SIN tocar
#      la app que está corriendo
#   4. venv NUEVO con pip install en la release (nunca se reutiliza el viejo)
#   5. release en releases/<timestamp>/: copia del repo sin .git, venv,
#      node_modules, datos ni .env (esos van por symlink desde shared/)
#   6. apunta el LaunchDaemon a la release nueva y reinicia el servicio
#   7. health check con rollback AUTOMÁTICO a la release anterior si falla
#   8. poda de releases y respaldos viejos
#
# Requisitos: macOS con sudo, rsync, /usr/libexec/PlistBuddy, Homebrew con
# python@3.12 y node@22 (rutas en el PATH más abajo).
# =============================================================================
set -euo pipefail

APP="${1:?Uso: sudo $0 <app> [--force]}"
FORCE=0
[[ "${2:-}" == "--force" ]] && FORCE=1

# Validación estricta del nombre (evita rutas raras fuera de /opt/go)
[[ "$APP" =~ ^[a-z0-9_-]+$ ]] || { echo "Nombre de app inválido: $APP" >&2; exit 2; }

BASE="/opt/go/$APP"
CONF="$BASE/deploy/app.conf"
[[ -f "$CONF" ]] || { echo "Falta la configuración $CONF" >&2; exit 2; }
# shellcheck disable=SC1090
source "$CONF"

[ "$(id -u)" -eq 0 ] || { echo "Correr con sudo." >&2; exit 2; }

# --- rutas derivadas ---------------------------------------------------------
REPO_DIR="$BASE/repo"
RELEASES_DIR="$BASE/releases"
SHARED_DATA="$BASE/shared/data"
BACKUPS_DIR="$BASE/backups"
DEPLOY_DIR="$BASE/deploy"
APP_HOME="$BASE/home_$APP"
PLIST="/Library/LaunchDaemons/com.go.$APP.api.plist"
LOG_FILE="$BASE/logs/deploy.log"
HEALTH_PATH="${HEALTH_PATH:-/api/health}"
BACKEND_SUBDIR="${BACKEND_SUBDIR:-backend}"
KEEP_RELEASES="${KEEP_RELEASES:-3}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"
TS="$(date +%Y%m%d-%H%M%S)"

# Homebrew visible para el usuario de servicio (sudo recorta el PATH)
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/node@22/bin:/opt/homebrew/opt/python@3.12/bin:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p "$BASE/logs" "$BACKUPS_DIR" "$DEPLOY_DIR" "$RELEASES_DIR"

# log va a stderr para no contaminar los $(...) que capturan stdout
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_FILE" >&2; }
die() { log "ERROR: $*"; exit 1; }

as_user() { sudo -u "$SERVICE_USER" env HOME="$APP_HOME" PATH="$PATH" "$@"; }

# Git como el usuario de servicio, con la llave SSH si la app la declara.
run_git() {
  local env_args=(env HOME="$APP_HOME" PATH="$PATH")
  if [ -n "${GIT_SSH_KEY:-}" ]; then
    # known_hosts persistido en la carpeta de la app: el HOME de los
    # usuarios de servicio suele ser /var/empty y ssh no puede escribir ahí
    env_args+=(GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$BASE/.ssh/known_hosts")
  fi
  sudo -u "$SERVICE_USER" "${env_args[@]}" "$@"
}

# ----------------------------------------------------------------------------
# Git: clone la primera vez, después fetch + fast-forward. Nunca --force.
# ----------------------------------------------------------------------------
git_sync() {
  if [ ! -d "$REPO_DIR/.git" ]; then
    log "Primera vez: clonando $REPO_URL (rama $BRANCH)…"
    mkdir -p "$REPO_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$REPO_DIR"
    run_git git clone -c core.autocrlf=input --branch "$BRANCH" "$REPO_URL" "$REPO_DIR" \
      || die "no se pudo clonar (¿deploy key agregada en GitHub para repos privados?)"
  else
    log "Fetch + fast-forward de origin/$BRANCH…"
    run_git git -C "$REPO_DIR" config core.autocrlf input
    run_git git -C "$REPO_DIR" fetch origin
    if [ -n "$(run_git git -C "$REPO_DIR" status --porcelain)" ]; then
      die "el repo $REPO_DIR tiene cambios locales; revísalo a mano (aquí nunca se fuerza el pull)."
    fi
    run_git git -C "$REPO_DIR" checkout "$BRANCH"
    run_git git -C "$REPO_DIR" merge --ff-only "origin/$BRANCH"
  fi
}

deployed_sha() { cat "$DEPLOY_DIR/current.sha" 2>/dev/null || true; }

# stdout = sha a desplegar (solo si hay que desplegar); return 1 = no hacer nada
needs_deploy() {
  local new old
  new="$(run_git git -C "$REPO_DIR" rev-parse HEAD)"
  old="$(deployed_sha)"
  [ "$FORCE" -eq 1 ] && { echo "$new"; return 0; }
  if [ -n "$old" ] && [ "$old" = "$new" ]; then
    if health_check 1; then
      log "Sin commits nuevos ($new) y la app responde; no hay nada que hacer."
      return 1
    fi
    log "La app no responde con la versión actual; se corta release de $new igualmente."
  fi
  echo "$new"
}

# ----------------------------------------------------------------------------
# Respaldo de datos (API de sqlite — aplica el WAL — y tar de uploads)
# ----------------------------------------------------------------------------
backup_data() {
  [ -d "$SHARED_DATA" ] || return 0
  local py
  py="$(/usr/libexec/PlistBuddy -c "Print :ProgramArguments:0" "$PLIST" 2>/dev/null || true)"
  if [ ! -x "$py" ]; then
    log "Sin venv activo aún; se omite el respaldo de DB."
    return 0
  fi
  local db
  for db in "$SHARED_DATA"/*.db; do
    [ -f "$db" ] || continue
    log "Respaldo consistente de $(basename "$db")…"
    sudo -u "$SERVICE_USER" env HOME="$APP_HOME" "$py" - "$db" "$BACKUPS_DIR/$(basename "$db" .db)-$TS.db" <<'PY' \
      || die "falló el respaldo de $db"
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
with dst:
    src.backup(dst)
dst.close(); src.close()
PY
  done
  if [ -d "$SHARED_DATA/uploads" ]; then
    tar -czf "$BACKUPS_DIR/uploads-$TS.tgz" -C "$SHARED_DATA" uploads
    log "uploads respaldados: uploads-$TS.tgz"
  fi
  # poda de respaldos viejos
  ls -1t "$BACKUPS_DIR" | tail -n +"$((BACKUP_KEEP + 1))" | while read -r f; do
    rm -f "$BACKUPS_DIR/$f"
  done || true
}

# ----------------------------------------------------------------------------
# Build del frontend en el repo (la app que está corriendo no se toca)
# ----------------------------------------------------------------------------
build_frontend() {
  [ -n "${FRONTEND_DIR:-}" ] || return 0
  log "Build del frontend ($FRONTEND_DIR)…"
  as_user bash -c "cd '$REPO_DIR/$FRONTEND_DIR' && npm install --no-audit --no-fund && ${NPM_BUILD_CMD:-npm run build}" \
    || die "falló el build del frontend; la app en producción no fue tocada."
}

# ----------------------------------------------------------------------------
# .env: vive una sola vez en shared/env/ y se enlaza a cada release
# ----------------------------------------------------------------------------
ensure_shared_env() {
  [ -n "${ENV_FILE:-}" ] || return 0
  local shared="$BASE/shared/env/.env"
  [ -f "$shared" ] && return 0
  local wd real
  wd="$(/usr/libexec/PlistBuddy -c "Print :WorkingDirectory" "$PLIST" 2>/dev/null || true)"
  real="${wd:+$wd/}$ENV_FILE"
  if [ -f "$real" ]; then
    mkdir -p "$BASE/shared/env"
    cp "$real" "$shared"
    chown "$SERVICE_USER:$SERVICE_USER" "$shared"
    chmod 600 "$shared"
    log "Migrado .env a $shared"
  else
    log "AVISO: no existe .env en shared/env ni en la release activa ($real);"
    log "       créalo en $shared antes del primer corte."
  fi
}

# ----------------------------------------------------------------------------
# Corte de release: copia del repo + venv nuevo + symlinks de datos
# ----------------------------------------------------------------------------
cut_release() {
  local release="$RELEASES_DIR/$TS"
  log "Cortando release $release…"
  rsync -a \
    --exclude='.git' --exclude='.ssh' --exclude='node_modules' \
    --exclude='venv' --exclude='backend/venv' --exclude='__pycache__' \
    --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' \
    --exclude='uploads' --exclude='.env' \
    "$REPO_DIR/" "$release/"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$release"

  local vdir="$release/$BACKEND_SUBDIR/venv"
  log "Creando venv nuevo e instalando dependencias…"
  as_user "$PYTHON_BIN" -m venv "$vdir"
  as_user "$vdir/bin/pip" install --quiet -r "$release/${REQUIREMENTS}" \
    || { rm -rf "$release"; die "falló pip install; release descartada y la app intacta."; }

  local par
  for par in ${DATA_LINKS[@]+"${DATA_LINKS[@]}"}; do
    [ -n "$par" ] || continue
    local rel="${par%%:*}" tgt="${par#*:}"
    rm -rf "$release/$rel"
    ln -s "$BASE/$tgt" "$release/$rel"
  done

  if [ -n "${ENV_FILE:-}" ] && [ -f "$BASE/shared/env/.env" ]; then
    rm -f "$release/$ENV_FILE"
    ln -s "$BASE/shared/env/.env" "$release/$ENV_FILE"
  fi

  echo "$release"
}

# ----------------------------------------------------------------------------
# LaunchDaemon: leer estado actual, apuntar a la release nueva, reiniciar
# ----------------------------------------------------------------------------
plist_get() { /usr/libexec/PlistBuddy -c "Print :$1" "$PLIST" 2>/dev/null || true; }
plist_set() { /usr/libexec/PlistBuddy -c "Set :$1 $2" "$PLIST" >/dev/null; }

health_check() {
  # El origen "responde" aunque sea con 3xx/4xx (no todas las apps tienen
  # /api/health). Solo el código 000 (connection refused/timeout) es caída.
  local tries="${1:-20}" code
  for ((i = 1; i <= tries; i++)); do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${PORT}${HEALTH_PATH}" 2>/dev/null || true)"
    [ -n "$code" ] && [ "$code" != "000" ] && return 0
    sleep 1.5
  done
  return 1
}

swap_release() {
  local release="$1"
  local py_dir="$release/$BACKEND_SUBDIR" wd_dir="$release/$BACKEND_SUBDIR"
  if [ "$BACKEND_SUBDIR" = "." ]; then
    py_dir="$release"; wd_dir="$release"
  fi
  cp "$PLIST" "$DEPLOY_DIR/$(basename "$PLIST").bak-$TS"
  plist_set "ProgramArguments:0" "$py_dir/venv/bin/python"
  plist_set "WorkingDirectory" "$wd_dir"
  # kickstart -k NO recarga un plist editado; launchd conserva la config
  # vieja en caché. Para que tome los paths nuevos: bootout + bootstrap.
  if launchctl print "system/$SERVICE_LABEL" >/dev/null 2>&1; then
    launchctl bootout "system/$SERVICE_LABEL" 2>/dev/null || true
    sleep 1
  fi
  launchctl bootstrap system "$PLIST" || die "no se pudo (re)cargar el servicio $SERVICE_LABEL"
  sleep 3
}

rollback_to() {
  local release="$1"
  log "ROLLBACK: restaurando $release…"
  swap_release "$release"
  if health_check; then
    log "Rollback exitoso; la app quedó sirviendo la release anterior."
  else
    log "CRÍTICO: la app tampoco responde tras el rollback. Revisar $LOG_FILE y el plist."
  fi
  exit 1
}

# ----------------------------------------------------------------------------
main() {
  log "=== deploy de $APP ($TS) ==="

  # Release activa según el plist (por si hay que rodar atrás)
  local prev_wd
  prev_wd="$(plist_get WorkingDirectory)"

  git_sync

  local new_sha
  new_sha="$(needs_deploy)" || exit 0

  ensure_shared_env
  backup_data
  build_frontend

  local release
  release="$(cut_release)"

  log "Apuntando el servicio a la release nueva…"
  swap_release "$release"

  if health_check; then
    log "Health check OK: http://127.0.0.1:${PORT}${HEALTH_PATH}"
  else
    log "Health check FALLÓ con la release nueva; rodando atrás…"
    rollback_to "$prev_wd"
  fi

  echo "$new_sha" > "$DEPLOY_DIR/current.sha"
  chown "$SERVICE_USER:$SERVICE_USER" "$DEPLOY_DIR/current.sha"
  log "Desplegado commit $new_sha en $release"

  # poda de releases viejas (nunca la activa ni la anterior)
  local count active_b prev_b old
  active_b="$(basename "$release")"
  prev_b="$(basename "$prev_wd")"
  count="$(ls -1 "$RELEASES_DIR" | wc -l | tr -d ' ')"
  for old in $(ls -1r "$RELEASES_DIR"); do
    [ "$old" = "$active_b" ] && continue
    [ "$old" = "$prev_b" ] && continue
    if [ "$count" -gt "$KEEP_RELEASES" ]; then
      log "Podando release vieja: $old"
      rm -rf "$RELEASES_DIR/$old"
      count=$((count - 1))
    fi
  done

  log "=== deploy completado ==="
  run_git git -C "$REPO_DIR" log --oneline -1 | tee -a "$LOG_FILE" >&2
  log "Releases actuales:"
  ls -1 "$RELEASES_DIR" | sed 's/^/    /' | tee -a "$LOG_FILE" >&2
}

main
