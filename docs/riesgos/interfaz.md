# Riesgos — interfaz

Descubiertos verificando en disco, no en teoria. Los que no son de mi carril se
reportan aqui y no se parchean.

## R-I01 — El presupuesto de rendimiento ya estaba vencido antes de empezar

El bundle inicial mide **261.76 kB gz** en el commit base, contra el techo de
**250 kB gz** de la asignacion. Medido con `npm run build` sobre `281f10b`, antes
de tocar una linea.

ApexCharts viaja dentro del chunk principal (942 kB sin comprimir), sin diferir.
`jspdf` y `html2canvas` si estan bien: salen en chunks aparte por el `import()`
dinamico.

Consecuencia: el `manualChunks` y el code splitting por ruta de I1 no son pulido
opcional, son deuda ya vencida. Y todo lo que agregue I1 (`motion`, fuentes,
cristal) empuja el numero hacia arriba desde un punto que ya no cumple.

## R-I02 — `CLAUDE.md` contradice a `models.py` en gastos generales

`CLAUDE.md:39` afirma que `general_expenses` va "sin `creator_id`/`brand_id`".
`models.py:142-148` dice lo contrario y es explicito:

```
Tiene brand_id (no nullable) porque TODO gasto general debe estar asociado a
una marca para trazabilidad y reportes por marca.
brand_id = Column(Integer, ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False)
```

Existe `backend/migrate_add_brand_to_general_expenses.py`: la marca se agrego
despues y la documentacion no se actualizo. Esa contradiccion ya costo un e2e
rojo (ver `1568ff6`).

`CLAUDE.md` esta fuera de mi alcance. **Pido que se corrija arriba.**

## R-I03 — `CLAUDE.md` apunta a una ruta que I0 movio

`CLAUDE.md:46` dice `frontend/src/hooks/useMobile.js`. Desde `d602e00` vive en
`frontend/src/modules/presupuestos/hooks/useMobile.js`.

El hook sigue funcionando y se conserva, como manda la regla; solo la ruta
documentada quedo vieja. Tampoco puedo editar ese archivo. Ver B-I07: cuando el
modulo de equipos necesite `useMobile`, hay que promoverlo a un lugar compartido,
y ese es el momento de corregir la referencia de una sola vez.

## R-I04 — `seed_demo_year.py` deja una DB que parece sembrada y pinta ceros

Corre sin error y reporta porcentajes de gasto por creador, pero deja:

- 355 tickets, **todos** en estado `pendiente`
- los 6 ciclos en `spent=0.0` y `amount=0.0`
- 0 gastos generales

Un ticket `pendiente` nunca descuenta (regla R7), asi que el dashboard sale con
todos los KPI en `$0.00` y los 5 graficos en "Sin datos", con la DB "llena". El
seed escribe el campo historico congelado `creators.spent_budget`, que ya no
alimenta ningun calculo vigente.

Es una trampa de verificacion: quien tome capturas despues de ese seed va a
fotografiar el estado vacio y creer que verifico la pantalla. Para las capturas de
I0 hubo que aprobar los 355 tickets **por la API real** (para que
`crud.approve_ticket` actualizara los ciclos), no tocando la DB.

`backend/` esta fuera de mi alcance. **Reportado, no parcheado.**

## R-I05 — Colision de nombre `AppShell` que llega en I1

`frontend/src/App.jsx:48` ya define un componente local llamado `AppShell`. I1
crea `src/shell/AppShell.jsx`. Hay que decidir el renombre al escribir I1, no en
el merge.

## R-I06 — Las fuentes de marca no existen en disco

Barrido de `context_desing_go`: cero `.woff2`, `.woff`, `.otf` y `.ttf`. Blauer
Nue y Conthic no estan. I7 quita el `@import` remoto de Google Fonts, que hoy es
lo unico que trae Inter, JetBrains Mono y Space Grotesk, asi que quitarlo sin
sustituto deja la app sin tipografia propia.

Plan acordado: `@fontsource` autohospedado para JetBrains Mono y los respaldos
documentados, con la pila lista para meter los woff2 de marca cuando lleguen.
Bloquea el cierre visual de I1 y de I7.

## R-I07 — El entorno de desarrollo no tolera Google Drive

`G:\Mi unidad` es Google Drive File Stream y Windows la reporta como FAT32. No
soporta reparse points y `npm install` falla ahi con `EPERM`/`EBADF`. Ademas
sincronizaria `node_modules` completo en segundo plano.

Riesgo real de que alguien vuelva a clonar el repo ahi y pierda medio dia
peleando con el gestor de paquetes en vez de con el codigo. Se trabaja en
`C:\dev\Ready2Go`.

## R-I08 — Push sin verificar

La llave SSH `id_ed25519` no esta autorizada en la org
(`SHA256:eMeepbSTJV6UM4k8g0ThUk4wv4toJh195ZPuCLKfLMQ`). El clon va por HTTPS con
Git Credential Manager. Hasta que un push cierre bien, el trabajo local no cuenta
como entregado.
