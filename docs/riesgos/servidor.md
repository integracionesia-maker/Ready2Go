# Riesgos — carril servidor y datos (Control de Equipos)

Lo que descubro que puede fallar. No lo que ya esta mitigado en el plan.

---

## R-SRV-11 — CRITICO: cualquiera del area puede escribir en el prestamo de otro

**Sev:** critico. **Estado:** abierto. **Decision de contrato, no la tomo yo.**

El contrato §3 y §5 piden **solo el permiso** `equipos_prestamos:solicitar` para
`POST /api/loans/{id}/items`, `POST /api/loans/{id}/media` y
`POST /api/loans/{id}/confirmar`. No exigen participacion en el prestamo.

Ese permiso lo tiene **todo** `colaborador_mkt`. Tal cual esta escrito el
contrato, cualquiera del area de marketing puede, poniendo el id ajeno en la
ruta: agregar equipos al prestamo de otra persona, **subir la firma de otro**, y
**confirmar** el prestamo generando una carta responsiva a su nombre.

Es la misma clase de agujero que el hallazgo §10.4 del plan (CRITICO: "firma sin
auth; cualquiera elige Melisa en un `<select>` y aprueba"), pero por la puerta de
escritura en vez de la de aprobacion. La lectura si esta protegida —el contrato
si exige "participante o ver_global" en los GET— asi que el hueco es asimetrico y
por eso pasa desapercibido leyendo la tabla.

**No lo cerre por mi cuenta**, aunque el arreglo es de tres lineas: endurecer un
solo lado es el modo tipico de falla de este reparto (un 403 que el cliente no
espera). Propuesta concreta para v1.1: exigir en esas tres rutas participante
(creador o responsable) **o** `equipos_prestamos:ver_global`.

Ojo con el efecto colateral antes de aprobarlo: `POST /media` es tambien la ruta
por la que se suben las fotos de devolucion, y quien recibe fisicamente el equipo
no siempre es el responsable. Si se exige participacion, esa persona necesita
`ver_global` o quedarse fuera.

---

## R-SRV-12 — Las pruebas escribian dentro de la carpeta sincronizada con Drive

**Sev:** medio. **Estado:** cerrado, pero vale para todo el repo.

`backend/uploads/` vive dentro del repo, y el repo vive dentro de una carpeta
sincronizada con Drive. Las pruebas de media escribian ahi: cada archivo
disparaba una sincronizacion.

Sintoma: `test_aprobacion.py` tardo **2 h 27 min** en su primera corrida (contra
48 s ahora) y una prueba fallo con un error que no se reproducia — una peticion
devolvio error en vez de payload por contencion de disco.

Mitigado con una fixture autouse que apunta los directorios de media y de
responsivas a un temporal (`backend/tests/equipos/conftest.py`).

Lo que queda abierto para el proyecto: **cualquier prueba nueva que escriba
archivos tiene que usar `tmp_path`**. Y en produccion conviene que `uploads/`
NO quede dentro de una carpeta sincronizada — el Mac mini del deploy no deberia
tener Drive sincronizando los comprobantes ni las fotos de los prestamos.

---

## R-SRV-10 — Un equipo dado de baja desaparece de la interfaz por completo

**Sev:** medio. **Estado:** abierto, implementado segun el plan.

`POST /api/equipment/{id}/baja` hace borrado logico (`is_deleted=True`) ademas de
poner `estado_operativo='baja'`, tal como pide el plan §5 ("Soft delete") y su
regla de que el listado excluye `is_deleted`.

Consecuencia: el equipo deja de salir en el listado **y su ficha responde 404**
(contrato §0: `NO_ENCONTRADO` incluye recursos con borrado logico). El registro,
sus auditorias y su historial siguen en la base, pero no hay endpoint que los
muestre.

Escenario que lo va a hacer notar: se da de baja un celular robado; tres meses
despues RH pregunta quien lo tenia la ultima vez. Hoy no hay pantalla que lo
conteste — hay que ir a la base.

Opciones, todas cambian el contrato:

- Un filtro `?incluir_baja=true` en el listado.
- Que `GET /api/equipment/{id}` devuelva el equipo dado de baja en vez de 404.
- Separar "dar de baja" (operativo, sigue visible) de "borrar" (logico, 404).

La tercera es la que mas se parece a lo que el area pidio, pero no la decido yo.

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
