#!/bin/bash
# =============================================================================
# actualizar.sh — despliega al QA la version que esta en la rama `qa` de GitHub.
#
# Uso:   ./actualizar.sh [--force] [--reiniciar]
#
#   --force      redespliega aunque no haya commits nuevos (la app se cayo, etc.)
#   --reiniciar  despues del deploy vacia y vuelve a sembrar los datos del QA.
#                Hazlo cuando la version nueva cambie el esquema de la base: el
#                QA usa create_all (crea tablas nuevas, NO agrega columnas), asi
#                que una columna nueva solo aparece con una base nueva.
#
# Para que el QA muestre otra version, mueve la rama `qa` ANTES de correr esto:
#   git push origin <mi-rama>:qa        (o  git push origin master:qa  para igualar prod)
#
# Es solo un envoltorio de `sudo /opt/go/bin/deploy-app.sh gocreate-qa` (el mismo
# pipeline que produccion: respaldo, build, release inmutable, health check y
# rollback automatico). Solo toca /opt/go/gocreate-qa y com.go.gocreate-qa.api.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=_comun.sh
source ./_comun.sh
exigir_mac_mini

FORCE=0; REINICIAR=0
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    --reiniciar) REINICIAR=1 ;;
    *) die "opcion desconocida: $a" ;;
  esac
done

# El argumento debe coincidir EXACTO con la regla de sudoers (no pasar vacios).
if [ "$FORCE" -eq 1 ]; then
  ( cd / && sudo -n /opt/go/bin/deploy-app.sh "$QA_SLUG" --force )
else
  ( cd / && sudo -n /opt/go/bin/deploy-app.sh "$QA_SLUG" )
fi

esperar_salud_qa || die "el QA no responde con QA_MODE tras el deploy; revisa $QA_BASE/logs/backend.log (como_qa tail)."
info "QA sirviendo: $(salud_qa)"
info "commit desplegado: $(como_qa cat "$QA_BASE/deploy/current.sha" 2>/dev/null || echo desconocido)"

if [ "$REINICIAR" -eq 1 ]; then
  exec ./reiniciar_datos.sh --si
fi
