#!/bin/bash
# =============================================================================
# encender.sh — enciende el QA (API y, si ya esta configurado, el tunel). QA-15.
# Uso: ./encender.sh
# Solo toca com.go.gocreate-qa.*; nunca los servicios de produccion.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=_comun.sh
source ./_comun.sh
exigir_mac_mini

arrancar() {
  local label="$1" plist="$2"
  sudo -n /bin/launchctl enable "system/$label"   # deshace el `disable` de apagar.sh
  if servicio_cargado "$label"; then
    info "$label ya estaba encendido."
  else
    sudo -n /bin/launchctl bootstrap system "$plist"
    info "$label encendido."
  fi
}

arrancar "$QA_LABEL_API" "$QA_PLIST_API"

if como_qa test -s "$QA_BASE/tunnel/tunnel.token"; then
  arrancar "$QA_LABEL_TUNNEL" "$QA_PLIST_TUNNEL"
else
  info "tunel NO encendido: falta $QA_BASE/tunnel/tunnel.token (ver README §Tunel y acceso). El QA solo responde en 127.0.0.1:$QA_PORT."
fi

esperar_salud_qa && info "QA responde: $(salud_qa)" || info "AVISO: la API aun no responde; revisa $QA_BASE/logs/backend.log"
