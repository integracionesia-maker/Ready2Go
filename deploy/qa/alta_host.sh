#!/bin/bash
# =============================================================================
# alta_host.sh — alta UNICA del entorno QA en la Mac mini (carril HOST, requiere root).
#
# Uso:   sudo ./alta_host.sh [--sudoers]
#
# Antes: copiar esta carpeta a la mini (desde la maquina de desarrollo):
#          scp -r deploy/qa gocreate-prod:~/qa
#        y verificar que /opt/go/bin/deploy-app.sh ya esta instalado (lo esta).
#
# Hace, en este orden, y es idempotente (se puede repetir sin romper nada):
#   1. Crea el usuario de servicio _gocreateqa (+ su grupo) con shell /usr/bin/false.
#   2. Crea /opt/go/gocreate-qa/ con sus subcarpetas, dueño _gocreateqa, modo 700.
#   3. Instala deploy/app.conf (root:wheel) y los dos plists en /Library/LaunchDaemons.
#   4. Genera shared/env/.env con un JWT_SECRET_KEY NUEVO (openssl). Nunca copia nada
#      del .env de produccion.
#   5. (--sudoers) valida con visudo e instala las reglas NOPASSWD acotadas al QA.
#
# NO hace: no toca /opt/go/gocreate ni com.go.gocreate.* (produccion), no arranca
# ningun servicio, no crea el tunel ni el DNS (eso va en el panel de Cloudflare;
# ver README.md §Tunel y acceso).
# =============================================================================
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Correr con sudo." >&2; exit 2; }
SRC="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_comun.sh
source "$SRC/_comun.sh"

CON_SUDOERS=0
[[ "${1:-}" == "--sudoers" ]] && CON_SUDOERS=1

for f in app.conf env.qa.example com.go.gocreate-qa.api.plist com.go.gocreate-qa.tunnel.plist sudoers-gocreate-qa.txt; do
  [ -f "$SRC/$f" ] || die "falta $SRC/$f (¿se copio toda la carpeta deploy/qa?)"
done
[ -x /opt/go/bin/deploy-app.sh ] || die "falta /opt/go/bin/deploy-app.sh"
[ -d "$PROD_BASE" ] || die "no existe $PROD_BASE: ¿esta es la Mac mini correcta?"

if lsof -nP -iTCP:"$QA_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  die "el puerto $QA_PORT ya esta en uso; elige otro en app.conf y en el plist antes de seguir."
fi

# --- 1. Usuario y grupo de servicio -----------------------------------------
if dscl . -read "/Users/$QA_USER" >/dev/null 2>&1; then
  info "usuario $QA_USER ya existe; no se toca."
else
  # Primer id (453..499) libre tanto para UID como para GID.
  N=""
  for cand in $(seq 453 499); do
    if ! dscl . -list /Users UniqueID | awk -v n="$cand" '$2==n{f=1} END{exit !f}' \
       && ! dscl . -list /Groups PrimaryGroupID | awk -v n="$cand" '$2==n{f=1} END{exit !f}'; then
      N="$cand"; break
    fi
  done
  [ -n "$N" ] || die "no hay un id libre entre 453 y 499 para el usuario de servicio."
  info "creando grupo y usuario $QA_USER con id $N..."
  dscl . -create "/Groups/$QA_USER"
  dscl . -create "/Groups/$QA_USER" PrimaryGroupID "$N"
  dscl . -create "/Groups/$QA_USER" Password "*"
  dscl . -create "/Users/$QA_USER"
  dscl . -create "/Users/$QA_USER" UserShell /usr/bin/false
  dscl . -create "/Users/$QA_USER" RealName "GOCreate QA (servicio)"
  dscl . -create "/Users/$QA_USER" UniqueID "$N"
  dscl . -create "/Users/$QA_USER" PrimaryGroupID "$N"
  dscl . -create "/Users/$QA_USER" NFSHomeDirectory /var/empty
  dscl . -create "/Users/$QA_USER" Password "*"
  dscl . -create "/Users/$QA_USER" IsHidden 1
fi

# --- 2. Estructura de carpetas ------------------------------------------------
info "creando $QA_BASE..."
for d in repo releases shared/data/uploads shared/env backups deploy logs tunnel incoming "home_${QA_SLUG}"; do
  mkdir -p "$QA_BASE/$d"
done
chown -R "$QA_USER:$QA_USER" "$QA_BASE"
# Modo 700 en el raiz y en lo sensible: ningun otro usuario del host (otras apps
# incluidas) puede entrar. Produccion hoy NO esta asi (ver INVENTARIO.md §Hallazgos).
chmod 700 "$QA_BASE" "$QA_BASE/shared" "$QA_BASE/shared/env" "$QA_BASE/shared/data" "$QA_BASE/tunnel"

# --- 3. app.conf y plists -------------------------------------------------------
install -m 0644 -o root -g wheel "$SRC/app.conf" "$QA_BASE/deploy/app.conf"
install -m 0644 -o root -g wheel "$SRC/com.go.gocreate-qa.api.plist" "$QA_PLIST_API"
install -m 0644 -o root -g wheel "$SRC/com.go.gocreate-qa.tunnel.plist" "$QA_PLIST_TUNNEL"
plutil -lint "$QA_PLIST_API" "$QA_PLIST_TUNNEL"

# --- 4. .env propio del QA --------------------------------------------------------
ENVF="$QA_BASE/shared/env/.env"
if [ -f "$ENVF" ]; then
  info ".env del QA ya existe; no se sobrescribe."
else
  SECRETO="$(openssl rand -hex 32)"
  ( umask 077; sed "s|__GENERADO_EN_EL_SERVIDOR__|${SECRETO}|" "$SRC/env.qa.example" > "$ENVF" )
  chown "$QA_USER:$QA_USER" "$ENVF"
  chmod 600 "$ENVF"
  info ".env del QA generado con un JWT_SECRET_KEY nuevo (no se muestra)."
fi

# --- 5. sudoers (opcional, con validacion previa) --------------------------------
if [ "$CON_SUDOERS" -eq 1 ]; then
  visudo -cf "$SRC/sudoers-gocreate-qa.txt" >/dev/null || die "sudoers-gocreate-qa.txt no pasa visudo -c; no se instala."
  install -m 0440 -o root -g wheel "$SRC/sudoers-gocreate-qa.txt" /etc/sudoers.d/integraciones-gocreate-qa
  visudo -c >/dev/null || { rm -f /etc/sudoers.d/integraciones-gocreate-qa; die "visudo -c fallo tras instalar; regla retirada."; }
  info "reglas sudo del QA instaladas en /etc/sudoers.d/integraciones-gocreate-qa"
else
  info "sudoers NO instalado (falta --sudoers). Sin esas reglas, los scripts piden contraseña de sudo."
fi

cat <<EOF

Alta lista. Siguientes pasos (ver README.md):
  1. Tunel y acceso en Cloudflare (hostname ${QA_HOSTNAME} -> http://127.0.0.1:${QA_PORT}); guardar el token en
       ${QA_BASE}/tunnel/tunnel.token  (permisos 600, dueño ${QA_USER}).
  2. Rama qa en GitHub:  git push origin master:qa   (desde la maquina de desarrollo).
  3. Primer deploy:      sudo /opt/go/bin/deploy-app.sh ${QA_SLUG}
  4. Sembrar datos:      ./reiniciar_datos.sh --si
  5. Encender el tunel:  ./encender.sh
  6. Verificar:          ./verificar_aislamiento.sh
EOF
