# Plan de Implementación: Gastos Generales + Borrado de Tickets + Dashboard

> **Rama objetivo:** `dami-branch`
> **Fecha del plan:** 2026-07-22
> **Roles afectados:** `admin`, `superadmin` (creador no accede a gastos generales ni a borrado)
> **Agente ejecutor:** Agente de código especializado (este documento es la especificación)

---

## Arquitectura actual (punto de partida)

```
Modelos:
  Creator ──< Ticket >── Brand
  Creator ──< BudgetCycle
  Ticket ── BudgetCycle (nullable)
  Ticket ── User (reviewed_by)

Routers:
  /api/auth/*        → auth.py
  /api/users/*       → users.py
  /api/creators/*    → creators.py
  /api/brands/*      → brands.py
  /api/tickets/*     → tickets.py
  /api/dashboard/*   → dashboard.py

Frontend (rutas):
  /                  → HomePage
  /dashboard         → Dashboard (admin/superadmin)
  /creadores         → CreatorList (admin/superadmin)
  /transacciones     → TransactionTable
  /validacion        → ValidationQueue (admin/superadmin)
  /administracion    → AdminView (admin/superadmin)
  /perfil            → ProfilePage

Sidebar:
  Inicio · Dashboard · Creadores · Transacciones · Validación · Administración · Mi Perfil
```

---

# ETAPA 1: DISEÑO

## 1.1 — Feature: Gastos Generales (nuevo tipo de presupuesto independiente)

### Decisión arquitectónica: Tabla separada `general_expenses`

**¿Por qué tabla separada y no extender `tickets` con un `ticket_type`?**

| Criterio | Tabla separada | Columna `ticket_type` en `tickets` |
|---|---|---|
| Riesgo de contaminar presupuestos de creadores | Cero — queries independientes | Alto — hay que añadir filtro `ticket_type='creador'` en ~15 queries existentes |
| `creator_id` / `brand_id` NOT NULL actuales | No se tocan | Hay que volverlos nullable (migración compleja, riesgo en JOINs) |
| BudgetCycle | No aplica — los gastos generales no tienen ciclo | Habría que manejar `budget_cycle_id=NULL` en lógica existente |
| Reutilización de código | Se comparte `upload_manager.py`, patrón de modelo, convenciones de API | Máxima reutilización |
| Mantenibilidad a largo plazo | Separación clara de dominios | Un solo modelo con dos personalidades |

**Decisión: Tabla `general_expenses` independiente.** El costo de duplicar algunos patrones (CRUD, file upload) es menor que el riesgo de romper la lógica de presupuestos de creadores.

### Modelo de datos nuevo

```python
# backend/app/models.py — nueva clase

class GeneralExpense(Base):
    __tablename__ = "general_expenses"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    amount          = Column(Float, nullable=False)
    description     = Column(Text, nullable=False)        # descripción del gasto
    file_name       = Column(String(255), nullable=False)
    file_path       = Column(String(512), nullable=False)
    mime_type       = Column(String(100), nullable=False)
    upload_date     = Column(DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Soft delete
    is_deleted      = Column(Boolean, nullable=False, default=False)
    deleted_at      = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    deleted_by = relationship("User", foreign_keys=[deleted_by_user_id], lazy="selectin")
```

### Nuevos endpoints API

| Método | Ruta | Descripción | Rol requerido |
|---|---|---|---|
| `POST` | `/api/general-expenses/` | Crear gasto general (multipart form) | `admin`, `superadmin` |
| `GET` | `/api/general-expenses/` | Listar con filtros `?start_date=&end_date=` | `admin`, `superadmin` |
| `GET` | `/api/general-expenses/{id}/file` | Descargar comprobante | `admin`, `superadmin` |
| `POST` | `/api/general-expenses/{id}/soft-delete` | Borrado lógico | `admin`, `superadmin` |
| `DELETE` | `/api/general-expenses/{id}/permanent` | Borrado físico (con confirmación) | `admin`, `superadmin` |
| `GET` | `/api/dashboard/general-expenses-monthly` | Totales mensuales para gráfica | `admin`, `superadmin` |
| `GET` | `/api/general-expenses/export` | Datos para exportación, con query `?months=2026-07,2026-08` | `admin`, `superadmin` |

### Nuevo router

```
backend/app/routers/general_expenses.py  (archivo nuevo)
```

Registrar en `backend/app/main.py`:
```python
from .routers import general_expenses
app.include_router(general_expenses.router)
```

### Estructura del formulario de creación (request body)

`POST /api/general-expenses/` — multipart/form-data:
- `amount`: float (requerido, > 0)
- `description`: str (requerido, min 1, max 500)
- `file`: UploadFile (requerido, mismas validaciones que tickets: JPG/PNG/PDF, max 10MB)

### Esquemas Pydantic nuevos

```python
# schemas.py

class GeneralExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)

class GeneralExpenseResponse(BaseModel):
    id: int
    amount: float
    description: str
    file_name: str
    file_path: str
    mime_type: str
    upload_date: datetime
    created_by_user_id: Optional[int] = None
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class GeneralExpenseMonthlyItem(BaseModel):
    month: str        # "2026-07"
    total: float
    count: int

class GeneralExpensesExportResponse(BaseModel):
    months: List[str]                     # meses incluidos
    items: List[GeneralExpenseResponse]   # gastos del período
    total: float                          # suma total
```

### Dashboard — Nueva gráfica

Nueva sección en el Dashboard debajo de "Tendencia de Gasto Acumulado":

```
┌──────────────────────────────────────────────┐
│  GASTOS GENERALES POR MES                    │
│  (gráfica de barras, mismo estilo que        │
│   MonthlySpendChart pero con datos de        │
│   general_expenses)                          │
│                                    MXN       │
└──────────────────────────────────────────────┘
```

**Componente nuevo:** `frontend/src/components/charts/GeneralExpensesChart.jsx`

Usa el mismo tema ApexCharts de `apexTheme.js`. Es una gráfica de barras simple: eje X = mes (`"2026-07"`), eje Y = total del mes.

### Nuevo KPI Card en Dashboard

Agregar un KPI card en la fila 2 del dashboard (la de "Gastado en el Período", "Tickets", "Creadores Activos") — se convierte en una grid de 4 columnas:

```
Gastado en el Período | Tickets | Creadores Activos | Gastos Generales
```

O alternativamente, una nueva fila de 1 columna full-width con un KPI específico.

### Exportación independiente

La exportación de gastos generales NO usa el PDF del dashboard de creadores. Es un botón separado que:

1. Abre un modal con checkboxes de meses (últimos 12 meses hacia atrás desde hoy)
2. El usuario selecciona cuáles meses exportar
3. Genera un PDF simple con:
   - Título: "Reporte de Gastos Generales"
   - Período seleccionado
   - Tabla: Fecha | Descripción | Monto | Comprobante (link)
   - Total general
   - Pie de página con fecha de generación y usuario

**Componentes nuevos:**
- `frontend/src/components/GeneralExpensesExportModal.jsx`
- `frontend/src/components/PdfReport/GeneralExpensesPdfTemplate.jsx`
- `frontend/src/components/PdfReport/generateGeneralExpensesPdf.js`

### Sidebar — Nueva entrada

Agregar item "Gastos Generales" en `Sidebar.jsx` después de "Validación", con ícono de billete/documento:

```javascript
{
  to: "/gastos-generales",
  label: "Gastos Generales",
  icon: "M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z",
  roles: ["admin", "superadmin"],
}
```

### Nueva ruta en App.jsx

```jsx
<Route
  path="/gastos-generales"
  element={
    <ProtectedRoute roles={ADMIN_ROLES}>
      <GeneralExpensesPage />
    </ProtectedRoute>
  }
/>
```

### Nueva página

`frontend/src/pages/GeneralExpensesPage.jsx` — tabla con historial de gastos generales + botón "Nuevo Gasto General" + botón "Exportar".

### Nuevo modal de creación

`frontend/src/components/GeneralExpenseModal.jsx` — similar a `UploadTicketModal` pero simplificado:
- Sin selector de creador
- Sin selector de marca
- Campo: descripción (textarea)
- Campo: monto
- Campo: archivo/comprobante
- Sin advertencia de ciclo/presupuesto

### Flujo completo

```
Sidebar "Gastos Generales"
  → GeneralExpensesPage
    → Tabla histórica (filtrable por mes)
    → Botón "Nuevo Gasto General" → GeneralExpenseModal
    → Botón "Exportar" → GeneralExpensesExportModal → PDF
    → Botón "Eliminar" en cada fila → Confirmación → soft delete
    → Dashboard: nueva gráfica + KPI
```

---

## 1.2 — Feature: Borrado lógico y físico de tickets

### Modelo de datos — Columnas nuevas en `Ticket`

```python
# Agregar a la clase Ticket existente:

is_deleted         = Column(Boolean, nullable=False, default=False)
deleted_at         = Column(DateTime, nullable=True)
deleted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

deleted_by = relationship("User", foreign_keys=[deleted_by_user_id], lazy="selectin")
```

### Migración de base de datos

Crear script `backend/migrate_add_soft_delete.py` que:
1. Agregue columnas `is_deleted`, `deleted_at`, `deleted_by_user_id` a la tabla `tickets`
2. Establezca `is_deleted = FALSE` para todos los registros existentes
3. Cree la misma estructura en `general_expenses` (si la tabla ya existe)

Ejecutar **una sola vez** antes de arrancar el backend con los cambios.

### Nuevas funciones CRUD

```python
# backend/app/crud.py

def soft_delete_ticket(db: Session, ticket: models.Ticket, actor_user_id: int) -> models.Ticket:
    """Marca un ticket como eliminado lógicamente. No borra el archivo del disco."""
    ticket.is_deleted = True
    ticket.deleted_at = datetime.now(timezone.utc)
    ticket.deleted_by_user_id = actor_user_id
    db.commit()
    db.refresh(ticket)
    return ticket

def hard_delete_ticket(db: Session, ticket: models.Ticket) -> None:
    """Borra el registro de la BD y el archivo del disco."""
    file_path = ticket.file_path
    db.delete(ticket)
    db.commit()
    delete_upload(file_path)  # import de upload_manager

def soft_delete_general_expense(db, expense, actor_user_id):  # análogo
def hard_delete_general_expense(db, expense):                   # análogo
```

### Filtro global en queries existentes

**TODAS las queries que leen de `tickets` deben excluir `is_deleted = True`:**

| Archivo | Función | Cambio |
|---|---|---|
| `crud.py` | `get_tickets()` | Agregar `.filter(models.Ticket.is_deleted == False)` |
| `crud.py` | `get_brand_spend_breakdown()` | Agregar filtro `is_deleted == False` en las condiciones del JOIN |
| `crud.py` | `get_monthly_spend()` | Agregar `.filter(models.Ticket.is_deleted == False)` |
| `crud.py` | `get_creator_usage()` | Agregar `.filter(models.Ticket.is_deleted == False)` en la subquery `ticket_spent` |
| `crud.py` | `get_dashboard_summary()` | Agregar `.filter(models.Ticket.is_deleted == False)` en ambas queries |
| `crud.py` | `approve_ticket()` | (No aplica — un ticket deleted no debería ser aprobable; agregar validación) |
| `crud.py` | `reject_ticket()` | (Ídem) |
| `tickets.py` | `list_tickets()` | Ya se beneficia del filtro en `crud.get_tickets()` |
| `tickets.py` | `download_file()` | Agregar validación de `is_deleted` antes de permitir descarga |
| `tickets.py` | `aprobar_ticket()` | Agregar validación: `if ticket.is_deleted: raise 404` |
| `tickets.py` | `rechazar_ticket()` | Agregar validación: `if ticket.is_deleted: raise 404` |

### Nuevos endpoints — Tickets

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/tickets/{id}/soft-delete` | Borrado lógico |
| `DELETE` | `/api/tickets/{id}/permanent` | Borrado físico |

**`POST /api/tickets/{id}/soft-delete`:**
- Solo `admin`, `superadmin`
- Si el ticket estaba aprobado, **revertir el descuento** del ciclo (`cycle.spent -= ticket.amount`)
- Marcar `is_deleted = True`, `deleted_at = now`, `deleted_by_user_id = current_user.id`
- Audit log: `ticket.soft-delete`

**`DELETE /api/tickets/{id}/permanent`:**
- Solo `admin`, `superadmin`
- Si el ticket estaba aprobado Y no estaba ya soft-deleted, revertir descuento del ciclo
- Borrar archivo del disco (`delete_upload(ticket.file_path)`)
- Borrar registro de la BD
- Audit log: `ticket.hard-delete`
- ⚠️ El frontend DEBE mostrar advertencia y pedir confirmación explícita antes de llamar este endpoint

### Reversión de descuento en borrado

Cuando se hace soft/hard delete de un ticket con `status = 'aprobado'`:
1. Recuperar el `budget_cycle` asociado
2. `cycle.spent = max(0, cycle.spent - ticket.amount)` (nunca negativo por seguridad)
3. El ticket deja de contar para TODOS los cálculos

**Importante:** Si un ticket `pendiente` o `rechazado` se borra, NO hay que revertir nada (nunca descontó).

### Nuevos endpoints — General Expenses (borrado)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/general-expenses/{id}/soft-delete` | Borrado lógico |
| `DELETE` | `/api/general-expenses/{id}/permanent` | Borrado físico |

Misma lógica que tickets pero sin interacción con ciclos de presupuesto.

---

## 1.3 — Feature: Nueva gráfica en Dashboard para Gastos Generales

### Datos

El endpoint `GET /api/dashboard/general-expenses-monthly?start_date=&end_date=` devuelve:

```json
[
  { "month": "2026-07", "total": 15200.00, "count": 3 },
  { "month": "2026-08", "total": 8900.00, "count": 2 }
]
```

Respetando el filtro de fechas del dashboard y excluyendo registros `is_deleted = True`.

### Componente chart

`GeneralExpensesChart.jsx`:
- Gráfica de barras con ApexCharts
- Mismo `apexTheme.js` y `createApexOptions`
- Colores: usar naranja GO (`#FB670B`) como color principal
- Tooltip: "Mes: $X,XXX.XX | N tickets"

### KPI card

Nuevo KPI en la segunda fila del dashboard:
- Título: "Gastos Generales"
- Valor: suma total del período
- Subtítulo: "N gastos en el período"
- Accent: "orange"

### Inclusión en PDF

Modificar `DashboardPdfTemplate.jsx` para incluir una nueva sección con la gráfica de gastos generales y una tabla resumen.

---

# ETAPA 2: IMPLEMENTACIÓN

## Orden de ejecución recomendado

### Fase 2.1 — Base de datos y modelos (backbone)

| Paso | Archivo | Acción |
|---|---|---|
| 2.1.1 | `backend/app/models.py` | Agregar clase `GeneralExpense` |
| 2.1.2 | `backend/app/models.py` | Agregar columnas `is_deleted`, `deleted_at`, `deleted_by_user_id` a `Ticket` |
| 2.1.3 | `backend/app/schemas.py` | Agregar `GeneralExpenseCreate`, `GeneralExpenseResponse`, `GeneralExpenseMonthlyItem`, `GeneralExpensesExportResponse` |
| 2.1.4 | `backend/migrate_add_soft_delete.py` | Crear script de migración (ejecutar una vez) |
| 2.1.5 | Ejecutar migración | `python migrate_add_soft_delete.py` |

### Fase 2.2 — CRUD y lógica de negocio (backend)

| Paso | Archivo | Acción |
|---|---|---|
| 2.2.1 | `backend/app/crud.py` | Agregar `soft_delete_ticket()`, `hard_delete_ticket()` |
| 2.2.2 | `backend/app/crud.py` | Agregar `get_general_expenses()`, `create_general_expense()`, `soft_delete_general_expense()`, `hard_delete_general_expense()`, `get_general_expenses_monthly()` |
| 2.2.3 | `backend/app/crud.py` | Modificar TODAS las queries de tickets: agregar filtro `is_deleted == False` |
| 2.2.4 | `backend/app/crud.py` | Agregar `get_general_expenses_for_export()` con filtro por lista de meses |

### Fase 2.3 — Endpoints API (backend)

| Paso | Archivo | Acción |
|---|---|---|
| 2.3.1 | `backend/app/routers/tickets.py` | Agregar endpoints `soft-delete` y `permanent` delete |
| 2.3.2 | `backend/app/routers/tickets.py` | Agregar validación `is_deleted` en aprobar, rechazar, download |
| 2.3.3 | `backend/app/routers/general_expenses.py` | **Crear archivo nuevo** con todos los endpoints de gastos generales |
| 2.3.4 | `backend/app/routers/dashboard.py` | Agregar endpoint `general-expenses-monthly` |
| 2.3.5 | `backend/app/main.py` | Registrar router `general_expenses` |

### Fase 2.4 — Frontend: API layer

| Paso | Archivo | Acción |
|---|---|---|
| 2.4.1 | `frontend/src/api/index.js` | Agregar funciones: `softDeleteTicket()`, `hardDeleteTicket()` |
| 2.4.2 | `frontend/src/api/index.js` | Agregar funciones: `createGeneralExpense()`, `fetchGeneralExpenses()`, `softDeleteGeneralExpense()`, `hardDeleteGeneralExpense()`, `fetchGeneralExpensesMonthly()`, `fetchGeneralExpensesExport()` |

### Fase 2.5 — Frontend: Componentes de Gastos Generales

| Paso | Archivo | Acción |
|---|---|---|
| 2.5.1 | `frontend/src/components/GeneralExpenseModal.jsx` | Modal para crear nuevo gasto general (admin) |
| 2.5.2 | `frontend/src/pages/GeneralExpensesPage.jsx` | Página con tabla histórica + botones de acción |
| 2.5.3 | `frontend/src/components/GeneralExpensesExportModal.jsx` | Modal con selector de meses para exportación |
| 2.5.4 | `frontend/src/components/PdfReport/GeneralExpensesPdfTemplate.jsx` | Plantilla HTML off-screen para el PDF |
| 2.5.5 | `frontend/src/components/PdfReport/generateGeneralExpensesPdf.js` | Lógica de generación del PDF (html2canvas + jsPDF) |
| 2.5.6 | `frontend/src/components/Sidebar.jsx` | Agregar entrada "Gastos Generales" |
| 2.5.7 | `frontend/src/App.jsx` | Agregar ruta `/gastos-generales` |

### Fase 2.6 — Frontend: Borrado en componentes existentes

| Paso | Archivo | Acción |
|---|---|---|
| 2.6.1 | `frontend/src/components/TransactionTable.jsx` | Agregar botón "Eliminar" (solo admin) en cada fila de ticket |
| 2.6.2 | `frontend/src/components/TransactionTable.jsx` | Modal de confirmación para soft delete |
| 2.6.3 | `frontend/src/components/TransactionTable.jsx` | Modal de advertencia + confirmación para hard delete (con texto rojo de advertencia) |
| 2.6.4 | `frontend/src/components/ValidationQueue.jsx` | Agregar botón "Eliminar" (misma lógica) |
| 2.6.5 | `frontend/src/components/GeneralExpensesPage.jsx` | Agregar botones de soft/hard delete en la tabla de gastos generales |

### Fase 2.7 — Frontend: Dashboard

| Paso | Archivo | Acción |
|---|---|---|
| 2.7.1 | `frontend/src/components/charts/GeneralExpensesChart.jsx` | Nueva gráfica de barras mensual |
| 2.7.2 | `frontend/src/components/Dashboard.jsx` | Cargar datos de `fetchGeneralExpensesMonthly()`, pasar a la gráfica |
| 2.7.3 | `frontend/src/components/Dashboard.jsx` | Agregar KPI card "Gastos Generales" |
| 2.7.4 | `frontend/src/components/Dashboard.jsx` | Agregar sección con `GeneralExpensesChart` |
| 2.7.5 | `frontend/src/components/PdfReport/DashboardPdfTemplate.jsx` | Agregar sección de gastos generales al PDF |

### Fase 2.8 — Integración y ajustes

| Paso | Archivo | Acción |
|---|---|---|
| 2.8.1 | `frontend/src/pages/HomePage.jsx` | Agregar tarjeta "Gastos Generales" en `AdminHome` (secciones navegables) |
| 2.8.2 | `frontend/src/components/UploadTicketModal.jsx` | Sin cambios (los gastos generales usan su propio modal) |
| 2.8.3 | Revisar que `loadData()` en `App.jsx` no necesite cambios | Solo si se quiere precargar datos de gastos generales |

---

# ETAPA 3: TESTEOS

## 3.1 — Backend: Tests unitarios/integración

### Archivo: `backend/tests/test_general_expenses.py` (nuevo)

| Test ID | Descripción | Tipo |
|---|---|---|
| `test_create_general_expense_as_admin` | Admin crea gasto general → 201, datos correctos en BD | Integración |
| `test_create_general_expense_as_creator` | Creador intenta crear → 403 | Seguridad |
| `test_create_general_expense_unauthenticated` | Sin sesión → 401 | Seguridad |
| `test_list_general_expenses` | GET retorna lista, respeta filtros de fecha | Integración |
| `test_list_general_expenses_excludes_deleted` | GET no incluye registros con `is_deleted=True` | Lógica |
| `test_soft_delete_general_expense` | Soft delete → `is_deleted=True`, `deleted_at` no nulo | Integración |
| `test_hard_delete_general_expense` | Hard delete → registro y archivo eliminados | Integración |
| `test_soft_delete_as_creator_forbidden` | Creador intenta borrar → 403 | Seguridad |
| `test_monthly_endpoint` | `general-expenses-monthly` agrupa correctamente por mes | Integración |
| `test_monthly_excludes_deleted` | Endpoint mensual no cuenta soft-deleted | Lógica |
| `test_export_endpoint` | Export filtra por meses específicos y suma correctamente | Integración |
| `test_export_excludes_deleted` | Export no incluye registros eliminados | Lógica |

### Archivo: `backend/tests/test_ticket_soft_delete.py` (nuevo)

| Test ID | Descripción |
|---|---|
| `test_soft_delete_approved_ticket_reverts_cycle` | Ticket aprobado → soft delete → `cycle.spent` disminuye |
| `test_soft_delete_pending_ticket_no_cycle_change` | Ticket pendiente → soft delete → `cycle.spent` no cambia |
| `test_hard_delete_removes_file` | Hard delete → archivo físico ya no existe en disco |
| `test_hard_delete_reverts_cycle_if_approved` | Ticket aprobado → hard delete → `cycle.spent` disminuye |
| `test_deleted_ticket_not_in_list` | `get_tickets()` no retorna soft-deleted |
| `test_deleted_ticket_not_in_dashboard` | Summary, monthly, creator-usage excluyen soft-deleted |
| `test_deleted_ticket_not_in_brand_spend` | Brand spend breakdown excluye soft-deleted |
| `test_approve_deleted_ticket_fails` | Aprobar ticket soft-deleted → 404 |
| `test_reject_deleted_ticket_fails` | Rechazar ticket soft-deleted → 404 |
| `test_soft_delete_as_creator_forbidden` | Creador no puede borrar → 403 |
| `test_hard_delete_as_creator_forbidden` | Creador no puede borrar físicamente → 403 |

### Archivos existentes a extender

| Archivo | Acción |
|---|---|
| `backend/tests/test_budget_cycles.py` | Agregar test: ticket soft-deleted aprobado revierte descuento del ciclo |
| `backend/tests/test_ticket_validation.py` | Agregar test: ticket soft-deleted no aparece en cola de validación |
| `backend/tests/test_permissions.py` | Agregar tests de permisos para nuevos endpoints |

### Configuración de tests

Los tests existentes usan una BD de prueba (`conftest.py` con fixture `db`). Los fixtures ya hacen rollback. Para los tests de archivos, usar `tmp_path` de pytest.

---

## 3.2 — Frontend: Tests E2E

### Archivo: `frontend/e2e/gastos-generales.spec.js` (nuevo)

Casos Playwright:

| Test ID | Descripción |
|---|---|
| `admin_can_create_general_expense` | Login admin → navegar a Gastos Generales → abrir modal → llenar campos → submit → aparece en tabla |
| `creator_cannot_see_general_expenses` | Login creador → sidebar no muestra "Gastos Generales" → ruta `/gastos-generales` redirige a 403 |
| `admin_can_soft_delete_general_expense` | Click eliminar → confirmar → item desaparece de tabla (soft delete) |
| `admin_can_hard_delete_general_expense` | Click eliminar permanente → advertencia → confirmar → item desaparece |
| `admin_can_export_general_expenses` | Abrir modal exportar → seleccionar meses → generar PDF → archivo se descarga |
| `soft_deleted_ticket_not_in_dashboard` | Soft delete de ticket aprobado → dashboard refleja números actualizados |
| `soft_deleted_ticket_not_in_transactions` | Soft delete → TransactionTable ya no lo muestra |
| `hard_delete_shows_warning` | Click eliminar permanente → modal muestra advertencia roja antes de confirmar |

---

## 3.3 — Verificaciones manuales recomendadas

1. **Regresión de presupuestos de creadores**: Crear y aprobar un ticket de creador normal → verificar que el ciclo descuenta correctamente (sin interferencia de gastos generales).
2. **Dashboard sin datos**: Abrir dashboard sin gastos generales → la nueva gráfica muestra "Sin datos" o está vacía, no crashea.
3. **PDF de dashboard incluye gastos generales**: Descargar PDF del dashboard → verificar que la sección de gastos generales aparece.
4. **Theme claro/oscuro**: Cambiar tema → verificar que todos los nuevos componentes respetan las variables CSS.
5. **Responsive**: Verificar en vista móvil que la tabla de gastos generales y los modales se adaptan correctamente.

---

# ETAPA 4: DOCUMENTACIÓN

## 4.1 — Archivos a crear

| Archivo | Contenido |
|---|---|
| `doc/gastos-generales-manual.md` | Manual de uso para administradores: cómo crear, listar, exportar y eliminar gastos generales |
| `doc/borrado-tickets.md` | Documentación técnica del sistema de borrado lógico/físico: reglas de negocio, reversión de ciclos, permisos |

## 4.2 — Archivos a actualizar

| Archivo | Cambio |
|---|---|
| `doc/auth-manual-usuario.md` | Agregar sección §Gastos Generales y §Borrado de Tickets en el manual de admin |
| `doc/auth-arquitectura.md` | Agregar filas en la matriz de permisos para los nuevos endpoints |
| `doc/presupuestos-y-validacion.md` | Agregar sección sobre gastos generales (independientes de ciclos de creadores) |
| `CLAUDE.md` | Agregar en "Reglas criticas": tickets soft-deleted no cuentan para ningún cálculo; gastos generales son independientes de ciclos |

## 4.3 — Contenido mínimo del manual de gastos generales

```markdown
# Gastos Generales — Manual de Administrador

## ¿Qué son?
Gastos operativos NO vinculados a creadores o marcas (apps, servicios, etc.).

## Crear un gasto general
1. Sidebar → "Gastos Generales"
2. Botón "Nuevo Gasto General"
3. Completar: descripción, monto, comprobante
4. El gasto se registra de inmediato

## Exportar
1. Botón "Exportar" en la página de Gastos Generales
2. Seleccionar los meses deseados
3. Se genera un PDF con el detalle

## Eliminar
- "Eliminar" (borrado lógico): el gasto deja de contar pero se conserva
- "Eliminar permanentemente" (borrado físico): ⚠️ irreversible, archivo y registro desaparecen
```

## 4.4 — Contenido mínimo de la doc de borrado

```markdown
# Sistema de Borrado de Tickets

## Borrado lógico (soft delete)
- El ticket se marca como `is_deleted = True`
- Ya NO aparece en listados, dashboard, ni cálculos
- Si estaba aprobado, el monto se REVIERTE del ciclo
- El archivo comprobante se conserva en disco
- El registro permanece en BD (auditable)

## Borrado físico (hard delete)
- El ticket se ELIMINA de la base de datos
- El archivo comprobante se BORRA del disco
- Si estaba aprobado, el monto se REVIERTE del ciclo
- ⚠️ IRREVERSIBLE — requiere confirmación explícita

## Permisos
- Solo admin y superadmin pueden borrar tickets
- El creador no tiene acceso a ninguna forma de borrado

## Impacto en ciclos
| Estado del ticket | Soft delete | Hard delete |
|---|---|---|
| Pendiente | No revierte (nunca descontó) | No revierte |
| Aprobado | Revierte descuento del ciclo | Revierte descuento del ciclo |
| Rechazado | No revierte (nunca descontó) | No revierte |
```

---

# Resumen de archivos modificados/creados

## Backend (13 archivos)

| Archivo | Acción |
|---|---|
| `backend/app/models.py` | Modificar (agregar `GeneralExpense` + columnas soft-delete en `Ticket`) |
| `backend/app/schemas.py` | Modificar (nuevos esquemas) |
| `backend/app/crud.py` | Modificar (nuevas funciones + filtros `is_deleted` en queries existentes) |
| `backend/app/routers/tickets.py` | Modificar (endpoints de borrado + validaciones) |
| `backend/app/routers/general_expenses.py` | **Crear** |
| `backend/app/routers/dashboard.py` | Modificar (nuevo endpoint) |
| `backend/app/main.py` | Modificar (registrar router) |
| `backend/app/upload_manager.py` | Sin cambios (se reutiliza tal cual) |
| `backend/migrate_add_soft_delete.py` | **Crear** |
| `backend/tests/test_general_expenses.py` | **Crear** |
| `backend/tests/test_ticket_soft_delete.py` | **Crear** |
| `backend/tests/test_budget_cycles.py` | Modificar (test de reversión) |
| `backend/tests/test_permissions.py` | Modificar (tests de permisos nuevos) |

## Frontend (16 archivos)

| Archivo | Acción |
|---|---|
| `frontend/src/api/index.js` | Modificar (nuevas funciones API) |
| `frontend/src/App.jsx` | Modificar (nueva ruta) |
| `frontend/src/components/Sidebar.jsx` | Modificar (nueva entrada) |
| `frontend/src/pages/HomePage.jsx` | Modificar (nueva tarjeta en AdminHome) |
| `frontend/src/pages/GeneralExpensesPage.jsx` | **Crear** |
| `frontend/src/components/GeneralExpenseModal.jsx` | **Crear** |
| `frontend/src/components/GeneralExpensesExportModal.jsx` | **Crear** |
| `frontend/src/components/Dashboard.jsx` | Modificar (nueva gráfica + KPI) |
| `frontend/src/components/TransactionTable.jsx` | Modificar (botones de borrado) |
| `frontend/src/components/ValidationQueue.jsx` | Modificar (botones de borrado) |
| `frontend/src/components/charts/GeneralExpensesChart.jsx` | **Crear** |
| `frontend/src/components/PdfReport/GeneralExpensesPdfTemplate.jsx` | **Crear** |
| `frontend/src/components/PdfReport/generateGeneralExpensesPdf.js` | **Crear** |
| `frontend/src/components/PdfReport/DashboardPdfTemplate.jsx` | Modificar (sección gastos generales) |
| `frontend/e2e/gastos-generales.spec.js` | **Crear** |

## Documentación (6 archivos)

| Archivo | Acción |
|---|---|
| `doc/gastos-generales-manual.md` | **Crear** |
| `doc/borrado-tickets.md` | **Crear** |
| `doc/auth-manual-usuario.md` | Modificar |
| `doc/auth-arquitectura.md` | Modificar |
| `doc/presupuestos-y-validacion.md` | Modificar |
| `CLAUDE.md` | Modificar |

---

# Notas para el agente implementador

1. **Nunca commitear sin que el usuario lo pida explícitamente** (regla del proyecto).
2. **Trabajar siempre en `dami-branch`**.
3. **Correr `python -m pytest` desde `backend/` después de cada fase** para asegurar que no hay regresiones (119 tests base deben seguir pasando).
4. **Ejecutar la migración `migrate_add_soft_delete.py` UNA sola vez** antes de probar los cambios.
5. **Respetar las reglas de ApexCharts** de `CLAUDE.md`: nunca asignar `stroke`/`fill`/`plotOptions`/`responsive` como `undefined` explícito.
6. **No agregar imports estáticos de `jspdf`/`html2canvas`** — usar `import()` dinámico como en `generateDashboardPdf.js`.
7. **El endpoint de hard delete usa `DELETE` HTTP** — asegurar que el frontend envía el método correcto (fetch con `method: "DELETE"`).
8. **La reversión de ciclo en soft/hard delete usa `max(0, cycle.spent - amount)`** por seguridad — nunca deja `spent` negativo.
9. **El filtro `is_deleted == False` DEBE agregarse en TODAS las queries sin excepción** — si se olvida una, ese endpoint filtrará tickets borrados.
10. **Los gastos generales no tienen `status`** (no pasan por validación) — se crean y quedan registrados inmediatamente, solo los administradores pueden crearlos.
