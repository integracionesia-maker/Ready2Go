#!/bin/bash
# =============================================================================
# apagar.sh — apaga el QA (API y tunel) para liberar memoria de la mini. QA-15.
#
# Uso:   ./apagar.sh [--hasta-reinicio]
#
# Por defecto ademas hace `launchctl disable`, asi el QA NO vuelve a arrancar solo
# si la mini se reinicia. Con --hasta-reinicio solo se detiene ahora (y vuelve al
# siguiente arranque de la maquina). encender.sh lo reactiva.
# Solo toca com.go.gocreate-qa.*; nunca los servicios de produccion.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=_comun.sh
source ./_comun.sh
exigir_mac_mini

PERSISTENTE=1
[[ "${1:-}" == "--hasta-reinicio" ]] && PERSISTENTE=0

for label in "$QA_LABEL_TUNNEL" "$QA_LABEL_API"; do
  if servicio_cargado "$label"; then
    sudo -n /bin/launchctl bootout "system/$label"
    info "$label apagado."
  else
    info "$label ya estaba apagado."
  fi
  if [ "$PERSISTENTE" -eq 1 ]; then
    sudo -n /bin/launchctl disable "system/$label"
  fi
done

[ "$PERSISTENTE" -eq 1 ] && info "Deshabilitado: no arrancara con la mini. Para volver: ./encender.sh" \
                         || info "Apagado hasta el proximo reinicio de la mini."
