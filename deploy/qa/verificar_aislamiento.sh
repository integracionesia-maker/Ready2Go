#!/bin/bash
# =============================================================================
# verificar_aislamiento.sh — comprueba que el QA no comparte nada con produccion
# (seccion 8 del doc 08-entorno-qa-aislado.md). Solo LEE produccion.
#
# Uso (en la mini; por SSH:  ssh gocreate-prod "~/qa/verificar_aislamiento.sh ..."):
#   ./verificar_aislamiento.sh [--dominio] [--prod-antes ARCHIVO] [--prod-despues ARCHIVO]
#
#   --dominio             tambien prueba https://qa.gocreate.mx (pide autenticacion)
#   --prod-antes FILE     guarda una huella del estado de produccion en FILE
#   --prod-despues FILE   compara el estado actual de produccion con esa huella
#                         (comprobacion 10: produccion intacta antes/despues del alta)
#
# Imprime un informe en Markdown (guardalo como VERIFICACION_AAAA-MM-DD.md):
#   ./verificar_aislamiento.sh --dominio | tee VERIFICACION_$(date +%F).md
# Nunca imprime secretos ni contraseñas. Codigo de salida = numero de FAIL.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")"
# shellcheck source=_comun.sh
source ./_comun.sh
exigir_mac_mini

DOMINIO=0; ANTES=""; DESPUES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dominio) DOMINIO=1 ;;
    --prod-antes) ANTES="${2:?falta archivo}"; shift ;;
    --prod-despues) DESPUES="${2:?falta archivo}"; shift ;;
    *) die "opcion desconocida: $1" ;;
  esac
  shift
done

FALLOS=0; N=0
fila() { # fila "comprobacion" PASS|FAIL|AVISO "detalle"
  N=$((N + 1))
  [ "$2" = "FAIL" ] && FALLOS=$((FALLOS + 1))
  echo "| $N | $1 | **$2** | $3 |"
}
ok_si() { # ok_si "comprobacion" <codigo> "detalle si pasa" "detalle si falla"
  if [ "$2" -eq 0 ]; then fila "$1" PASS "$3"; else fila "$1" FAIL "$4"; fi
}

PROD_PLIST="/Library/LaunchDaemons/${PROD_LABEL_API}.plist"
PROD_WD="$(/usr/libexec/PlistBuddy -c 'Print :WorkingDirectory' "$PROD_PLIST")"
PROD_PY="$(/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:0' "$PROD_PLIST")"

huella_secreto() { # huella_secreto <qa|prod>: sha256 truncado del JWT_SECRET_KEY (nunca el valor)
  local f=como_qa file="$QA_BASE/shared/env/.env"
  [ "$1" = prod ] && { f=como_prod_lectura; file="$PROD_BASE/shared/env/.env"; }
  "$f" sh -c 'grep "^JWT_SECRET_KEY=" "$1" | head -1 | cut -d= -f2- | tr -d "\"" | shasum -a 256 | cut -c1-16' _ "$file"
}
# Huella de produccion: LO QUE NO DEBE CAMBIAR al crear el QA (commit, procesos,
# plists, configuracion del tunel y huella del secreto). No incluye la base: esa
# cambia con el uso normal.
snapshot_prod() {
  echo "sha=$(como_prod_lectura cat "$PROD_BASE/deploy/current.sha" 2>/dev/null)"
  echo "workdir=$PROD_WD"
  echo "api_pid=$(sudo -n /bin/launchctl print "system/${PROD_LABEL_API}" 2>/dev/null | awk '/^[[:space:]]+pid =/{print $3; exit}')"
  echo "tunnel_pid=$(sudo -n /bin/launchctl print system/com.go.gocreate.tunnel 2>/dev/null | awk '/^[[:space:]]+pid =/{print $3; exit}')"
  echo "plist_api=$(shasum -a 256 "$PROD_PLIST" | cut -c1-16)"
  echo "plist_tunnel=$(shasum -a 256 /Library/LaunchDaemons/com.go.gocreate.tunnel.plist | cut -c1-16)"
  echo "env=$(huella_secreto prod)"
  echo "tunnel_config=$(como_prod_lectura shasum -a 256 "$PROD_BASE/tunnel/config.yml" 2>/dev/null | cut -c1-16)"
}

# Paso 0 del README: antes de que exista el QA solo se guarda la huella de produccion.
if [ -n "$ANTES" ] && [ ! -f "$QA_PLIST_API" ]; then
  snapshot_prod > "$ANTES"
  info "huella de produccion guardada en $ANTES (el QA aun no existe; no hay mas que verificar)."
  exit 0
fi

WD="$(release_backend)" || die "no encuentro el plist del QA; ¿se corrio alta_host.sh?"
QA_PY="$WD/venv/bin/python"
QA_COMMIT="$(como_qa cat "$QA_BASE/deploy/current.sha" 2>/dev/null || echo desconocido)"

realpath_como() { # realpath_como <usuario: qa|prod> <ruta>
  local py="$QA_PY"; local f=como_qa
  [ "$1" = prod ] && { py="$PROD_PY"; f=como_prod_lectura; }
  "$f" "$py" -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$2"
}

echo "# Verificación de aislamiento del QA de GOCreate"
echo
echo "- Fecha: $(date '+%F %T')  ·  Host: $(hostname)  ·  Commit QA: \`${QA_COMMIT}\`"
echo "- Release QA: \`${WD}\`  ·  Puerto QA: ${QA_PORT}"
echo
echo "| # | Comprobación | Resultado | Detalle |"
echo "|---|---|---|---|"

# 1 ── Base de datos distinta
QA_DB="$(realpath_como qa "$WD/presupuesto.db")"
PROD_DB="$(realpath_como prod "$PROD_WD/presupuesto.db")"
if [ -n "$QA_DB" ] && [ -n "$PROD_DB" ] && [ "$QA_DB" != "$PROD_DB" ] \
   && [[ "$QA_DB" == ${QA_BASE}/* ]] && [[ "$PROD_DB" == ${PROD_BASE}/* ]]; then
  fila "QA-01 Base de datos distinta a produccion" PASS "QA \`$QA_DB\` ≠ prod \`$PROD_DB\`"
else
  fila "QA-01 Base de datos distinta a produccion" FAIL "QA=\`$QA_DB\` prod=\`$PROD_DB\`"
fi

# 2 ── Escritura en QA no aparece en produccion
como_qa "$QA_PY" -c 'import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute("create table if not exists _qa_aislamiento_marker(x)");c.commit()' "$QA_DB" 2>/dev/null
EN_QA="$(como_qa "$QA_PY" -c 'import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute("select count(*) from sqlite_master where name=\"_qa_aislamiento_marker\"").fetchone()[0])' "$QA_DB" 2>/dev/null)"
EN_PROD="$(como_prod_lectura "$PROD_PY" -c 'import sqlite3,sys;print(sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True).execute("select count(*) from sqlite_master where name=\"_qa_aislamiento_marker\"").fetchone()[0])' "$PROD_DB" 2>/dev/null)"
como_qa "$QA_PY" -c 'import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute("drop table if exists _qa_aislamiento_marker");c.commit()' "$QA_DB" 2>/dev/null
if [ "$EN_QA" = "1" ] && [ "$EN_PROD" = "0" ]; then
  fila "Escritura de prueba: existe solo en QA" PASS "marcador en QA=1, en producción=0 (ya retirado del QA)"
else
  fila "Escritura de prueba: existe solo en QA" FAIL "QA=${EN_QA:-?} prod=${EN_PROD:-?}"
fi

# 3 ── Archivos distintos
QA_UP="$(realpath_como qa "$WD/uploads")"
PROD_UP="$(realpath_como prod "$PROD_WD/uploads")"
if [ -n "$QA_UP" ] && [ -n "$PROD_UP" ] && [[ "$QA_UP" == ${QA_BASE}/* ]] && [[ "$PROD_UP" == ${PROD_BASE}/* ]]; then
  fila "QA-02 Directorio de archivos propio" PASS "QA \`$QA_UP\` · prod \`$PROD_UP\`"
else
  fila "QA-02 Directorio de archivos propio" FAIL "QA=\`$QA_UP\` prod=\`$PROD_UP\`"
fi

# 4 ── Secretos distintos (por huella)
H_QA="$(huella_secreto qa)"; H_PROD="$(huella_secreto prod)"
if [ -n "$H_QA" ] && [ -n "$H_PROD" ] && [ "$H_QA" != "$H_PROD" ] && [ "$H_QA" != "$(printf '' | shasum -a 256 | cut -c1-16)" ]; then
  fila "QA-03 JWT_SECRET_KEY distinto (por huella)" PASS "huellas distintas (no se imprimen)"
else
  fila "QA-03 JWT_SECRET_KEY distinto (por huella)" FAIL "iguales, vacias o ilegibles"
fi

# 5 ── Escucha solo en 127.0.0.1
ESCUCHA="$(netstat -an -p tcp 2>/dev/null | awk -v p="$QA_PORT" '/LISTEN/ && $4 ~ ("[.]" p "$") {print $4}')"
if [ "$ESCUCHA" = "127.0.0.1.${QA_PORT}" ]; then
  fila "QA-04 Escucha solo en 127.0.0.1 y puerto exclusivo" PASS "\`$ESCUCHA\`"
else
  fila "QA-04 Escucha solo en 127.0.0.1 y puerto exclusivo" FAIL "sockets: \`${ESCUCHA:-ninguno}\`"
fi

# 6 ── Interruptores en valor seguro
ENVQA="$QA_BASE/shared/env/.env"
vq() { como_qa sh -c 'grep "^$2=" "$1" | head -1 | cut -d= -f2- | tr -d "\"" ' _ "$ENVQA" "$1"; }
MALOS=""
[ "$(vq QA_MODE)" = "true" ] || MALOS="$MALOS QA_MODE!=true"
[ "$(vq ENV)" = "production" ] || MALOS="$MALOS ENV!=production"
case "$(vq NOTIF_ENABLED | tr 'A-Z' 'a-z')" in true|1|yes|si|on) MALOS="$MALOS NOTIF_ENABLED=activo" ;; esac
[ -z "$(vq SMTP_HOST)" ] || MALOS="$MALOS SMTP_HOST-definido"
[ -z "$(vq SMTP_BCC)" ] || MALOS="$MALOS SMTP_BCC-definido"
if [ -z "$MALOS" ]; then
  fila "QA-09 Interruptores seguros (correo apagado, sin SMTP ni BCC, QA_MODE)" PASS "QA_MODE=true, ENV=production, NOTIF_ENABLED=false, sin SMTP"
else
  fila "QA-09 Interruptores seguros (correo apagado, sin SMTP ni BCC, QA_MODE)" FAIL "$MALOS"
fi

# 7 ── Usuarios QA: un usuario por rol base, todos ficticios, ninguno en produccion
ROLES_QA="$(como_qa "$QA_PY" -c 'import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);print(len(c.execute("select distinct role from users").fetchall()), c.execute("select count(*) from users where email not like \"%@qa.gocreate.example\"").fetchone()[0])' "$QA_DB" 2>/dev/null)"
QA_PROD="$(como_prod_lectura "$PROD_PY" -c 'import sqlite3,sys;print(sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True).execute("select count(*) from users where username like \"qa.%\" or email like \"%@qa.gocreate.example\"").fetchone()[0])' "$PROD_DB" 2>/dev/null)"
N_ROLES="${ROLES_QA% *}"; N_REALES="${ROLES_QA#* }"
if [ "${N_ROLES:-0}" -ge 9 ] && [ "${N_REALES:-1}" = "0" ] && [ "${QA_PROD:-1}" = "0" ]; then
  fila "QA-08/10 Un usuario por rol, todos ficticios, ninguno en producción" PASS "$N_ROLES roles base; usuarios con correo real en QA: 0; usuarios QA en producción: 0"
else
  fila "QA-08/10 Un usuario por rol, todos ficticios, ninguno en producción" FAIL "roles=$N_ROLES correos_reales_en_QA=$N_REALES usuarios_qa_en_prod=${QA_PROD:-?}"
fi

# 8 ── Dominio sin sesión pide autenticación
if [ "$DOMINIO" -eq 1 ]; then
  R="$(curl -s -o /dev/null -m 15 -w '%{http_code} %{redirect_url}' "https://${QA_HOSTNAME}/")"
  case "$R" in
    302*cloudflareaccess.com*|401*|403*) fila "QA-07 Dominio sin sesión pide autenticación" PASS "\`$R\`" ;;
    *) fila "QA-07 Dominio sin sesión pide autenticación" FAIL "respuesta: \`$R\` (¿Cloudflare Access configurado?)" ;;
  esac
else
  fila "QA-07 Dominio sin sesión pide autenticación" AVISO "no se probó (falta --dominio)"
fi

# 9 ── Cabeceras y señales de QA
H="$(curl -sI -m 5 "http://127.0.0.1:${QA_PORT}/" | tr -d '\r' | tr 'A-Z' 'a-z')"
HEALTH="$(salud_qa)"
if echo "$H" | grep -q '^x-robots-tag: noindex' && echo "$HEALTH" | grep -q '"qa": *true'; then
  fila "QA-11 Señales de QA (noindex y QA_MODE en /api/health)" PASS "x-robots-tag: noindex, nofollow; health qa=true"
else
  fila "QA-11 Señales de QA (noindex y QA_MODE en /api/health)" FAIL "cabeceras: $(echo "$H" | grep -c x-robots-tag) · health: ${HEALTH:-sin respuesta}"
fi

# 10 ── Producción intacta
if [ -n "$ANTES" ]; then
  snapshot_prod > "$ANTES"
  fila "QA-13 Huella de producción guardada" AVISO "en \`$ANTES\` (vuelve a correr con --prod-despues)"
fi
if [ -n "$DESPUES" ]; then
  if [ -f "$DESPUES" ] && diff -q <(snapshot_prod) "$DESPUES" >/dev/null; then
    fila "QA-13 Producción intacta (mismo commit, procesos y configuración)" PASS "huella idéntica a la de \`$DESPUES\`"
  else
    fila "QA-13 Producción intacta (mismo commit, procesos y configuración)" FAIL "difiere de \`$DESPUES\`: $(diff <(snapshot_prod) "$DESPUES" 2>&1 | head -3 | tr '\n' ' ')"
  fi
fi
[ -z "$ANTES$DESPUES" ] && fila "QA-13 Producción intacta" AVISO "no se probó (usa --prod-antes antes del alta y --prod-despues después)"

# 11 ── Prueba de humo
como_qa sh -c 'cd "$1" && exec "$2" "$3" --credenciales "$4" >/dev/null 2>&1' _ \
  "$WD" "$QA_PY" "$WD/../deploy/qa/smoke_qa.py" "$QA_CREDENCIALES"
ok_si "Prueba de humo (sesión, crear, editar, subir archivo, borrar)" $? "5 pasos en verde" "falló; correr smoke_qa.py a mano para ver el paso"

# 12 ── El usuario del QA no puede leer ni escribir los datos de producción
LEE_ENV=0; ESCRIBE_DB=0
como_qa test -r "$PROD_BASE/shared/env/.env" && LEE_ENV=1
como_qa test -w "$PROD_DB" && ESCRIBE_DB=1
if [ "$LEE_ENV" -eq 0 ] && [ "$ESCRIBE_DB" -eq 0 ]; then
  fila "Aislamiento hacia producción: \`$QA_USER\` no lee su .env ni escribe su base" PASS "sin acceso"
else
  fila "Aislamiento hacia producción: \`$QA_USER\` no lee su .env ni escribe su base" FAIL "lee .env de prod=$LEE_ENV · escribe base de prod=$ESCRIBE_DB — permisos de /opt/go/gocreate demasiado abiertos (ver INVENTARIO.md §Hallazgos); afecta a TODAS las apps del host"
fi

echo
if [ "$FALLOS" -eq 0 ]; then
  echo "**Resultado: todo en verde** ($N comprobaciones; las marcadas AVISO no se ejecutaron)."
else
  echo "**Resultado: $FALLOS comprobación(es) en FAIL.** El QA no está listo para entregarse hasta resolverlas."
fi
exit "$FALLOS"
