# Avances — interfaz

## 2026-07-28

### I0 — Costura (cerrada): `d602e00`

`git mv` de `components/`, `pages/`, `hooks/` y `utils/` a
`src/modules/presupuestos/`. Los cuatro juntos, no dos: asi los imports internos
del modulo (`../utils/priority`, `../hooks/useSortable`, `../../hooks/useMobile`)
siguen resolviendo sin tocarse, y solo se reescriben los 37 imports que cruzan la
frontera. `api/`, `context/` y `assets/` se quedan en `src/` porque los va a
compartir el modulo de equipos.

Ademas: `src/api/client.js` con el transporte, `src/api/index.js` como barril,
alias `@` en `jsconfig.json` y en `resolve.alias` de `vite.config.js`.

Git detecto los 41 archivos como rename con 95-100% de similitud.

**Evidencia**

`npm run build` verde, y los bundles salen con **hash de contenido identico** al
de antes del movimiento:

```
dist/assets/index-DaiH1YwQ.js    942.05 kB  gzip: 261.76 kB
dist/assets/index-BHkVJudo.css    24.90 kB  gzip:   6.01 kB
+ los 4 PNG de logos, mismo hash
```

Mismo hash = mismo bundle byte por byte. Es una prueba mas fuerte que comparar
capturas a ojo.

Capturas reales de las 10 rutas (`/login`, `/`, `/dashboard`, `/creadores`,
`/transacciones`, `/validacion`, `/gastos-generales`, `/administracion`,
`/perfil`, `/403`) en desktop 1280x800 y en 390x844, antes y despues del
movimiento: **las 20 imagenes son identicas por SHA256**.

Las capturas se tomaron contra datos reales, no contra el estado vacio: 355
tickets aprobados, 8 marcas, 6 creadores, 2 gastos generales. El dashboard monta
sus 5 canvas de ApexCharts en los dos anchos. El verificador cuenta
`.apexcharts-canvas`, no solo caracteres del DOM: DOM lleno no es pantalla
pintada, y un dashboard con datos en cero pinta el estado vacio sin montar ni un
grafico, lo que esconderia una regresion.

Los 3 e2e desde DB limpia, reiniciando el backend entre archivos:

| Spec | Antes de I0 | Despues de I0 |
|---|---|---|
| `auth.spec.js` | 7/7 | 7/7 |
| `presupuesto-flujo-completo.spec.js` | 9/9 | 9/9 |
| `gastos-generales.spec.js` | 9/9 (tras `1568ff6`) | 9/9 |

Sin tocar: `index.css`, `index.html`, `package.json`, `tailwind.config.js`, los 3
specs, y todo `backend/`.

### Pre-I0 — `gastos-generales.spec.js` venia rojo de fabrica: `1568ff6`

Antes de mover nada corri los 3 specs para tener baseline. `gastos-generales`
fallaba: 2 pasaban, 1 fallaba, 6 no corrian. El archivo usa
`test.describe.serial`, asi que una sola asercion podrida abortaba 7 de 9 tests.

Causa: el spec nunca elegia marca en el modal de nuevo gasto general, y la marca
es obligatoria (`models.GeneralExpense.brand_id` `nullable=False`,
`schemas.GeneralExpenseCreate.brand_id` requerido, `required` en el select del
modal mas un guard propio en JS). La validacion nativa del navegador bloqueaba el
submit; la captura de fallo muestra el tooltip "Please select an item in the
list" sobre el campo MARCA.

Backend y UI coinciden: el spec era el desactualizado. Arreglado en un commit
aislado, antes de I0, para que I0 quedara demostrable.

### Entorno

Bloqueos resueltos, con su causa, para que no se vuelvan a descubrir a golpes:

- **El repo no puede vivir en `G:\Mi unidad` (Google Drive).** Windows la reporta
  como FAT32: no soporta reparse points (la junction falla con "Funcion
  incorrecta") y `npm install` revienta con `EPERM`/`EBADF` a mitad del arbol.
  El mismo `npm install` en `C:\dev\Ready2Go` cierra en 18s con 165 paquetes.
  Se trabaja en `C:\dev\Ready2Go`.
- **`pip` fallaba con `SSLError` contra PyPI** aunque PowerShell si alcanza
  pypi.org: `certifi` no trae el CA corporativo, el almacen de Windows si.
  Se resuelve con `pip install --use-feature=truststore`, sin desactivar la
  verificacion TLS.
- **Los 3 specs no se pueden correr en una sola invocacion.** El rate limit de
  login es 30 por 15 min por IP y esta en memoria (`security._login_attempts_by_ip`),
  asi que se resetea reiniciando uvicorn. Se corre un archivo, se reinicia el
  backend, se corre el siguiente.
- **`auth.spec.js` no es idempotente**: rota la contraseña del superadmin en su
  test 2. Necesita DB recien sembrada con `seed_auth.py`.

### Cierre de sesion

Push a `BeniBranch` limpio: `281f10b..012ef13`, fast-forward, 0 commits detras
del remoto. Tres commits: `1568ff6` (arreglo del spec), `d602e00` (I0),
`012ef13` (estos reportes).

La llave SSH `id_ed25519` sigue sin autorizar en la org, asi que el clon y el
push van por HTTPS con Git Credential Manager. Ya no bloquea, pero el comando de
clonado que da la asignacion (`git@github.com:...`) falla de entrada para quien
lo copie tal cual. Ver R-I08.
