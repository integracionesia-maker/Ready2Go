// @ts-check
import { test, expect } from "@playwright/test";

// Cubre el flujo de negocio completo introducido por el paquete R1-R11:
// ciclos de presupuesto, validación de tickets, prioridad de marcas, visor
// de comprobantes, header/popover, tema claro/oscuro, PDF y responsividad.
//
// Nota: el backend limita a 30 logins/15min por IP (rate limiting, ver
// security.py) — correr este archivo junto con auth.spec.js en una sola
// invocación puede acercarse al límite. Para una corrida limpia, ejecuta
// cada archivo por separado (ver comentario en auth.spec.js).
//
// Sufijo único para no colisionar con datos de una corrida anterior.
const RUN_ID = Date.now();

const SUPERADMIN_USERNAME = "superadmin";
const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
// Contraseña a la que cae el superadmin tras el cambio forzado en auth.spec.js,
// por si esta suite corre después de esa en la misma invocación de Playwright.
const SUPERADMIN_KNOWN_ROTATED_PASSWORD = "SuperClaveE2ENueva123!";
const SUPERADMIN_FLUJO_PASSWORD = `SuperFlujoE2E${RUN_ID}!`;

const ADMIN = {
  username: `admin.flujo.${RUN_ID}`,
  email: `admin.flujo.${RUN_ID}@test.com`,
  fullName: `Admin Flujo ${RUN_ID}`,
  password: "AdminFlujoClave123!",
  newPassword: "AdminFlujoClaveNueva123!",
};

const CREADOR = {
  username: `creador.flujo.${RUN_ID}`,
  email: `creador.flujo.${RUN_ID}@test.com`,
  fullName: `Persona Flujo ${RUN_ID}`,
  password: "CreadorFlujoClave123!",
  newPassword: "CreadorFlujoClaveNueva123!",
};

const CREATOR_NAME = `Creador Flujo ${RUN_ID}`;
const BRAND_NAME = `Marca Flujo ${RUN_ID}`;
const TICKET_AMOUNT = 500; // < 2000 (monto del ciclo semanal), no fuerza negativo
const REJECTION_REASON = `Comprobante ilegible E2E ${RUN_ID}`;

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

/** Login resiliente de superadmin: prueba la contraseña sembrada y la que
 * pudo haber quedado tras un cambio forzado de una corrida anterior de la
 * suite (auth.spec.js u otra ejecución de este mismo archivo), y completa el
 * cambio forzado si hace falta. Cachea la contraseña vigente en el módulo. */
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
    await changePasswordOnForcedPerfil(page, superadminActivePassword, SUPERADMIN_FLUJO_PASSWORD);
    superadminActivePassword = SUPERADMIN_FLUJO_PASSWORD;
  }
}

function ticketFileBuffer() {
  return Buffer.from(`%PDF-1.4\n% comprobante de prueba E2E ${RUN_ID}\n`);
}

test.describe.serial("Flujo completo de negocio (R1-R11)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD para correr esta suite");

  test("bootstrap: superadmin crea admin, creador con ciclo semanal y marca de prioridad alta", async ({ page }) => {
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
    await modal.locator('input[type="number"]').fill("2000");
    await modal.locator("select").selectOption("semanal");
    await modal.locator('button:has-text("Crear")').click();
    const creatorRow = page.locator("tr", { hasText: CREATOR_NAME });
    await expect(creatorRow).toBeVisible();
    await expect(creatorRow).toContainText("Semanal");
    await expect(creatorRow).toContainText("$2,000.00");

    await page.click('button:has-text("Marcas")');
    await page.click('button:has-text("Nueva Marca")');
    modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').fill(BRAND_NAME);
    await modal.locator("select").selectOption("alta");
    await modal.locator('button:has-text("Crear")').click();
    const brandRow = page.locator("tr", { hasText: BRAND_NAME });
    await expect(brandRow).toBeVisible();
    await expect(brandRow).toContainText("Alta");

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

  test("creador sube un ticket que nace pendiente y NO descuenta presupuesto", async ({ page }) => {
    await login(page, CREADOR.username, CREADOR.password);
    await changePasswordOnForcedPerfil(page, CREADOR.password, CREADOR.newPassword);

    await page.click('button:has-text("Nuevo Ticket")');
    const modal = page.locator(".fixed.inset-0");
    await expect(modal.getByText("Registrar Nuevo Ticket")).toBeVisible();
    await modal.locator("select").nth(1).selectOption({ label: BRAND_NAME });
    await modal.locator('input[type="number"]').fill(String(TICKET_AMOUNT));
    await expect(modal.getByText("pendiente de validación")).toBeVisible();
    await modal.locator('input[type="file"]').setInputFiles({
      name: "comprobante.pdf",
      mimeType: "application/pdf",
      buffer: ticketFileBuffer(),
    });
    await modal.locator('button:has-text("Registrar Ticket")').click();
    await expect(modal.getByText("Ticket registrado exitosamente.")).toBeVisible();

    await page.goto("/perfil");
    await expect(page.getByText("Mi ciclo de presupuesto")).toBeVisible();
    await expect(page.getByText("$0.00")).toBeVisible(); // gastado sigue en 0: el ticket está pendiente
    await expect(page.getByText("$2,000.00").first()).toBeVisible(); // restante sin cambios

    await logout(page);
  });

  test("admin ve el ticket pendiente en Validación, lo abre en el visor y lo rechaza con motivo", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await changePasswordOnForcedPerfil(page, ADMIN.password, ADMIN.newPassword);

    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).toContainText("Validación");
    await page.goto("/validacion");

    const row = page.locator("tr", { hasText: CREATOR_NAME });
    await expect(row).toBeVisible();
    await expect(row).toContainText(BRAND_NAME);
    await expect(row).toContainText("Alta"); // prioridad de la marca visible en la bandeja
    await expect(row).toContainText("$500.00");

    await row.getByRole("button", { name: "Ver" }).click();
    await expect(page.getByText(/^Comprobante —/)).toBeVisible();
    await page.getByRole("button", { name: "Cerrar" }).click();
    await expect(page.getByText(/^Comprobante —/)).toBeHidden();

    await row.getByRole("button", { name: "Rechazar" }).click();
    const rejectModal = page.locator(".fixed.inset-0");
    await rejectModal.locator("textarea").fill(REJECTION_REASON);
    await rejectModal.locator('button:has-text("Rechazar")').click();
    await expect(page.locator("tr", { hasText: CREATOR_NAME })).toHaveCount(0);

    await logout(page);
  });

  test("creador ve el motivo de rechazo y vuelve a subir el ticket", async ({ page }) => {
    await login(page, CREADOR.username, CREADOR.newPassword);

    await page.goto("/transacciones");
    await page.locator("select").nth(2).selectOption("rechazado"); // orden de filtros: Marca, Prioridad, Estado
    const rejectedRow = page.locator("tr", { hasText: BRAND_NAME });
    await expect(rejectedRow).toBeVisible();
    const badge = rejectedRow.getByText("Rechazado");
    await expect(badge).toHaveAttribute("title", new RegExp(REJECTION_REASON.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));

    await page.click('button:has-text("Nuevo Ticket")');
    const modal = page.locator(".fixed.inset-0");
    await modal.locator("select").nth(1).selectOption({ label: BRAND_NAME });
    await modal.locator('input[type="number"]').fill(String(TICKET_AMOUNT));
    await modal.locator('input[type="file"]').setInputFiles({
      name: "comprobante-2.pdf",
      mimeType: "application/pdf",
      buffer: ticketFileBuffer(),
    });
    await modal.locator('button:has-text("Registrar Ticket")').click();
    await expect(modal.getByText("Ticket registrado exitosamente.")).toBeVisible();

    await logout(page);
  });

  test("admin aprueba el ticket re-subido y se descuenta del ciclo vigente", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);

    await page.goto("/validacion");
    const row = page.locator("tr", { hasText: CREATOR_NAME });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Aprobar" }).click();
    await page.locator(".fixed.inset-0").getByRole("button", { name: "Aprobar", exact: true }).click();
    await expect(page.locator("tr", { hasText: CREATOR_NAME })).toHaveCount(0);

    await page.goto("/creadores");
    const card = page.locator(".go-card", { hasText: CREATOR_NAME });
    await expect(card).toContainText("$500.00"); // gastado
    await expect(card).toContainText("$1,500.00"); // restante = 2000 - 500

    await page.goto("/administracion");
    await page.click('button:has-text("Creadores")');
    await page.locator("tr", { hasText: CREATOR_NAME }).getByRole("button", { name: "Histórico" }).click();
    const historyModal = page.locator(".fixed.inset-0");
    await expect(historyModal.getByText("Histórico de ciclos")).toBeVisible();
    await expect(historyModal.locator("table tbody tr").first()).toBeVisible();
    await historyModal.getByRole("button", { name: "Cerrar" }).last().click();

    await logout(page);
  });

  test("el toggle de tema persiste tras recargar la página", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);

    const initialTheme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    await page.click('button[aria-label*="Cambiar a tema"]');
    const toggledTheme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    expect(toggledTheme).not.toBe(initialTheme);

    await page.reload();
    await page.waitForLoadState("networkidle");
    const themeAfterReload = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    expect(themeAfterReload).toBe(toggledTheme);

    // Restaura el tema para no afectar otras pruebas que asuman el default.
    await page.click('button[aria-label*="Cambiar a tema"]');
    await logout(page);
  });

  test("el popover de perfil abre, navega a Mi Perfil y cierra con click afuera", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);

    await page.click('button[aria-haspopup="true"]');
    await expect(page.getByRole("menuitem", { name: "Mi perfil" })).toBeVisible();
    await page.click('button[aria-haspopup="true"]');
    await expect(page.getByRole("menuitem", { name: "Mi perfil" })).toBeHidden();

    await page.click('button[aria-haspopup="true"]');
    await page.getByRole("menuitem", { name: "Mi perfil" }).click();
    await expect(page).toHaveURL(/\/perfil/);

    await logout(page);
  });

  test("el PDF del dashboard se descarga con contenido real", async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.newPassword);
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 60_000 }),
      page.click('button:has-text("Descargar PDF")'),
    ]);
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();

    const fs = await import("node:fs");
    const buffer = fs.readFileSync(downloadPath);
    expect(buffer.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    expect(buffer.byteLength).toBeGreaterThan(10_000);

    await logout(page);
  });

  test("recorrido en 375px: creador abre el drawer móvil y sube un ticket sin scroll horizontal", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await login(page, CREADOR.username, CREADOR.newPassword);

    for (const path of ["/", "/transacciones", "/perfil"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);
    }

    await page.goto("/");
    await page.click('button[aria-label="Abrir menú"]');
    await page.click('button:has-text("Nuevo Ticket")');
    await expect(page.getByText("Registrar Nuevo Ticket")).toBeVisible();
    await page.getByRole("button", { name: "Cerrar" }).click();
  });
});
