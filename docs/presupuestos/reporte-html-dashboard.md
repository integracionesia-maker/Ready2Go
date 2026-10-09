# Reporte HTML del Dashboard (reemplaza al PDF)

> Complementa `docs/presupuestos/periodo-unico-dashboard.md` (la detección de mes/año y la comparación son las mismas) y `docs/presupuestos/meta-gasto-mensual.md`.

## Qué es

El botón **Descargar reporte** del Dashboard baja un único archivo `.html` pensado para **compartir con otras personas**: se abre en cualquier navegador, sin sesión ni conexión a la API. Antes era un PDF de reportlab (retirado el 09/10/2026).

- `GET /api/dashboard/report.html?start_date=&end_date=` → `attachment`, nombre `reporte-presupuesto_<inicio|historico>_a_<fin|actual>.html`. Misma puerta que el resto de `/api/dashboard` (`admin`/`superadmin`/`marketing_presupuestos`/`marketing_admin`).
- Código: `backend/app/reporte_dashboard.py` (arma los datos, alertas y textos) + `backend/app/reporte_dashboard_plantilla.html` (CSS + JS del reporte). El router solo reúne los datos con las funciones CRUD de siempre; no hay lógica de negocio nueva.
- Los datos viajan **incrustados** como JSON (`<script type="application/json" id="report-data">`) y el JS del archivo los pinta. El archivo nunca hace `fetch`. Nada externo: fuentes y logo van incrustados.

## Identidad visual

**Estructura = la del HTML de referencia de marketing** (encabezado con el badge "GO", pestañas, KPI destacado + 3 KPIs, barra apilada de reparto, comparativo, alertas, etc.); lo que se aplicó encima son **solo estilos** de GOCreate (`frontend/src/design/tokens.css`, `DESIGN_SYSTEM.md`): fondo oscuro con ruido y retícula de puntos, cristal en encabezado y barra de pestañas, naranja `#FB670B` como acento, tema claro con los neutros de marca. Series: Creadores naranja, Generales turquesa, Operativos violeta (paleta de gráficas de la app). Sin emojis. No cambiar el marcado del HTML para "rediseñar": si se quiere otro look, tocar el CSS.

**Autocontenido y sin imágenes:** el archivo no incluye ninguna imagen (ni logo) ni pide nada a internet, así que no hay nada que pueda dejar de verse al compartirlo por correo, chat o visores. Solo las fuentes viajan en base64 (si un visor las bloquea, cae a la fuente del sistema sin perder nada). Archivos en `backend/app/reporte_assets/`: Nunito 700/800 (display), Inter 400/600 (cuerpo), JetBrains Mono 500 (cifras) — los mismos respaldos de la app mientras llegan Blauer Nue/Conthic (si el equipo que abre el archivo las tiene instaladas, las usa primero). Nunito/Inter/JetBrains son OFL (licencia de Nunito en la misma carpeta). Para cambiar la tipografía de marca cuando lleguen los woff2: reemplazar los archivos y ajustar `_RECURSOS` en `reporte_dashboard.py`.

## Contenido

Cuatro pestañas, cada una con el color de su serie: **Resumen** (KPIs, reparto del gasto, comparativo vs periodo anterior, alertas, presupuesto de creadores, top 5), **Creadores** (por responsable o por marca, tickets por día), **Gastos generales** y **Gastos operativos** (barras + chips que filtran el top 5). Cierra con "Notas sobre los datos". Modo oscuro por defecto con botón; al imprimir / "Guardar como PDF" sale en tema claro con todas las secciones seguidas.

- Comparativo "vs mes pasado / año pasado": solo en periodo único (si no, la tarjeta se oculta y una nota lo explica).
- Solo aparecen creadores con actividad (gastado o pendiente > 0), marcas y rubros con monto > 0.

## Alertas y textos automáticos (reglas en `reporte_dashboard.py`)

| Alerta | Regla |
|---|---|
| Creador excedió su ciclo (rojo, máx. 4) | `ciclo > 0` y `gastado > ciclo` |
| Creador sin presupuesto (ámbar, máx. 3) | `ciclo == 0` y `gastado > 0` |
| Tickets pendientes | `pending_total > 0` |
| Un solo gasto domina su sección | >= 30% del total de generales/operativos y la sección tiene >= 2 gastos |
| Categoría subió | >= 50% **y** >= $500 vs el periodo anterior (solo periodo único) |

Máximo 8 alertas, las rojas primero; clic en una abre su pestaña (y al creador). La frase de reparto ("El 58% del gasto fue en gastos operativos, y 44% de eso es un solo gasto: …") y las notas salen de los mismos datos.

## Caveat importante (heredado del dashboard)

**Presupuesto asignado / gastado / disponible, "Ciclo" y "% usado" son del ciclo vigente al generar el reporte, no del periodo filtrado** (misma fuente que los KPI fijos de la pantalla). El gasto de cada creador sí es del periodo. El reporte lo dice en "Notas sobre los datos"; si algún día se quiere unificar, es el mismo pendiente de `get_creator_usage`.

## Seguridad

Nombres de creadores/marcas y descripciones son **texto libre**. El JSON se serializa ASCII con `<`, `>`, `&` escapados (no puede cerrar el `<script>`) y la plantilla pasa todo por `esc()` antes de `innerHTML`. Cualquier campo nuevo que se pinte debe seguir esa regla.
