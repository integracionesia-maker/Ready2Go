# Changelog — interfaz

## 2026-07-28

### Agregado

- `frontend/src/modules/presupuestos/` — raiz del modulo, con `components/`,
  `pages/`, `hooks/` y `utils/` adentro.
- `frontend/src/api/client.js` — transporte HTTP compartido: `request`,
  `fetchWithAuthRetry`, `refreshSession`, `isNetworkError`,
  `setAuthFailureHandler`.
- `frontend/jsconfig.json` — alias `@/*` -> `./src/*` para el editor.
- Alias `@` en `resolve.alias` de `frontend/vite.config.js`, con la razon por la
  que ahi NUNCA van `react` ni `react-dom` escrita en el propio archivo.
- `docs/avances/interfaz.md`, `docs/backlog_interfaz.md`,
  `docs/changelog/interfaz.md`, `docs/riesgos/interfaz.md`.

### Cambiado

- 37 imports en 25 archivos del modulo pasan al alias `@`: solo los que cruzan la
  frontera (`api/`, `context/`, `assets/`). Los internos (`../utils/`,
  `../hooks/`) no se tocaron porque siguen resolviendo.
- `frontend/src/App.jsx` — los 15 imports de vistas apuntan a
  `./modules/presupuestos/`.
- `frontend/src/api/index.js` — pasa a ser barril: conserva las 38 funciones por
  dominio e importa el transporte de `./client`. Re-exporta `isNetworkError`,
  `setAuthFailureHandler`, `request` y `fetchWithAuthRetry`.
- `frontend/src/assets/logos/README.md` — la ruta de `BrandLogo.jsx` que el
  movimiento invalido.
- `frontend/e2e/gastos-generales.spec.js` — selecciona la marca obligatoria en el
  modal de nuevo gasto general, en los dos tests que lo abren.

### Quitado

- `refreshSession` deja de ser alcanzable desde `@/api`. Sigue exportado de
  `./client` porque el transporte lo usa; no se re-exporta en el barril a
  proposito, es interno del reintento por 401.
- Dejan de existir como raices `frontend/src/components/`, `pages/`, `hooks/` y
  `utils/`. Ningun archivo se borro: los 41 son renames.

### Sin cambio

Bundle identico byte por byte y las 20 capturas (10 rutas x 2 anchos) identicas
por SHA256. No se toco `index.css`, `index.html`, `package.json`,
`tailwind.config.js`, `apexTheme.js` ni `backend/`.
