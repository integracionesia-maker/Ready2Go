#!/bin/bash
# =============================================================================
# _comun.sh — constantes y utilidades compartidas por los scripts de deploy/qa.
# Se carga con `source`; no se ejecuta solo.
#
# TODO lo que escriben estos scripts cuelga de QA_BASE (/opt/go/gocreate-qa) o de
# los servicios com.go.gocreate-qa.*. Las constantes de produccion (PROD_*) se
# usan SOLO para LEER (verificar_aislamiento.sh) — ningun script del QA modifica
# nada de /opt/go/gocreate ni de com.go.gocreate.* (requisito QA-13).
# =============================================================================

QA_SLUG="gocreate-qa"
QA_BASE="/opt/go/${QA_SLUG}"
QA_USER="_gocreateqa"
QA_LABEL_API="com.go.${QA_SLUG}.api"
QA_LABEL_TUNNEL="com.go.${QA_SLUG}.tunnel"
QA_PLIST_API="/Library/LaunchDaemons/${QA_LABEL_API}.plist"
QA_PLIST_TUNNEL="/Library/LaunchDaemons/${QA_LABEL_TUNNEL}.plist"
QA_PORT=8010
QA_HOSTNAME="qa.gocreate.mx"
QA_CREDENCIALES="${QA_BASE}/shared/env/credenciales_qa.txt"

PROD_BASE="/opt/go/gocreate"
PROD_USER="_gocreate"
PROD_PORT=8000
PROD_LABEL_API="com.go.gocreate.api"

# Homebrew visible (sudo recorta el PATH), igual que deploy-app.sh
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.12/bin:/usr/bin:/bin:/usr/sbin:/sbin"

info() { echo "[qa] $*"; }
die() { echo "[qa] ERROR: $*" >&2; exit 1; }

exigir_mac_mini() {
  [ "$(uname)" = "Darwin" ] && [ -d /opt/go ] \
    || die "Este script corre EN la Mac mini de marketing (necesita /opt/go). Por SSH: ssh gocreate-prod \"\$HOME/qa/<script>\"."
}

# Ejecutar como el usuario de servicio del QA (regla sudoers: integraciones -> _gocreateqa).
# El cd / es obligatorio: sudo hereda el directorio actual de quien llama (p. ej. ~/qa) y el
# usuario de servicio no puede leerlo ("Incapaz de leer el directorio de trabajo actual").
como_qa() { ( cd / && sudo -n -u "$QA_USER" env HOME="$QA_BASE/home_${QA_SLUG}" PATH="$PATH" "$@" ); }

# Solo lectura sobre produccion (regla sudoers existente: integraciones -> _gocreate).
como_prod_lectura() { ( cd / && sudo -n -u "$PROD_USER" "$@" ); }

# Carpeta backend/ de la release activa del QA, segun el plist.
release_backend() {
  /usr/libexec/PlistBuddy -c "Print :WorkingDirectory" "$QA_PLIST_API" 2>/dev/null
}

salud_qa() { curl -s -m 5 "http://127.0.0.1:${QA_PORT}/api/health" 2>/dev/null || true; }

esperar_salud_qa() {
  local i
  for i in $(seq 1 25); do
    if salud_qa | grep -q '"qa":true\|"qa": true'; then return 0; fi
    sleep 1.5
  done
  return 1
}

servicio_cargado() { sudo -n /bin/launchctl print "system/$1" >/dev/null 2>&1; }
