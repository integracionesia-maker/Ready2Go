// @ts-check
import { test, expect } from "@playwright/test";

// Cubre el flujo de negocio del paquete R12: gastos generales (crear, listar,
// exportar a PDF, borrado lógico/físico) y borrado lógico/físico de tickets
// reflejado en Transacciones y Dashboard. Detalle de reglas en
// doc/gastos-generales-manual.md y doc/borrado-tickets.md.
//
// Nota: el backend limita a 30 logins/15min por IP (rate limiting, ver
// security.py) — correr este archivo junto con los demás .spec.js en una
// sola invocación puede acercarse al límite. Para una corrida limpia,
// ejecuta cada archivo por separado (ver doc/auth-manual-usuario.md §Pruebas).

const RUN_ID = Date.now();

const SUPERADMIN_USERNAME = "superadmin";
const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
// Contraseña a la que puede haber quedado el superadmin tras otro archivo de
// la suite en la misma invocación de Playwright (ver auth.spec.js).
const SUPERADMIN_KNOWN_ROTATED_PASSWORD = "SuperClaveE2ENueva123!";
const SUPERADMIN_GASTOS_PASSWORD = `SuperGastosE2E${RUN_ID}!`;

const ADMIN = {
  username: `admin.gastos.${RUN_ID}`,
  email: `admin.gastos.${RUN_ID}@test.com`,
  fullName: `Admin Gastos ${RUN_ID}`,
  password: "AdminGastosClave123!",
  newPassword: "AdminGastosClaveNueva123!",
};

const CREADOR = {
  username: `creador.gastos.${RUN_ID}`,
  email: `creador.gastos.${RUN_ID}@test.com`,
  fullName: `Persona Gastos ${RUN_ID}`,
  password: "CreadorGastosClave123!",
  newPassword: "CreadorGastosClaveNueva123!",
};

const CREATOR_NAME = `Creador Gastos ${RUN_ID}`;
const BRAND_NAME = `Marca Gastos ${RUN_ID}`;

const EXPENSE_DESC_A = `Suscripción software E2E ${RUN_ID}`;
const EXPENSE_DESC_B = `Servicio de hosting E2E ${RUN_ID}`;
const EXPENSE_AMOUNT_A = 350;
const EXPENSE_AMOUNT_B = 480;

async function login(page, identificador, password) {
  await page.goto("/login");
  await page.fill('input[autocomplete="username"]', identificador);
  await page.fill('input[autocomplete="current-password"]', password);
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes("/api/auth/login")),
    page.click('button[type="submit"]'),
  ]);
}

async function changePasswordOnForcedPerfil(page, currentPassword, newPassword) {
  await expect(page).toHaveURL(/\/perfil/);
  const pw = page.locator('input[type="password"]');
  await pw.nth(0).fill(currentPassword);
  await pw.nth(1).fill(newPassword);
  await pw.nth(2).fill(newPassword);
  await page.click('button:has-text("Actualizar contraseña")');
  await expect(page.getByText("Contraseña actualizada.")).toBeVisible();
}

async function logout(page) {
  await page.click('button[aria-haspopup="true"]');
  await page.click('button:has-text("Cerrar sesión")');
  await expect(page).toHaveURL(/\/login/);
}

/** Login resiliente de superadmin: ver la misma estrategia en
 * presupuesto-flujo-completo.spec.js (prueba la contraseña sembrada y la que
 * pudo haber quedado tras un cambio forzado de otro archivo de la suite). */
let superadminActivePassword = null;
async function loginSuperadmin(page) {
  if (superadminActivePassword) {
    await login(page, SUPERADMIN_USERNAME, superadminActivePassword);
    return;
  }
  const candidates = [SUPERADMIN_SEED_PASSWORD, SUPERADMIN_KNOWN_ROTATED_PASSWORD].filter(Boolean);
  let logged = false;
  for (const candidate of candidates) {
    await login(page, SUPERADMIN_USERNAME, candidate);
    const wrongCreds = await page
      .getByText("Usuario o contraseña incorrectos.")
      .isVisible()
      .catch(() => false);
    if (!wrongCreds) {
      superadminActivePassword = candidate;
      logged = true;
      break;
    }
  }
  if (!logged) {
    throw new Error("No se pudo iniciar sesión como superadmin con ninguna contraseña candidata.");
  }
  if (page.url().includes("/perfil")) {
    await changePasswordOnForcedPerfil(page, superadminActivePassword, SUPERADMIN_GASTOS_PASSWORD);
    superadminActivePassword = SUPERADMIN_GASTOS_PASSWORD;
  }
}

function fileBuffer(label) {
  return Buffer.from(`%PDF-1.4\n% comprobante de prueba E2E ${label}\n`);
}

/** Selecciona un <option> por texto parcial (el select de creador en
 * UploadTicketModal concatena el nombre con el restante del ciclo, así que
 * un match exacto por nombre no sirve). */
async function selectOptionByPartialText(select, partialText) {
  const value = await select.locator("option", { hasText: partialText }).first().getAttribute("value");
  await select.selectOption(value);
}

test.describe.serial("Gastos Generales y borrado de tickets (R12)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD para correr esta suite");

  test("bootstrap: superadmin crea admin, creador, un Creador y una Marca", async ({ page }) => {
    await loginSuperadmin(page);

    // Gestión de usuarios vive en /administracion-sistema (exclusiva de
    // superadmin); Creadores/Marcas siguen en /administracion.
    await page.goto("/administracion-sistema");
    await page.click('button:has-text("Nuevo Usuario")');
    let modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').nth(0).fill(ADMIN.username);
    await modal.locator('input[type="text"]').nth(1).fill(ADMIN.fullName);
    await modal.locator('input[type="email"]').fill(ADMIN.email);
    await modal.locator("select").first().selectOption("admin");
    await modal.locator('input[type="password"]').fill(ADMIN.password);
    await modal.locator('button:has-text("Crear")').click();
    await expect(page.getByRole("cell", { name: ADMIN.username, exact: true })).toBeVisible();

    await page.goto("/administracion");
    await page.click('button:has-text("Creadores")');
    await page.click('button:has-text("Nuevo Creador")');
    modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').fill(CREATOR_NAME);
    await modal.locator('input[type="number"]').fill("1000");
    await modal.locator("select").selectOption("mensual");
    await modal.locator('button:has-text("Crear")').click();
    await expect(page.locator("tr", { hasText: CREATOR_NAME })).toBeVisible();

    await page.click('button:has-text("Marcas")');
    await page.click('button:has-text("Nueva Marca")');
    modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').fill(BRAND_NAME);
    await modal.locator('button:has-text("Crear")').click();
    await expect(page.locator("tr", { hasText: BRAND_NAME })).toBeVisible();

    await page.goto("/administracion-sistema");
    await page.click('button:has-text("Nuevo Usuario")');
    modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').nth(0).fill(CREADOR.username);
    await modal.locator('input[type="text"]').nth(1).fill(CREADOR.fullName);
    await modal.locator('input[type="email"]').fill(CREADOR.email);
    await modal.locator("select").nth(1).selectOption({ label: CREATOR_NAME });
    await modal.locator('input[type="password"]').fill(CREADOR.password);
    await modal.locator('button:has-text("Crear")').click();
    await expect(page.getByRole("cell", { name: CREADOR.username, exact: true })).toBeVisible();

    await logout(page);
  });

  test("un creador no ve Gastos Generales en el menú y la ruta devuelve acceso no autorizado", async ({ page }) => {
    await login(page, CREADOR.username, CREADOR.password);
    await changePasswordOnForcedPerfil(page, CREADOR.password, CREADOR.newPassword);

    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).not.toContainText("Gastos Generales");

    await page.goto("/gastos-generales");
    await expect(page).toHaveURL(/\/403/);

    await logout(page);
  });

  test("admin crea un gasto general y aparece en la tabla", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await changePasswordOnForcedPerfil(page, ADMIN.password, ADMIN.newPassword);

    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).toContainText("Gastos Generales");
    await page.goto("/gastos-generales");
    await expect(page.getByRole("heading", { name: "Gastos Generales" })).toBeVisible();

    await page.click('button:has-text("Nuevo Gasto General")');
    const modal = page.locator(".fixed.inset-0");
    await expect(modal.getByText("Nuevo Gasto General")).toBeVisible();
    // La marca es obligatoria en gastos generales (models.GeneralExpense.brand_id
    // nullable=False + `required` en el select). Sin seleccionarla, la validación
    // nativa del navegador bloquea el submit y el modal nunca responde.
    await modal.locator("select").selectOption({ label: BRAND_NAME });
    await modal.locator("textarea").fill(EXPENSE_DESC_A);
    await modal.locator('input[type="number"]').fill(String(EXPENSE_AMOUNT_A));
    await modal.locator('input[type="file"]').setInputFiles({
      name: "comprobante-a.pdf",
      mimeType: "application/pdf",
      buffer: fileBuffer(`${RUN_ID}-a`),
    });
    await modal.locator('button:has-text("Registrar Gasto")').click();
    await expect(modal.getByText("Gasto general registrado exitosamente.")).toBeVisible();

    const row = page.locator("tr", { hasText: EXPENSE_DESC_A });
    await expect(row).toBeVisible();
    await expect(row).toContainText("$350.00");
  });

  test("el gasto general aparece en la gráfica y el KPI del Dashboard", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Gastos Generales por Mes")).toBeVisible();
    const kpiCard = page.locator(".go-card, [class*='go-card']", { hasText: "Gastos Generales" }).first();
    await expect(kpiCard).toContainText("$350.00");
  });

  test("admin exporta Gastos Generales a PDF", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);
    await page.goto("/gastos-generales");

    await page.click('button:has-text("Exportar")');
    const modal = page.locator(".fixed.inset-0");
    await expect(modal.getByText("Exportar Gastos Generales")).toBeVisible();

    // El mes actual es el primer checkbox (los últimos 12 meses, más reciente primero).
    await modal.locator('input[type="checkbox"]').first().check();

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 60_000 }),
      modal.locator('button:has-text("Generar PDF")').click(),
    ]);
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();

    const fs = await import("node:fs");
    const buffer = fs.readFileSync(downloadPath);
    expect(buffer.subarray(0, 5).toString("latin1")).toBe("%PDF-");
  });

  test("admin elimina lógicamente un gasto general y deja de aparecer", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);
    await page.goto("/gastos-generales");

    const row = page.locator("tr", { hasText: EXPENSE_DESC_A });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Eliminar" }).click();

    const confirmModal = page.locator(".fixed.inset-0");
    await expect(confirmModal.getByText("¿Eliminar")).toBeVisible();
    await confirmModal.getByRole("button", { name: "Eliminar", exact: true }).click();

    await expect(page.locator("tr", { hasText: EXPENSE_DESC_A })).toHaveCount(0);
  });

  test("admin elimina permanentemente un gasto general (con advertencia)", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);
    await page.goto("/gastos-generales");

    await page.click('button:has-text("Nuevo Gasto General")');
    let modal = page.locator(".fixed.inset-0");
    await modal.locator("select").selectOption({ label: BRAND_NAME });
    await modal.locator("textarea").fill(EXPENSE_DESC_B);
    await modal.locator('input[type="number"]').fill(String(EXPENSE_AMOUNT_B));
    await modal.locator('input[type="file"]').setInputFiles({
      name: "comprobante-b.pdf",
      mimeType: "application/pdf",
      buffer: fileBuffer(`${RUN_ID}-b`),
    });
    await modal.locator('button:has-text("Registrar Gasto")').click();
    await expect(modal.getByText("Gasto general registrado exitosamente.")).toBeVisible();

    const row = page.locator("tr", { hasText: EXPENSE_DESC_B });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Eliminar" }).click();

    const confirmModal = page.locator(".fixed.inset-0");
    await confirmModal.getByRole("button", { name: "Prefiero eliminarlo permanentemente" }).click();
    await expect(confirmModal.getByText("Esta acción es irreversible.")).toBeVisible();
    await confirmModal.getByRole("button", { name: "Eliminar permanentemente" }).click();

    await expect(page.locator("tr", { hasText: EXPENSE_DESC_B })).toHaveCount(0);
  });

  test("borrado lógico de un ticket aprobado lo quita de Transacciones y del Dashboard", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);

    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    const summaryCardBefore = page.locator(".go-card", { hasText: "Gastado en el Período" }).first();
    const textBefore = await summaryCardBefore.innerText();

    await page.goto("/transacciones");
    await page.click('button:has-text("Nuevo Ticket")');
    const uploadModal = page.locator(".fixed.inset-0");
    await selectOptionByPartialText(uploadModal.locator("select").nth(0), CREATOR_NAME);
    await uploadModal.locator("select").nth(1).selectOption({ label: BRAND_NAME });
    await uploadModal.locator('input[type="number"]').fill("125");
    await uploadModal.locator('input[type="file"]').setInputFiles({
      name: "ticket-soft-delete.pdf",
      mimeType: "application/pdf",
      buffer: fileBuffer(`${RUN_ID}-soft`),
    });
    await uploadModal.locator('button:has-text("Registrar Ticket")').click();
    await expect(uploadModal.getByText("Ticket registrado exitosamente.")).toBeVisible();

    await page.goto("/transacciones");
    const row = page.locator("tr", { hasText: BRAND_NAME }).first();
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Eliminar" }).click();

    const confirmModal = page.locator(".fixed.inset-0");
    await confirmModal.getByRole("button", { name: "Eliminar", exact: true }).click();
    await expect(page.locator("tr", { hasText: BRAND_NAME })).toHaveCount(0);

    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    const summaryCardAfter = page.locator(".go-card", { hasText: "Gastado en el Período" }).first();
    await expect(summaryCardAfter).not.toHaveText(textBefore);

    await logout(page);
  });

  test("borrado permanente de un ticket muestra advertencia roja antes de confirmar", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);

    await page.goto("/transacciones");
    await page.click('button:has-text("Nuevo Ticket")');
    const uploadModal = page.locator(".fixed.inset-0");
    await selectOptionByPartialText(uploadModal.locator("select").nth(0), CREATOR_NAME);
    await uploadModal.locator("select").nth(1).selectOption({ label: BRAND_NAME });
    await uploadModal.locator('input[type="number"]').fill("140");
    await uploadModal.locator('input[type="file"]').setInputFiles({
      name: "ticket-hard-delete.pdf",
      mimeType: "application/pdf",
      buffer: fileBuffer(`${RUN_ID}-hard`),
    });
    await uploadModal.locator('button:has-text("Registrar Ticket")').click();
    await expect(uploadModal.getByText("Ticket registrado exitosamente.")).toBeVisible();

    await page.goto("/transacciones");
    const row = page.locator("tr", { hasText: BRAND_NAME }).first();
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Eliminar" }).click();

    const confirmModal = page.locator(".fixed.inset-0");
    // Antes de la advertencia, el paso por defecto es el borrado lógico (recuperable).
    await expect(confirmModal.getByText("¿Eliminar")).toBeVisible();
    await confirmModal.getByRole("button", { name: "Prefiero eliminarlo permanentemente" }).click();
    await expect(confirmModal.getByText("Esta acción es irreversible.")).toBeVisible();

    await confirmModal.getByRole("button", { name: "Eliminar permanentemente" }).click();
    await expect(page.locator("tr", { hasText: BRAND_NAME })).toHaveCount(0);

    await logout(page);
  });
});
