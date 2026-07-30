# Manual de usuario — Autenticación, roles, presupuestos y validación

> Incluye los flujos del paquete R1-R11 (temas, header/popover, ciclos de presupuesto, validación de tickets, prioridad de marcas, visor de comprobantes, PDF, responsividad) y del paquete R12 (gastos generales, borrado lógico/físico de tickets). Reglas de negocio detalladas en `docs/presupuestos/presupuestos-y-validacion.md`, `docs/presupuestos/gastos-generales-manual.md` y `docs/presupuestos/borrado-tickets.md`.

## Iniciar sesión

1. Entra a la app; si no tienes sesión, te lleva automáticamente a `/login`.
2. Escribe tu **usuario o correo** y tu contraseña. Presiona "Iniciar sesión".
3. Si es tu primer ingreso (o un administrador te reseteó la contraseña), el sistema te pedirá **cambiarla obligatoriamente** antes de dejarte usar el resto de la app.

Si escribes mal la contraseña varias veces, tu cuenta se bloquea temporalmente unos minutos (el bloqueo crece si sigues intentando). El mensaje de error es el mismo si el usuario no existe, la contraseña es incorrecta, o la cuenta está desactivada — por seguridad, no se distingue cuál fue el caso.

## Cambiar tu contraseña

Ve a **Mi Perfil** (ícono en la barra lateral) → sección "Cambiar contraseña". Necesitas tu contraseña actual, la nueva (mínimo 10 caracteres, con letras y números, no puede ser igual a tu usuario) y confirmarla. Tu sesión actual sigue activa después del cambio; las demás sesiones abiertas (si iniciaste sesión en otro dispositivo) se cierran.

## Qué ves según tu rol

| Rol | Ves en la barra lateral | Puedes hacer |
|---|---|---|
| **Superadministrador** | Todo, incluida "Usuarios" | Todo lo del Administrador, **más** gestionar usuarios (crear/editar/resetear contraseña/activar-desactivar) |
| **Administrador** | Inicio, Dashboard, Creadores, Transacciones, Validación, Gastos Generales, Administración (Creadores/Marcas) | Gestionar creadores y marcas, asignar presupuestos por ciclo, validar tickets de cualquier creador, descargar el PDF del dashboard, registrar/eliminar gastos generales, eliminar tickets (lógico o permanente). **No** gestiona usuarios (ver más abajo) |
| **Creador** | Inicio, Transacciones, Mi Perfil | Ver y subir **solo tus propios** tickets (nacen pendientes hasta que un admin los valide); ver tu ciclo de presupuesto en Mi Perfil |

Si entras a una URL que tu rol no puede ver, te muestra una página de "Acceso no autorizado" (no un error).

El **header superior** (logo + "Grupo Ortiz") es fijo y está en todas las vistas. A la derecha tiene el interruptor de tema (sol/luna) y tu foto/iniciales — haz click ahí para abrir el menú de perfil ("Mi perfil" / "Cerrar sesión"); se cierra con click afuera, con `Escape`, o al navegar. En pantallas angostas (celular), un ícono de hamburguesa junto al logo abre el menú lateral como un panel deslizable.

## Tema claro/oscuro

El botón de sol/luna en el header cambia el tema al instante, sin parpadeo al recargar la página. Tu elección se guarda en el navegador (no en el servidor) y se mantiene entre sesiones. Aplica a toda la app, incluidas las gráficas del dashboard.

---

## Para Superadmin: gestión de usuarios

**Solo el superadministrador** ve y usa **Administración → Usuarios** — un administrador que intente entrar a esos endpoints directamente recibe acceso denegado, y la pestaña ni siquiera aparece en su vista.

- **Crear usuario**: botón "Nuevo Usuario". Si el rol es "Creador", debes vincularlo a un Creador ya existente (créalo primero en Administración → Creadores si hace falta — eso sí lo puede hacer un administrador). Si no escribes una contraseña, el sistema genera una temporal — anótala, se muestra una sola vez.
- **Resetear contraseña**: genera una nueva contraseña temporal para ese usuario (debe cambiarla en su próximo login). También se muestra una sola vez — compártela por un canal seguro (no por correo sin cifrar ni chat público).
- **Activar/Desactivar**: una cuenta desactivada no puede iniciar sesión.

La cuenta superadmin no se puede desactivar ni degradar desde ningún lugar de la app (es intencional: es la única cuenta de ese tipo).

## Para Admin/Superadmin: presupuestos por ciclo

En **Administración → Creadores**, al crear o editar un creador defines:
- **Monto del ciclo**: el presupuesto que se renueva automáticamente cada periodo.
- **Periodicidad**: Semanal (lunes a domingo) o Mensual (calendario).

El ciclo se renueva solo (no hay que hacer nada manualmente) y **no acumula sobrante** — lo que no se gastó en un ciclo no pasa al siguiente. Si cambias el monto o la periodicidad, **el ciclo en curso no se toca**; el cambio aplica desde el próximo ciclo. Cada creador muestra su ciclo vigente (gastado/restante/días que quedan) en la tabla de Creadores, y el botón "Histórico" abre sus ciclos pasados con los montos de cada uno.

Un ciclo **puede quedar en negativo** si apruebas tickets que superan el restante — la app te avisa con una advertencia, pero nunca te bloquea; la decisión final siempre es tuya.

## Para Admin/Superadmin: validar tickets de creadores

Los tickets que sube un **creador** nacen **pendientes** y no descuentan nada hasta que los revisas en **Validación** (un badge junto a ese ítem del menú muestra cuántos hay pendientes). Ahí, por cada ticket puedes:
- **Ver**: abre el comprobante (imagen con zoom o PDF) sin descargarlo.
- **Aprobar**: descuenta del ciclo del creador correspondiente a la fecha en que subió el ticket (no la fecha en que lo apruebas — si tardaste semanas en revisarlo, se descuenta del ciclo original, no del vigente hoy).
- **Rechazar**: debes escribir un motivo; el creador lo verá junto a su ticket rechazado y puede volver a subirlo.

Los tickets que sube un **admin o superadmin** (a nombre de cualquier creador) se aprueban y descuentan automáticamente — el flujo de validación es solo para lo que sube un creador sobre sí mismo.

## Prioridad de marcas

Cada marca tiene una prioridad — **Alta**, **Media** (default) o **Baja** — que editas en Administración → Marcas. Se ve como una etiqueta de color en Transacciones, Validación y el desglose del dashboard, y las marcas de mayor prioridad aparecen primero en listados y selectores.

## Reporte en PDF del dashboard

Botón "Descargar PDF" en el Dashboard (solo admin/superadmin): genera un PDF con los KPIs, las gráficas y las tablas de desglose (por marca y por creador) tal como se ven en pantalla, con branding de Grupo Ortiz, para el período que tengas seleccionado en el filtro de fechas (incluye los atajos "Este mes", "Mes pasado", etc., o un rango personalizado).

## Para Admin/Superadmin: Gastos Generales

Sección **Gastos Generales** (barra lateral, entre Validación y Administración): gastos operativos que **no** están ligados a ningún creador ni marca (suscripciones, servicios, herramientas internas). No tienen ciclo de presupuesto ni pasan por validación — se registran y cuentan de inmediato.

- **Nuevo Gasto General**: descripción, monto y comprobante (mismas reglas de archivo que un ticket: JPG/PNG/PDF, máx. 10 MB).
- **Exportar**: elige uno o más de los últimos 12 meses y genera un PDF propio (independiente del PDF del Dashboard) con el detalle y el total.
- **Eliminar**: igual mecanismo de dos niveles que los tickets — ver la siguiente sección.

El Dashboard incluye una gráfica y un KPI de Gastos Generales para el período filtrado, y el PDF del Dashboard también los incluye. Detalle completo: `docs/presupuestos/gastos-generales-manual.md`.

## Para Admin/Superadmin: eliminar tickets

Cualquier ticket (en Transacciones o en Validación) tiene un botón **"Eliminar"**, con dos niveles:

1. **Eliminar** (borrado lógico): el ticket deja de contar en listados, Dashboard y reportes, pero el registro y el comprobante se conservan — es reversible en el sentido de que queda auditado, aunque no hay un botón de "restaurar" en la UI todavía. Si el ticket estaba **aprobado**, su monto se devuelve al ciclo de presupuesto del creador.
2. **Eliminar permanentemente**: un segundo paso con advertencia en rojo, ⚠️ **irreversible** — borra el registro y el archivo para siempre. Úsalo solo cuando estés seguro.

Un creador nunca ve estos botones (ni en su propia vista de Transacciones). Detalle completo, incluida la tabla de impacto por estado del ticket: `docs/presupuestos/borrado-tickets.md`.

## Para Creadores: tu presupuesto y tickets

- **Mi Perfil** muestra tu ciclo de presupuesto vigente: periodicidad, fechas del ciclo actual, monto, gastado y restante.
- **Nuevo Ticket** (botón naranja de la barra lateral): tu nombre ya viene preseleccionado y no se puede cambiar — solo puedes registrar gastos a tu propio nombre. Tu ticket queda **pendiente de validación** — no se descuenta de tu presupuesto hasta que un administrador lo apruebe.
- **Transacciones** muestra únicamente tus propios tickets, con su estado (Pendiente/Aprobado/Rechazado). Si uno fue rechazado, el motivo aparece al pasar el cursor sobre la etiqueta — puedes volver a subir el ticket corregido como uno nuevo.

## Si perdiste el acceso

- **Olvidaste tu contraseña (rol Creador o Administrador)**: pide a un administrador o al superadmin que te haga un reset desde Administración → Usuarios.
- **El superadmin perdió su contraseña y no hay otra cuenta con acceso**: esto requiere acceso al servidor (no se puede resolver desde la app, a propósito — la cuenta superadmin es inmutable por API). Desde `backend/`, ejecutar:
  ```
  python reset_superadmin_password.py --password "NuevaClaveSegura123!"
  ```
  Esto resetea la contraseña directamente en la base de datos y obliga a cambiarla en el siguiente login.

---

## Para desarrolladores: correr las pruebas

**Suite pytest** (matriz de permisos, login, tokens — usa su propia base de datos de prueba, nunca `presupuesto.db`):
```
cd backend
python -m pytest
```

**Suite E2E (Playwright)** — requiere un backend y un frontend dedicados a pruebas, con una base de datos separada, para no interferir con tu sesión de desarrollo normal en el puerto 8000/5173:
```
# Terminal 1 — backend de pruebas con su propia DB
cd backend
python seed_auth.py --username superadmin --email superadmin@e2e.grupo-ortiz.com --password "SuperClaveE2E123!" 
# (usar DATABASE_URL=sqlite:///./test_e2e.db antes de este comando y del siguiente)
JWT_SECRET_KEY=e2e-test-secret-0123456789abcdef ENV=development DATABASE_URL=sqlite:///./test_e2e.db CORS_ORIGINS=http://127.0.0.1:5175 python -m uvicorn app.main:app --host 127.0.0.1 --port 8793

# Terminal 2 — frontend apuntando a ese backend
cd frontend
VITE_BACKEND_PORT=8793 npx vite --host 127.0.0.1 --port 5175

# Terminal 3 — la suite (los archivos por separado, ver nota de rate-limit abajo)
cd frontend
E2E_SUPERADMIN_PASSWORD="SuperClaveE2E123!" E2E_BASE_URL="http://127.0.0.1:5175" npx playwright test e2e/auth.spec.js
E2E_SUPERADMIN_PASSWORD="SuperClaveE2E123!" E2E_BASE_URL="http://127.0.0.1:5175" npx playwright test e2e/presupuesto-flujo-completo.spec.js
E2E_SUPERADMIN_PASSWORD="SuperClaveE2E123!" E2E_BASE_URL="http://127.0.0.1:5175" npx playwright test e2e/gastos-generales.spec.js
```
Borra `backend/test_e2e.db` antes de repetir el flujo completo desde cero (el superadmin es idempotente, pero los usuarios/creadores que crea la prueba no lo son entre corridas con la misma base).

**Nota sobre el rate limit de login**: el backend limita a 30 intentos de login por IP cada 15 minutos (defensa contra fuerza bruta, ver `docs/presupuestos/auth/auth-arquitectura.md` §4). Cada archivo de la suite se mantiene bien por debajo de eso, pero si el superadmin ya no tiene la contraseña sembrada (por ejemplo, porque `auth.spec.js` la cambió en una corrida anterior en la misma DB), usa `python reset_superadmin_password.py --password "..."` antes de repetir.
