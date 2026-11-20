# Entorno QA de GOCreate — guía de implementación y operación

Segunda instancia de GOCreate (misma app, **otro proceso, otra base, otros archivos, otros secretos**, sin correo ni integraciones) para que la ingeniera de procesos y calidad la audite sin riesgo para producción. Contexto y requisitos: `AVANCES/optimizacion/08-entorno-qa-aislado.md`. Qué se aisló y qué falta: [INVENTARIO.md](INVENTARIO.md).

```
Internet ─► Cloudflare (Access + TLS) ─► túnel PROPIO gocreate-qa ─► cloudflared (com.go.gocreate-qa.tunnel)
                                                                        │ http://127.0.0.1:8010
                                                                        ▼
   Mac mini de marketing ── uvicorn (com.go.gocreate-qa.api, usuario _gocreateqa, 1 worker)
                              ├─ /api/*  → FastAPI  (QA_MODE=true, ENV=production)
                              └─ /*      → frontend/dist compilado con VITE_APP_ENV=qa
   Datos: /opt/go/gocreate-qa/shared/data (base + uploads)   ·   Producción: /opt/go/gocreate (no se toca)
```

| Dato | Valor |
|---|---|
| Slug en `deploy-app.sh` | `gocreate-qa` → `/opt/go/gocreate-qa/` |
| Usuario de servicio | `_gocreateqa` (propio; **no** `_gocreate`) |
| Servicios | `com.go.gocreate-qa.api`, `com.go.gocreate-qa.tunnel` (LaunchDaemons) |
| Puerto | `127.0.0.1:8010` |
| Hostname (default, decisión D1) | `qa.gocreate.mx` |
| Rama que se despliega | `qa` |

## Qué hay en esta carpeta

| Archivo | Qué es |
|---|---|
| `app.conf` | Configuración para `/opt/go/bin/deploy-app.sh` (reutiliza el pipeline de producción tal cual) |
| `env.qa.example` | Plantilla del `.env` del QA (sin secretos) |
| `com.go.gocreate-qa.api.plist`, `…tunnel.plist` | LaunchDaemons del QA |
| `sudoers-gocreate-qa.txt` | Reglas NOPASSWD acotadas al QA |
| `alta_host.sh` | **Alta única** en la mini (root): usuario, carpetas, `app.conf`, plists, `.env` |
| `actualizar.sh` | Despliega la rama `qa` (`--force`, `--reiniciar`) |
| `reiniciar_datos.sh` | Vacía y vuelve a sembrar (`--si`, `--credenciales-nuevas`) |
| `sembrar_datos.py` | Datos 100 % ficticios + un usuario por rol; recorre Equipos por la API real |
| `smoke_qa.py` | Prueba de humo (sesión, crear, editar, subir archivo, borrar) |
| `verificar_aislamiento.sh` | Informe de la sección 8 del documento (Markdown) |
| `encender.sh`, `apagar.sh` | Encendido y apagado bajo demanda |
| `requirements-qa.txt` | `httpx` (lo necesita el sembrado; no está en el venv de producción) |
| `_comun.sh` | Constantes compartidas |

## Qué cambia en el código de GOCreate (inerte en producción)

- `backend/app/main.py`: con `QA_MODE=true` añade `X-Robots-Tag: noindex, nofollow`, `/robots.txt` con `Disallow: /` y `"qa": true` en `/api/health`. Sin la variable, nada cambia.
- `frontend`: banner naranja «Entorno de pruebas · QA · datos ficticios» (`design/QaBanner.jsx`), título con prefijo `[QA]` y «QA (datos ficticios)» en el panel «acerca de». Se activa con `VITE_APP_ENV=qa` en el build **o** con un host que empiece por `qa.`. En producción no se pinta nada.
- **Por qué no `ENV=qa`:** en este código `ENV` solo distingue `production` del resto; con otro valor las cookies pierden `Secure` y `/docs` queda abierto. El QA corre con `ENV=production` y se identifica con `QA_MODE`.

## Procedimiento (en este orden)

> Regla del proyecto: **cada comando contra la mini, Cloudflare o DNS se muestra y se confirma antes de ejecutarse.** Producción es de solo lectura.

### 0. Antes de tocar nada: huella de producción

```bash
scp -r deploy/qa gocreate-prod:~/qa
ssh gocreate-prod "~/qa/verificar_aislamiento.sh --prod-antes ~/qa/prod_antes.txt"
```

Mientras el QA no existe, `--prod-antes` solo guarda la huella de producción (commit, procesos, plists, configuración del túnel y huella del secreto) y termina. Es de solo lectura.

### 1. Código en GitHub (sin root)

Los cambios de código de arriba deben estar en `master` y luego en `qa`:

```bash
git push origin master:qa        # después del merge a master que lo incluya
```

### 2. Alta en la mini (root, una sola vez)

```bash
ssh -t gocreate-prod "cd ~/qa && sudo ./alta_host.sh --sudoers"
```

Pide la contraseña de `sudo` de `integraciones`. Es idempotente. No arranca nada ni toca `/opt/go/gocreate`.

### 3. Túnel y acceso (panel de Cloudflare, lo hace una persona)

1. **Zero Trust → Networks → Tunnels → Create a tunnel → Cloudflared**, nombre `gocreate-qa`. Copia el **token**.
2. En la mini, guarda el token (nunca en el historial ni en el repo):
   ```bash
   ssh -t gocreate-prod "sudo -u _gocreateqa sh -c 'umask 077; cat > /opt/go/gocreate-qa/tunnel/tunnel.token'"
   # pega el token, Enter, Ctrl-D
   ```
3. En el túnel → **Public Hostname**: `qa.gocreate.mx` → `HTTP` → `127.0.0.1:8010`. Deja la regla final «catch-all» en `http_status:404` (QA-06). Cloudflare crea el CNAME con proxy.
4. **Access → Applications → Self-hosted**: dominio `qa.gocreate.mx`, política *Allow* con la lista de correos de Dafnne y los ingenieros (autenticación por código de un solo uso al correo). **Sin esto el QA queda protegido solo por el login de la app** (QA-07, decisión D2).
5. *(Opcional)* Regla de transformación de respuesta que añada `X-Robots-Tag: noindex` en ese hostname; la app ya lo hace por sí misma.

### 4. Primer deploy y datos

```bash
ssh -t gocreate-prod "cd /tmp && sudo /opt/go/bin/deploy-app.sh gocreate-qa"   # (desde /tmp: el usuario del QA no puede leer tu home) clona la rama qa, compila con VITE_APP_ENV=qa, arranca
ssh -t gocreate-prod "~/qa/reiniciar_datos.sh --si"                    # siembra los datos ficticios y crea las credenciales
ssh -t gocreate-prod "~/qa/encender.sh"                                # enciende también el túnel
```

Si el primer deploy falla a medias, revisa `/opt/go/gocreate-qa/logs/deploy.log`; el rollback automático no tiene release previa a la cual volver en la primera vez.

### 5. Verificación (QA-13 incluido)

```bash
ssh gocreate-prod "~/qa/verificar_aislamiento.sh --dominio --prod-despues ~/qa/prod_antes.txt" | tee deploy/qa/VERIFICACION_$(date +%F).md
```

Guarda el informe fechado. **Debe quedar todo en PASS.** Ojo con la última comprobación («`_gocreateqa` no lee el `.env` de producción ni escribe su base»): si sale en FAIL, es un problema de permisos de **producción** (ver INVENTARIO §6) que hay que corregir antes de dar el QA por aislado.

### 6. Registro (QA-14) y entrega a Dafnne

- Anota en `status.md`, `context.md` y en `docs/deploy/` la fila: fecha, máquina, puerto 8010, servicios, hostname, responsable, commit desplegado.
- Entrega por **canal privado** (no chat ni correo en claro): URL, el archivo de credenciales (`ssh gocreate-prod "sudo -u _gocreateqa cat /opt/go/gocreate-qa/shared/env/credenciales_qa.txt"`), la tabla de roles de INVENTARIO §4 y el formato de hallazgos (sección 9 del documento 08).

## Operación

| Quiero… | Comando (en la mini, o `ssh gocreate-prod "~/qa/…"`) |
|---|---|
| Ver otra versión en el QA | `git push origin <rama>:qa` y luego `./actualizar.sh` |
| Que el QA iguale a producción | `git push origin master:qa` y `./actualizar.sh` |
| Redesplegar la misma versión | `./actualizar.sh --force` |
| Adoptar un cambio de esquema | `./actualizar.sh --reiniciar` |
| Dejar los datos como nuevos | `./reiniciar_datos.sh` (conserva las contraseñas; `--credenciales-nuevas` las cambia) |
| Liberar memoria | `./apagar.sh` (no vuelve al reiniciar la mini; `--hasta-reinicio` sí) |
| Volver a encender | `./encender.sh` |
| Ver logs | `ssh gocreate-prod "sudo -u _gocreateqa tail -f /opt/go/gocreate-qa/logs/backend.log"` |
| Auditoría rápida del túnel | `cloudflared tunnel list` (debe aparecer `gocreate-qa`) y `ps -eo pid,args \| grep [c]loudflared \| grep -- --url` (debe salir vacío: sin *quick tunnels*) |

**Prohibido** (heredado del protocolo del túnel): *quick tunnels*, procesos sueltos sin launchd, escuchar en `0.0.0.0`, DNS a una IP pública, reutilizar el túnel o el `.env` de producción.

## Probar el sembrado en tu máquina, sin tocar nada

Se hace sobre una **copia** de `backend/app` en una carpeta temporal, para no escribir `uploads/` dentro del repo (está en una carpeta sincronizada con Drive):

```bash
mkdir -p /tmp/qa_prueba/backend && cp -r backend/app /tmp/qa_prueba/backend/app && cd /tmp/qa_prueba/backend
JWT_SECRET_KEY=prueba-local-0123456789abcdef QA_MODE=true ENV=production \
  python /ruta/al/repo/deploy/qa/sembrar_datos.py --credenciales /tmp/qa_prueba/credenciales.txt
```

Sin `QA_MODE=true` el script aborta a propósito. Requiere `httpx`, `Pillow` y las dependencias de `backend/requirements.txt`.

## Deshacer el QA por completo

```bash
ssh -t gocreate-prod "cd ~/qa && ./apagar.sh && sudo rm -f /Library/LaunchDaemons/com.go.gocreate-qa.*.plist /etc/sudoers.d/integraciones-gocreate-qa && sudo rm -rf /opt/go/gocreate-qa && sudo dscl . -delete /Users/_gocreateqa && sudo dscl . -delete /Groups/_gocreateqa"
```

Y borrar en Cloudflare el túnel `gocreate-qa`, el hostname y la aplicación de Access. Producción no se ve afectada.
