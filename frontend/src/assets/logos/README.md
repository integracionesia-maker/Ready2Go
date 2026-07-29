# Logos oficiales — Grupo Ortiz

Assets de marca importados por componentes (Vite los optimiza y les da hash de caché).

| Archivo | Uso |
|---|---|
| `imagotipo-go-{blanco,naranja}.png` | Logo completo (cuadrado 1667×1667) — LoginPage |
| `isotipo-go-{blanco,naranja}.png` | Símbolo (apaisado 1667×1063) — Header, PDF, favicon |
| `logo-go.png` | Copia original de referencia |

**Regla de variantes por tema**: blanco en modo oscuro, naranja en modo claro.

**No usar `<img>` directo**: importar el componente
`src/modules/presupuestos/components/BrandLogo.jsx`, que
elige la variante correcta según `ThemeContext`:

```jsx
<BrandLogo variant="isotipo" className="h-8 w-auto" />
<BrandLogo variant="imagotipo" className="h-28 w-auto" />
```

Excepciones sin BrandLogo: el reporte PDF (`PdfReport/DashboardPdfTemplate.jsx`)
importa `isotipo-go-naranja.png` directo porque siempre se genera en tema claro,
y el favicon es una copia estática en `frontend/public/favicon.png`.

Fuente de verdad de la identidad: `IDENTIDAD DE MARCA/context_design.md` (repo `context_desing_go`).
