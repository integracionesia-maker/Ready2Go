# Documentación — GOCreate

> Plataforma de Marketing (Presupuestos + Control de Equipos) — Grupo Ortiz
> Última reestructuración: 2026-07-30

## Estructura

```
docs/
├── README.md                          ← Este archivo
├── presupuestos/                      ← Módulo de Presupuestos
│   ├── auth/                          ← Autenticación (compartida)
│   ├── presupuestos-y-validacion.md   ← Reglas de negocio de presupuestos
│   ├── borrado-tickets.md             ← Sistema de borrado lógico/físico
│   ├── gastos-generales-manual.md     ← Gastos generales
│   └── responsividad-movil.md         ← Infraestructura responsive
├── equipos/                           ← Módulo de Control de Equipos
│   ├── plan-quirurgico.md             ← Plan maestro de integración
│   ├── asignacion-trabajo.md          ← Reparto de tareas (Damian/Beni)
│   ├── rbac-aditivo.md                ← RBAC aditivo (patrón Bruckner)
│   ├── contratos/                     ← Contrato de API + fixtures
│   ├── maqueta/                       ← Maqueta HTML de marketing (referencia)
│   └── prompts/                       ← Prompts de implementación de Equipos
├── historico/                         ← Archivo histórico
│   ├── changelog-*.md                 ← Changelogs por carril
│   ├── avances-*.md                   ← Bitácoras de avances diarios
│   ├── backlog-*.md                   ← Backlogs por carril
│   ├── riesgos-*.md                   ← Registros de riesgos por carril
│   ├── prompt-*.md                    ← Prompts históricos ya ejecutados
│   ├── auditoria-responsividad-movil.md ← Auditoría original de responsive
│   └── plan-gastos-generales*.md      ← Plan de R12 (ya implementado)
├── deploy/                            ← Infraestructura y despliegue
│   ├── migracion-macmini.md           ← Migración droplet → Mac mini (túnel, datos, ventana)
│   ├── runbook.md                     ← Runbook de deploy (Mac Mini)
│   └── recordatorios-launchagent.md   ← LaunchAgent de recordatorios
└── presentaciones/                    ← Material de difusión
    └── presentacion-ejecutivos.html   ← Deck para dirección (8 diapositivas, autocontenido)
```

---

## Presupuestos

Módulo de control de presupuesto para creadores de contenido. En producción, uso interno.

| Documento | Contenido |
|-----------|-----------|
| [`presupuestos/auth/auth-arquitectura.md`](presupuestos/auth/auth-arquitectura.md) | Arquitectura de autenticación: JWT, cookies, roles, matriz de permisos, 167 tests. **Referencia definitiva.** |
| [`presupuestos/auth/auth-manual-usuario.md`](presupuestos/auth/auth-manual-usuario.md) | Manual por rol: superadmin, admin, creador. Flujos, pantallas, E2E. |
| [`presupuestos/presupuestos-y-validacion.md`](presupuestos/presupuestos-y-validacion.md) | Reglas de negocio: ciclos de presupuesto, validación de tickets, prioridad de marcas (R7/R9/R10/R11). |
| [`presupuestos/borrado-tickets.md`](presupuestos/borrado-tickets.md) | Sistema de borrado en dos niveles (soft/hard delete) con reversión de ciclo (R12). |
| [`presupuestos/gastos-generales-manual.md`](presupuestos/gastos-generales-manual.md) | Gastos generales: creación, conteo, borrado. Independientes de creadores y ciclos (R12). |
| [`presupuestos/responsividad-movil.md`](presupuestos/responsividad-movil.md) | Infraestructura responsive: `useMobile`, `RowActions`, `go-table-scroll-wrapper`. Qué se implementó y cómo usarlo. |

---

## Control de Equipos

Módulo de préstamo de equipo de grabación. **Plan aprobado, en construcción (dami-branch).**

| Documento | Contenido |
|-----------|-----------|
| [`equipos/plan-quirurgico.md`](equipos/plan-quirurgico.md) | Plan maestro de integración: RBAC aditivo, modelo de datos (10 tablas), API, PDF, correo. **Lectura obligatoria antes de tocar cualquier cosa de Equipos.** |
| [`equipos/firma-pendiente-al-confirmar.md`](equipos/firma-pendiente-al-confirmar.md) | `confirmar` ya no exige ninguna firma; cada una (aprobador/beneficiario) se completa después por su lado. Paquete singleton `TITULAR_FIRMA_EQUIPO`: quién puede firmar `firma_entrega` de verdad (identidad, no permiso) y de quién es el nombre por default en la carta antes de que exista una firma. |
| [`equipos/asignacion-trabajo.md`](equipos/asignacion-trabajo.md) | Reparto de tareas: carril servidor (Damian) + carril interfaz (Beni). Paquetes WP1-WP6. |
| [`equipos/rbac-aditivo.md`](equipos/rbac-aditivo.md) | Diseño del RBAC aditivo: motor, catálogo, tablas, endpoints de roles y paquetes. |
| [`equipos/contratos/API_EQUIPOS_v1.md`](equipos/contratos/API_EQUIPOS_v1.md) | Contrato de API v1 **congelado**. 24 endpoints, matriz de permisos, máquina de estados, reglas de media. |
| [`equipos/contratos/openapi_equipos_v1.json`](equipos/contratos/openapi_equipos_v1.json) | OpenAPI 3.0 del servidor real (22 endpoints, 35 schemas). Companion técnico del contrato. |
| [`equipos/contratos/permisos_catalogo.json`](equipos/contratos/permisos_catalogo.json) | Catálogo de permisos RBAC: 8 módulos, 15 paquetes (incluye el singleton `TITULAR_FIRMA_EQUIPO`), 5 reglas. **Congelado.** |
| [`equipos/contratos/tokens_marca.md`](equipos/contratos/tokens_marca.md) | Tokens visuales para el PDF de responsiva (colores, fuentes). |
| [`equipos/contratos/auth_me.json`](equipos/contratos/auth_me.json) | Forma exacta de `GET /api/auth/me` con campo `permisos`. |
| [`equipos/contratos/fixtures/`](equipos/contratos/fixtures/) | Fixtures: empresas (3), equipos (8), errores (7 códigos), préstamo demo. |
| [`equipos/maqueta/CONTROL_DE_EQUIPOS_maqueta_mkt.htm`](equipos/maqueta/CONTROL_DE_EQUIPOS_maqueta_mkt.htm) | Maqueta HTML original de marketing (referencia funcional — **su implementación NO se porta**; ver plan §1.3). |
| [`equipos/prompts/unificacion-visual-equipos.md`](equipos/prompts/unificacion-visual-equipos.md) | Prompt para unificar visualmente Equipos con Presupuestos (pendiente de ejecutar). |

---

## Gastos Operativos

**Fusionado dentro de Presupuestos → Gastos Generales (WP fusión, sept-2026)**: ya no es un módulo aparte con switch ni rol propio — ver [`presupuestos/gastos-generales-manual.md`](presupuestos/gastos-generales-manual.md). Los documentos del diseño original (tablas propias por rubro, rol `operativo`, aislamiento total de marketing) quedaron como referencia histórica en [`historico/gastos-operativos-plan-implementacion.md`](historico/gastos-operativos-plan-implementacion.md) y [`historico/gastos-operativos-manual-usuario.md`](historico/gastos-operativos-manual-usuario.md).

---

## Histórico

Registros de lo que pasó durante el desarrollo. Organizados por carril (interfaz/servidor).

| Documento | Contenido |
|-----------|-----------|
| [`historico/changelog-interfaz.md`](historico/changelog-interfaz.md) | Changelog del carril interfaz (I0-I8, commits, capturas). |
| [`historico/changelog-servidor.md`](historico/changelog-servidor.md) | Changelog del carril servidor (S0-S7, WP1-WP6). |
| [`historico/avances-interfaz.md`](historico/avances-interfaz.md) | Bitácora diaria de avances del frontend. |
| [`historico/avances-servidor.md`](historico/avances-servidor.md) | Bitácora diaria de avances del backend. |
| [`historico/backlog-interfaz.md`](historico/backlog-interfaz.md) | Backlog detallado del carril interfaz (I0-I8 con commits). |
| [`historico/backlog-servidor.md`](historico/backlog-servidor.md) | Backlog detallado del carril servidor (S0-S7, todos "hecho"). |
| [`historico/riesgos-interfaz.md`](historico/riesgos-interfaz.md) | Riesgos del frontend (R-I01 a R-I14). |
| [`historico/riesgos-servidor.md`](historico/riesgos-servidor.md) | Riesgos del servidor (R-SRV-13, R-SRV-14, etc.). |
| [`historico/auditoria-responsividad-movil.md`](historico/auditoria-responsividad-movil.md) | Auditoría original de responsive (21 hallazgos) — las correcciones están en `presupuestos/responsividad-movil.md`. |
| [`historico/plan-gastos-generales-y-borrado-tickets.md`](historico/plan-gastos-generales-y-borrado-tickets.md) | Plan de implementación de R12 — la implementación real está en `presupuestos/gastos-generales-manual.md` y `presupuestos/borrado-tickets.md`. |

### Prompts históricos (ya ejecutados)

| Documento | Contenido |
|-----------|-----------|
| [`historico/prompt-sistema-autenticacion.md`](historico/prompt-sistema-autenticacion.md) | Prompt original del sistema de autenticación (Fase 2-3, YA EJECUTADO). |
| [`historico/prompt-mejoras-integrales.md`](historico/prompt-mejoras-integrales.md) | Prompt de mejoras R1-R11 (YA EJECUTADO). |
| [`historico/prompt-pantalla-carga.md`](historico/prompt-pantalla-carga.md) | Prompt de loading screen + orden de tablas (YA EJECUTADO). |

---

## Deploy

| Documento | Contenido |
|-----------|-----------|
| [`deploy/migracion-macmini.md`](deploy/migracion-macmini.md) | **Migración del droplet Ubuntu a la Mac mini**, conservando la base y el dominio `gocreate.mx`. Inventario del servidor en vivo, cómo se mueve el túnel de Cloudflare, trampas del proyecto (WAL, cwd relativo), ventana paso a paso, verificación y rollback. **Preparado, no ejecutado.** |
| [`deploy/runbook.md`](deploy/runbook.md) | Runbook de deploy en Mac Mini on-premise: LaunchDaemon, backups, hardening. ⚠️ Anterior al deploy actual con Cloudflare Tunnel — su §6 (Caddy) **ya no aplica**, ver §2 de `migracion-macmini.md`. |
| [`deploy/recordatorios-launchagent.md`](deploy/recordatorios-launchagent.md) | LaunchAgent de macOS para el script de recordatorios de vencimiento. 8 variables SMTP requeridas. |

---

## Presentaciones

| Documento | Contenido |
|-----------|-----------|
| [`presentaciones/presentacion-ejecutivos.html`](presentaciones/presentacion-ejecutivos.html) | Deck de 8 diapositivas para dirección: qué es GOCreate, el problema que resuelve, antes/después, los tres módulos, y cierre con demo en vivo. Autocontenido (imágenes en base64) — se abre en cualquier navegador, sin servidor. Navegación con ← →, `F` para pantalla completa. |

---

## Fuera de `docs/`

Estos archivos en la raíz complementan la documentación:

| Archivo | Contenido |
|---------|-----------|
| `CLAUDE.md` | Instrucciones para agentes AI: reglas críticas, stack, convenciones. **Leer primero.** |
| `frontend/CLAUDE.md` | Convenciones de frontend: theming, PDF, ApexCharts, responsividad. |
| `backend/CLAUDE.md` | Convenciones de backend: rutas relativas, seeds. |
| `CHANGELOG.md` | Changelog maestro del proyecto (hitos, no commits individuales). |
| `BACKLOG.md` | Backlog maestro (Presupuestos + Equipos). |
| `RISKS.md` | Registro de riesgos maestro (8 activos + 9 cerrados). |
| `DESIGN_SYSTEM.md` | Sistema de diseño: Liquid Glass, tipografía Blauer Nue/Conthic, tokens. |
| `status.md` | Dashboard de estado del proyecto (semáforo, fases, carriles). |
| `MVP_BREAKDOWN.md` | Desglose de MVP: Módulo A (Presupuestos) + Módulo B (Equipos). |

---

## Cómo navegar esto

1. **¿Vas a desarrollar?** Empieza por `CLAUDE.md` (raíz).
2. **¿Vas a tocar Presupuestos?** Ve a [`presupuestos/`](presupuestos/).
3. **¿Vas a tocar Equipos?** Ve a [`equipos/plan-quirurgico.md`](equipos/plan-quirurgico.md) primero, luego al resto de [`equipos/`](equipos/).
4. **¿Quieres ver qué pasó antes?** [`historico/`](historico/).
5. **¿Vas a deployar o migrar el servidor?** [`deploy/migracion-macmini.md`](deploy/migracion-macmini.md) para la migración a la Mac mini; [`deploy/runbook.md`](deploy/runbook.md) para el contexto previo.
