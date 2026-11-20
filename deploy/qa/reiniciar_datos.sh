#!/bin/bash
# =============================================================================
# reiniciar_datos.sh — vacia la base y los archivos del QA y los vuelve a sembrar
# con datos ficticios (QA-12). Solo toca /opt/go/gocreate-qa/shared/data.
#
# Uso:   ./reiniciar_datos.sh [--si] [--credenciales-nuevas]
#
#   --si                    no pide confirmacion (lo usan actualizar.sh y la primera siembra)
#   --credenciales-nuevas   regenera TODAS las contraseñas. Por defecto se conservan
#                           (para no re-entregar credenciales a la auditora cada vez).
#
# Pasos: detiene la API del QA -> borra DB (+WAL/SHM) y uploads del QA -> instala
# httpx en el venv de la release (lo necesita el sembrado; no esta en produccion) ->
# corre sembrar_datos.py como _gocreateqa -> vuelve a arrancar la API.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=_comun.sh
source ./_comun.sh
exigir_mac_mini

SI=0; NUEVAS=0
for a in "$@"; do
  case "$a" in
    --si) SI=1 ;;
    --credenciales-nuevas) NUEVAS=1 ;;
    *) die "opcion desconocida: $a" ;;
  esac
done

DATA="$QA_BASE/shared/data"
# Freno: solo la carpeta de datos del QA, jamas otra (p. ej. la de produccion, que
# tiene archivos con el mismo nombre).
[ "$DATA" = "/opt/go/gocreate-qa/shared/data" ] || die "ruta de datos inesperada: $DATA"

WD="$(release_backend)" || die "no encuentro el plist del QA; ¿se corrio alta_host.sh?"
# /opt/go/gocreate-qa es 700 del usuario de servicio: las pruebas de existencia se
# hacen COMO ese usuario (el usuario que corre el script no puede ni entrar).
como_qa test -x "$WD/venv/bin/python" || die "no hay release desplegada (falta $WD/venv). Corre ./actualizar.sh primero."
como_qa test -f "$WD/../deploy/qa/sembrar_datos.py" || die "la release no trae deploy/qa/sembrar_datos.py: la rama qa no tiene estos archivos."

if [ "$SI" -ne 1 ]; then
  echo "Esto BORRA la base y los archivos del QA ($DATA) y los siembra de nuevo."
  echo "Solo afecta al QA (datos ficticios); produccion no se toca."
  read -r -p "Escribe QA para continuar: " resp
  [ "$resp" = "QA" ] || die "cancelado."
fi

info "deteniendo la API del QA..."
sudo -n /bin/launchctl bootout "system/$QA_LABEL_API" 2>/dev/null || true
sleep 2

info "borrando base y archivos del QA..."
como_qa sh -c 'rm -f "$1/presupuesto.db" "$1/presupuesto.db-wal" "$1/presupuesto.db-shm" && rm -rf "$1/uploads" && mkdir -p "$1/uploads"' _ "$DATA"
if [ "$NUEVAS" -eq 1 ]; then
  como_qa rm -f "$QA_CREDENCIALES"
  info "credenciales anteriores descartadas: se generaran nuevas."
fi

info "instalando dependencias extra del QA (httpx) en el venv de la release..."
como_qa "$WD/venv/bin/pip" install --quiet -r "$WD/../deploy/qa/requirements-qa.txt"

info "sembrando datos ficticios..."
set +e
como_qa sh -c 'cd "$1" && exec "$2" "$3" --credenciales "$4"' _ \
  "$WD" "$WD/venv/bin/python" "$WD/../deploy/qa/sembrar_datos.py" "$QA_CREDENCIALES"
RC=$?
set -e
[ "$RC" -eq 0 ] || [ "$RC" -eq 2 ] || die "el sembrado fallo (codigo $RC); la API del QA queda detenida."
[ "$RC" -eq 2 ] && info "AVISO: sembrado PARCIAL (algun escenario de prestamos fallo; ver arriba)."

info "arrancando la API del QA..."
sudo -n /bin/launchctl bootstrap system "$QA_PLIST_API" 2>/dev/null || sudo -n /bin/launchctl kickstart -k "system/$QA_LABEL_API"
esperar_salud_qa || die "la API del QA no responde tras sembrar; revisa $QA_BASE/logs/backend.log"
info "QA listo: $(salud_qa)"
info "Credenciales (NO compartir por chat; entregar por canal privado):"
info "  sudo -u $QA_USER cat $QA_CREDENCIALES"
