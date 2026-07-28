# Riesgos — carril servidor y datos (Control de Equipos)

Lo que descubro que puede fallar. No lo que ya esta mitigado en el plan.

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
