# Riesgos — carril servidor y datos (Control de Equipos)

Lo que descubro que puede fallar. No lo que ya esta mitigado en el plan.

---

## R-SRV-07 — Un borrador abandonado bloquea su equipo para siempre

**Sev:** alto. **Estado:** abierto, necesita decision de producto.

El contrato §3 expone `POST /api/loans/{id}/items` sobre un borrador y exige
`409 EQUIPO_OCUPADO` si el equipo ya esta en otro prestamo abierto, con el
indice unico como arbitro. Eso significa que **los renglones existen desde el
borrador y por lo tanto reservan**. (El plan §4.3 dice lo contrario; se siguio el
contrato, que es el que esta congelado. Ver `docs/avances/servidor.md`.)

Escenario: alguien abre el wizard, agrega el iPhone 17 Pro, se distrae y cierra
la pestaña. Ese equipo queda no disponible **indefinidamente**. El contrato
incluso preve recuperar el borrador (`?estado=borrador&mios=1`), asi que los
borradores estan pensados para persistir.

No hay caducidad de borradores en el contrato ni en el plan. Falta decidir una
de estas:

- Caducidad automatica: un borrador sin tocar en N horas se cancela y libera.
- Que un aprobador o custodio pueda cancelar borradores ajenos.
- Nada, y se vive con el bloqueo (peor opcion: el area no va a saber por que un
  equipo "prestado" no aparece en ningun prestamo).

No lo decido yo: cualquiera de las tres cambia el contrato o agrega un proceso.

---

## R-SRV-08 — El seed demo no puede correr sobre la base de desarrollo

**Sev:** bajo. **Estado:** abierto, comportamiento intencional.

`seed_prestamo_demo.py` fija ids explicitos (prestamo 7, renglon 11, media
39-42, evento 21, usuarios 4 y 12) porque
`docs/contratos/fixtures/prestamo_demo.json` es el criterio de aceptacion del
payload y el cliente mockea contra la copia literal.

En `presupuesto.db` la cuenta `melisa` ya existe con id 2, asi que el seed se
detiene con un mensaje explicito en vez de reasignar el id.

Es el comportamiento correcto —sobrescribir la cuenta de una persona para cuadrar
un fixture es peor que no sembrar— pero conviene saberlo: **el prestamo demo solo
se puede sembrar en una base limpia**. La guardia de contrato de S7 usa la base
de pruebas, que se recrea en cada prueba, asi que ahi si corre.

---

## R-SRV-09 — El indice unico parcial no conoce `is_deleted`

**Sev:** medio. **Estado:** mitigado por convencion, sin red de seguridad en la base.

`ux_loan_item_equipo_abierto` bloquea por `devuelto_at IS NULL` y nada mas. La
formula de disponibilidad ademas excluye prestamos con `is_deleted = 1`.

Si un prestamo se borra logicamente **sin cerrar sus renglones**, los dos dejan
de coincidir: la pantalla muestra el equipo disponible y `POST /items` da un
error de integridad. Igual con cancelar.

Convencion que la API tiene que respetar (S4): **toda operacion que libere un
equipo escribe `devuelto_at`** — cancelar, confirmar devolucion, borrar el
prestamo. Esta escrita en el docstring de `LoanItem` y hay una prueba que
documenta el hueco (`test_prestamo_borrado_libera_el_equipo_en_la_formula`).

No se puede cerrar en la base: SQLite no permite un indice parcial que consulte
otra tabla. La alternativa seria duplicar `is_deleted` en `loan_item`, que es
justo la doble fuente de verdad que el plan §4.2 elimina.

---

## R-SRV-04 — `GET /api/auth/me` puede devolver 503 y el cliente tiene que saberlo

**Sev:** alto. **Estado:** abierto, necesita acuerdo con el carril de interfaz.

Decision de S1: si la base falla al resolver permisos, `/api/auth/me` contesta
**503 `PERMISOS_NO_DISPONIBLES`**, no 200 con `permisos: {}`.

Por que asi: devolver `{}` es exactamente el 403 masivo que la regla del plan
(§10.6, leccion Bruckner) existe para evitar — la interfaz esconderia todo y se
leeria como politica.

Por que es riesgo: `/api/auth/me` es tipicamente lo primero que llama el cliente
al arrancar. Si su manejo de errores trata "me fallo" como "sesion invalida",
un 503 va a producir un deslogueo masivo, que es justo lo que queriamos evitar,
por el otro camino.

Que hace falta: que el cliente distinga 401 (desloguear) de 503 (reintentar,
mantener sesion). El contrato lo dice explicito en §0 —
"Jamas se interpreta como sesion invalida. No desloguear." — pero conviene
confirmarlo con quien construye la interfaz antes de integrar.

Hay prueba: `test_el_503_no_invalida_la_sesion`.

---

## R-SRV-05 — `RBAC_MODO=legacy` deja la aprobacion de equipos sin aprobadora

**Sev:** medio. **Estado:** abierto, documentado.

El rollback de §13 del plan apaga la consulta a las 3 tablas. Consecuencia que
el plan no escribe: **los paquetes aditivos dejan de aplicar**, asi que Melisa
pierde `equipos_aprobacion` y nadie mas que el `superadmin` puede autorizar
entregas ni confirmar devoluciones.

Por que importa: si alguien activa `legacy` a las 8 de la noche para destrabar
un problema de accesos, el lunes el modulo de equipos esta trabado y el motivo
no es obvio.

Mitigacion: documentado en `doc/rbac-aditivo.md` §Rollback y en el docstring de
`rbac.modo_rbac()`. No hay forma de arreglarlo sin consultar la base, que es
justo lo que el rollback apaga. Es un rollback de emergencia, no un modo de
operacion.

---

## R-SRV-06 — La materializacion en base puede desincronizarse del catalogo

**Sev:** bajo. **Estado:** abierto con guardia.

El motor resuelve permisos desde `rbac_catalog.py` (codigo). Las tablas `roles`
y `role_permissions` son copia sembrada por la migracion.

Si alguien edita el catalogo y no corre la migracion, la pantalla de
administracion muestra un mundo (la tabla) y el motor decide con otro (el
codigo). Nadie ve un error.

Mitigacion: `test_materializacion_en_base_coincide_con_el_catalogo` en
`backend/tests/rbac/test_catalogo_contrato.py` se pone roja si divergen. La
siembra ademas **reconcilia**: borra las filas que ya no estan en el catalogo,
no solo agrega las nuevas.

Pendiente real: nada obliga a correr la migracion en el despliegue. Cuando exista
el runbook de deploy de este modulo, `migrate_rbac_aditivo.py` tiene que quedar
en la lista de pasos obligatorios.

---

## R-SRV-01 — Conteo de pruebas del plan esta desfasado

**Sev:** bajo. **Estado:** abierto, informativo.

`CLAUDE.md` y el plan (§12) dicen 167 pruebas. La suite real en `dami-branch`
tiene **169**. La asignacion dice 167, el encargo verbal dice 169.

Por que importa: el criterio de cierre es "las existentes siguen verdes". Si
alguien compara contra 167 y ve 169, no sabe si sobran dos o si el documento
esta viejo.

Mitigacion: uso 169 como linea base y lo dejo escrito en cada entrada de
`docs/avances/servidor.md`. Que lo corrija quien sea dueño de `CLAUDE.md` — yo
no lo edito.

---

## R-SRV-02 — reportlab instalado es 5.0.0, el plan asumia la serie 4

**Sev:** bajo. **Estado:** abierto.

`requirements.txt` pide `reportlab>=4.2.0`. `pip` resolvio **5.0.0** en Python
3.14.6. El plan (§6) se escribio contra la serie 4.

Por que importa: la serie 5 puede haber movido APIs de `platypus`. Si el PDF de
S5 se escribe contra 5.0.0 y produccion instala una 4.x vieja, el generador
truena en el unico entorno que importa.

Mitigacion: cuando S5 este escrito y probado contra 5.0.0, subir el piso de
`requirements.txt` a la version exacta que compilo el PDF. Pendiente en
`docs/backlog_servidor.md`.

---

## R-SRV-03 — freezegun arrastro python-dateutil como dependencia nueva

**Sev:** informativo. **Estado:** cerrado, sin accion.

`freezegun` instalo `python-dateutil 2.9.0.post0` de transitiva. Es dependencia
de **desarrollo**, no entra a `requirements.txt` de produccion. Lo anoto para que
nadie se sorprenda de verla en `pip list`.
