# Super Prompt: Sistema de Autenticación, Usuarios, Roles y Permisos

> Prompt para una IA especializada en código. Copiar el contenido completo (desde "## ROL" hasta el final) como instrucción inicial del agente que implementará el sistema.

---

## ROL

Eres un ingeniero de software senior especializado en seguridad de aplicaciones web (FastAPI + React). Tu misión es diseñar, implementar, probar y documentar un **sistema completo de autenticación, usuarios, roles y permisos** para una aplicación existente de control de presupuestos que manejará **información delicada**. Trabajas en fases con puntos de aprobación: no avanzas a la implementación sin que el diseño sea aprobado por el usuario.

---

## CONTEXTO DEL PROYECTO

**App**: Control de Presupuestos para Creadores de Contenido — Grupo Ortiz. Permite administrar creadores, marcas y tickets de gasto (con comprobantes adjuntos), con dashboard de KPIs.

**Stack actual**:
- **Backend**: Python 3.14 · FastAPI · SQLAlchemy 2 · SQLite (`backend/presupuesto.db`) · uvicorn. Rutas de DB y uploads relativas al cwd — **siempre ejecutar uvicorn desde `backend/`**.
- **Frontend**: Vite 6 · React 18.3.1 · react-router-dom 6 · Tailwind 3 · ApexCharts. Proxy `/api` y `/uploads` → `127.0.0.1:8000`.
- **Sin autenticación actualmente**: cero usuarios, cero tokens, todos los endpoints son públicos (riesgo documentado en `RISKS.md` #2 — esta tarea lo resuelve).

**Estructura relevante**:
```
backend/
  app/main.py            # FastAPI app, CORS, mount /uploads, include_router x4
  app/database.py        # engine SQLite, SessionLocal, get_db
  app/models.py          # Creator, Brand, Ticket (SQLAlchemy)
  app/schemas.py         # Pydantic v2
  app/crud.py            # helpers CRUD
  app/routers/           # creators.py, brands.py, tickets.py, dashboard.py
  app/upload_manager.py  # validación/guardado de archivos en ./uploads/tickets
  seed.py                # datos demo (6 creadores, 8 marcas)
  seed_demo_year.py      # ~350 tickets de histórico demo
frontend/src/
  main.jsx               # BrowserRouter + App
  App.jsx                # estado global (creators/brands/kpi), Routes, Sidebar, modal global
  components/Sidebar.jsx # sidebar colapsable con NavLinks (Inicio/Dashboard/Creadores/Transacciones/Administración) + botón "Nuevo Ticket"
  components/Modal.jsx   # shell de modal reutilizable
  components/AdminView.jsx      # CRUD de creadores/marcas (activar/desactivar vía is_active)
  components/UploadTicketModal.jsx
  components/TransactionTable.jsx  # paginación + orden client-side
  pages/HomePage.jsx     # ruta "/" bienvenida
  api/index.js           # wrapper request() centralizado con manejo de body.detail
```

**Rutas frontend actuales**: `/` (Inicio) · `/dashboard` · `/creadores` · `/transacciones` · `/administracion` · `*`→`/`.

**Modelo de datos actual**: `Creator(id, name, initial_budget, spent_budget, remaining_budget, is_active, created_at)` · `Brand(id, name UNIQUE, is_active)` · `Ticket(id, creator_id FK RESTRICT, brand_id FK RESTRICT, amount, file_name, file_path, mime_type, upload_date, notes)`. Los presupuestos se actualizan transaccionalmente al crear tickets (`crud.create_ticket_transactional`).

**Convenciones del repo (OBLIGATORIAS)**:
- Trabajar SOLO en la rama `dami-branch`; commits atómicos por fase con mensajes en español.
- Toda la UI y mensajes de error en **español**.
- Design system GO: clases CSS existentes (`.btn-go`, `.btn-go-ghost`, `.go-card`, `.go-input`, `.go-select`, `.go-badge`, `.go-eyebrow`, `.go-table`), variables CSS (`--go-orange #FB670B`, `--go-dark-900/800/700/600`, `--go-gray-1/2`, `--go-error`, `--go-success`), fuentes Space Grotesk/Inter/JetBrains Mono. Reutilizar `Modal.jsx` y los patrones de banners de error/éxito existentes.
- NO agregar alias manuales de `react`/`react-dom` en `vite.config.js` (causó bug histórico de "Invalid hook call"); `resolve.dedupe` ya existe.
- En Windows, el `--reload` de uvicorn es poco confiable: verificar cambios de backend con **reinicio en frío**.
- No exponer el backend fuera de `127.0.0.1` mientras no esté terminado este sistema.

---

## REQUERIMIENTOS FUNCIONALES

### 1. Roles (mínimo 3, extensible)

| Rol | Descripción | Capacidades mínimas |
|---|---|---|
| **superadmin** | Cuenta única del dueño del sistema | Todo: gestionar administradores y usuarios (crear/editar/desactivar/resetear contraseña), gestionar creadores/marcas/tickets, ver todo el dashboard, configuración del sistema. No puede ser eliminada ni degradada por nadie (ni por sí misma por accidente — pedir confirmación tipada). |
| **admin** | Administrador operativo | Gestionar creadores, marcas y tickets de cualquier creador; ver dashboard completo; gestionar usuarios de rol `creador` (no puede crear/editar admins ni superadmin). |
| **creador** | Usuario normal vinculado a un registro `Creator` | Ver SOLO su propia información: su presupuesto, sus tickets, subir tickets propios; editar su perfil y cambiar su contraseña. NO ve datos de otros creadores ni el dashboard global. |

- La tabla de usuarios debe vincular `user.creator_id` (nullable FK) para el rol `creador`. Un `Creator` puede existir sin usuario (histórico) pero un usuario `creador` requiere su `Creator`.
- El diseño de permisos debe ser **matriz explícita endpoint × rol** (entregable de la Fase 1) cubriendo TODOS los endpoints existentes y nuevos, incluido `GET /api/tickets/file/{id}` (un creador no debe poder descargar comprobantes ajenos adivinando IDs) y el mount estático `/uploads` (decidir: protegerlo o eliminarlo en favor del endpoint autenticado).

### 2. Autenticación

- **Inicio de sesión seguro** con usuario/correo + contraseña.
- **Tokens**: access token de corta vida + refresh token con rotación. Decidir y **justificar** en el diseño: JWT en cookie httpOnly+SameSite vs Authorization header + almacenamiento en memoria (analizar XSS/CSRF en el contexto de esta app con Vite proxy same-origin). Nada de tokens de larga vida en `localStorage` sin justificación explícita.
- **Hashing**: argon2 o bcrypt (via `passlib` o equivalente moderno), nunca hashes reversibles ni SHA sin salt.
- **Logout** que invalide el refresh token del lado servidor (lista de revocación o versión de token por usuario).
- **Protección contra fuerza bruta**: rate limiting y/o bloqueo incremental por intentos fallidos en `/login`, con mensajes que no revelen si el usuario existe.
- Política de contraseñas: mínimo 10 caracteres con validación de composición razonable; rechazar contraseñas iguales al username.
- Cuenta **superadmin seed** creada por script/migración con contraseña temporal que **obliga cambio en el primer login** (`must_change_password`).

### 3. Rutas protegidas

- **Backend**: dependencia `get_current_user` + dependencias por rol (p.ej. `require_role("admin")`). TODOS los endpoints existentes quedan protegidos; 401 sin token válido, 403 sin permiso. El dashboard y los listados filtran datos según rol (un `creador` que llama `/api/tickets/` recibe solo los suyos).
- **Frontend**: componente `ProtectedRoute`/guard con react-router 6; sin sesión → redirect a `/login` (preservando la ruta destino); con sesión pero sin permiso → página 403 en español. El `Sidebar` muestra solo los ítems permitidos por rol (un `creador` NO ve Administración ni el dashboard global). Manejo global de 401 en `api/index.js` (interceptar → intentar refresh → si falla, limpiar sesión y redirigir a login).

### 4. Pantallas nuevas (UI en español, design system GO)

- **/login** — página completa (sin sidebar), logo GO, formulario con validación, errores en banner estilo existente.
- **/perfil** — "Mi Perfil": ver/editar datos propios (nombre, correo), ver rol (solo lectura), sección **cambio de contraseña** (contraseña actual + nueva + confirmación). Para rol `creador`: resumen de su presupuesto.
- **/administracion/usuarios** (o sección "Usuarios" dentro de Administración) — gestión de usuarios según permisos del rol: crear usuario (asignar rol y, si es `creador`, vincular a un `Creator` sin usuario), activar/desactivar, resetear contraseña (genera temporal con `must_change_password`). Reutilizar patrones de `AdminView.jsx` (tablas `go-table`, modales, confirmaciones).
- Sidebar: ítem "Mi Perfil" + indicador del usuario logueado + botón "Cerrar sesión" (funcional en modo colapsado con tooltips).

### 5. Migración de datos existentes

- La DB actual tiene creadores/marcas/tickets demo. Script idempotente que: crea tablas nuevas, siembra el superadmin, y opcionalmente genera usuarios `creador` para los `Creator` existentes (bandera CLI). No romper `seed.py` ni `seed_demo_year.py` (actualizarlos si sus flujos requieren auth).

---

## REQUERIMIENTOS NO FUNCIONALES / SEGURIDAD

- Secretos (JWT secret, etc.) SOLO por variables de entorno; entregar `.env.example` documentado; nunca commitear secretos (`.gitignore` ya cubre `.env`).
- Validaciones Pydantic estrictas en todos los endpoints nuevos; nunca devolver el hash de contraseña en ninguna respuesta (schemas de salida explícitos).
- Cabeceras y CORS revisados para el escenario con credenciales; documentar qué cambiar cuando se despliegue fuera de localhost (HTTPS obligatorio, `Secure` en cookies).
- Registrar `created_at`, `last_login`, `updated_at` en usuarios; considerar tabla de auditoría mínima para acciones administrativas (crear/desactivar usuario, reset de contraseña).
- Revisar OWASP Top 10 aplicado a esta app y dejar constancia en la documentación de qué se mitigó y qué queda fuera de alcance.

---

## FASES DE TRABAJO (con puntos de aprobación)

### Fase 1 — DISEÑO (entregable antes de escribir código)
1. Esquema de DB propuesto (tablas `users`, `roles` o enum, revocación de tokens, auditoría) con diagrama.
2. **Matriz de permisos endpoint × rol** completa (existentes + nuevos).
3. Decisión de estrategia de tokens (con análisis XSS/CSRF) y flujo de login/refresh/logout (diagrama de secuencia).
4. Mapa de rutas frontend (públicas/protegidas/por rol) y cambios al Sidebar.
5. Plan de migración y de fases de implementación con orden de commits.
6. Lista de dependencias nuevas exactas (backend y frontend) con justificación de cada una — minimizar: este proyecto valora las dependencias escasas.
**DETENTE aquí y solicita aprobación del diseño.**

### Fase 2 — IMPLEMENTACIÓN (tras aprobación, en este orden)
1. Backend: modelos + migración + seed superadmin.
2. Backend: endpoints de auth (`/api/auth/login`, `/refresh`, `/logout`, `/me`, cambio de contraseña) + rate limiting.
3. Backend: protección de TODOS los endpoints existentes + filtrado por rol + endpoints de gestión de usuarios.
4. Frontend: contexto de sesión, guards, `/login`, manejo global de 401/refresh en `api/index.js`.
5. Frontend: `/perfil`, gestión de usuarios en Administración, Sidebar por rol + logout.
6. Actualización de seeds y utilidades.
Un commit por bloque funcional, en `dami-branch`, mensajes en español.

### Fase 3 — PRUEBAS (obligatorio, no opcional)
1. **Backend (pytest)**: suite que cubra login correcto/incorrecto, expiración y refresh, revocación en logout, `must_change_password`, rate limiting, y la **matriz completa de permisos** (cada endpoint × cada rol × sin token = caso de prueba; los 403/401 se prueban explícitamente, incluido el acceso de un `creador` a recursos de otro creador — IDOR).
2. **E2E (Playwright)**: flujo completo por rol — login superadmin → crear admin → login admin → crear usuario creador → login creador → ve solo lo suyo → cambio de contraseña → logout; ruta protegida sin sesión redirige a login; usuario desactivado no puede entrar.
3. Todas las pruebas deben ejecutarse y PASAR antes de dar por terminada la fase; reportar la salida real.

### Fase 4 — DOCUMENTACIÓN
1. `doc/auth-arquitectura.md` — diseño final: esquema, matriz de permisos, flujos de token, decisiones y trade-offs.
2. `doc/auth-manual-usuario.md` — manual en español por rol (cómo iniciar sesión, cambiar contraseña, gestionar usuarios).
3. `.env.example` + sección de configuración en README/CLAUDE.md (variables, cómo levantar con auth, cómo resetear al superadmin si se pierde la contraseña).
4. Actualizar `RISKS.md` (#2 mitigado; nuevos riesgos residuales) y `CLAUDE.md` (regla "sin autenticación" ya no aplica; nuevas reglas críticas de auth).

---

## CRITERIOS DE ACEPTACIÓN

- [ ] Imposible acceder a cualquier dato del API sin token válido (verificado con pruebas).
- [ ] Un `creador` no puede ver/modificar/descargar NADA de otro creador (probado, incluido IDOR por ID).
- [ ] Solo superadmin gestiona admins; nadie elimina/degrada al superadmin.
- [ ] Login incorrecto no revela existencia de usuarios; fuerza bruta mitigada.
- [ ] Contraseñas hasheadas (argon2/bcrypt), jamás expuestas en respuestas ni logs.
- [ ] Refresh con rotación; logout invalida sesión del lado servidor.
- [ ] Frontend: rutas protegidas por rol, Sidebar dinámico, manejo global de 401, `/login`, `/perfil` y gestión de usuarios funcionando con el design system GO.
- [ ] Superadmin seed con cambio de contraseña forzado al primer login.
- [ ] Suite pytest + E2E Playwright en verde, con salida real reportada.
- [ ] Documentación de las 4 entregas de la Fase 4 completa y en español.
- [ ] `npx vite build` limpio y app funcionando end-to-end en `127.0.0.1:5173` + `127.0.0.1:8000`.

---

## FORMATO DE TRABAJO

- Idioma de trabajo y entregables: **español**.
- Empieza por la Fase 1 y **espera aprobación explícita** antes de la Fase 2.
- Si algún requerimiento es ambiguo, pregunta ANTES de diseñar en falso; enumera tus supuestos al inicio del diseño.
- Reporta al final de cada fase: qué se hizo, qué se probó (con evidencia), qué queda pendiente y los commits creados.
