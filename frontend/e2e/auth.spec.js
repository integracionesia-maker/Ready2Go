// @ts-check
import { test, expect } from "@playwright/test";

// Nota: el backend limita a 30 logins/15min por IP (rate limiting, ver
// security.py). Cada archivo de esta suite se mantiene bien por debajo de
// eso, pero correr TODOS los .spec.js en una sola invocación de Playwright
// puede acercarse al límite (todos los tests pegan al mismo 127.0.0.1). Si
// eso pasa, corre los archivos por separado:
//   npx playwright test e2e/auth.spec.js
//   npx playwright test e2e/presupuesto-flujo-completo.spec.js

// Sufijo único para que la suite sea repetible contra la misma DB de prueba
// sin colisionar con usuarios/creadores de una corrida anterior.
const RUN_ID = Date.now();
const SUPERADMIN = { username: "superadmin", password: process.env.E2E_SUPERADMIN_PASSWORD || "" };

const ADMIN = {
  username: `admin.e2e.${RUN_ID}`,
  email: `admin.e2e.${RUN_ID}@test.com`,
  fullName: `Admin E2E ${RUN_ID}`,
  password: "AdminE2EClave123!",
  newPassword: "AdminE2EClaveNueva123!",
};

const CREATOR_NAME = `Creador E2E ${RUN_ID}`;

const CREADOR = {
  username: `creador.e2e.${RUN_ID}`,
  email: `creador.e2e.${RUN_ID}@test.com`,
  fullName: `Persona Creadora E2E ${RUN_ID}`,
  password: "CreadorE2EClave123!",
  newPassword: "CreadorE2EClaveNueva123!",
};

async function login(page, identificador, password) {
  await page.goto("/login");
  await page.fill('input[autocomplete="username"]', identificador);
  await page.fill('input[autocomplete="current-password"]', password);
  // Espera la respuesta del login antes de continuar: un page.goto() inmediato
  // después del click puede navegar antes de que la cookie de sesión se procese.
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
  // El botón vive dentro del popover de perfil (R1) — hay que abrirlo primero.
  await page.click('button[aria-haspopup="true"]');
  await page.click('button:has-text("Cerrar sesión")');
  await expect(page).toHaveURL(/\/login/);
}

test.describe.serial("Flujo de autenticación por rol", () => {
  test("ruta protegida sin sesión redirige a /login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("superadmin inicia sesión, cambia contraseña forzada y crea un admin", async ({ page }) => {
    test.skip(!SUPERADMIN.password, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

    await login(page, SUPERADMIN.username, SUPERADMIN.password);
    await changePasswordOnForcedPerfil(page, SUPERADMIN.password, "SuperClaveE2ENueva123!");

    await page.goto("/administracion");
    await page.click('button:has-text("Usuarios")');
    await page.click('button:has-text("Nuevo Usuario")');

    const modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').nth(0).fill(ADMIN.username); // usuario
    await modal.locator('input[type="text"]').nth(1).fill(ADMIN.fullName); // nombre completo
    await modal.locator('input[type="email"]').fill(ADMIN.email);
    await modal.locator("select").first().selectOption("admin");
    await modal.locator('input[type="password"]').fill(ADMIN.password);
    await modal.locator('button:has-text("Crear")').click();

    await expect(page.getByRole("cell", { name: ADMIN.username, exact: true })).toBeVisible();
    await logout(page);
  });

  test("admin inicia sesión, ve dashboard/creadores pero NO usuarios, y crea un creador", async ({ page }) => {
    test.skip(!SUPERADMIN.password, "Requiere que el test anterior haya creado el admin");

    await login(page, ADMIN.username, ADMIN.password);
    await changePasswordOnForcedPerfil(page, ADMIN.password, ADMIN.newPassword);

    // R5: admin ve dashboard/creadores/administración (todo excepto usuarios).
    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).toContainText("Dashboard");
    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).toContainText("Creadores");
    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).toContainText("Administración");
    await page.goto("/dashboard");
    await expect(page).not.toHaveURL(/\/403/);

    await page.goto("/administracion");
    // R4: "Usuarios" ya no es una pestaña visible/operable para admin.
    await expect(page.getByRole("button", { name: "Usuarios", exact: true })).toHaveCount(0);

    await page.click('button:has-text("Creadores")');
    await page.click('button:has-text("Nuevo Creador")');

    const creatorModal = page.locator(".fixed.inset-0");
    await creatorModal.locator('input[type="text"]').fill(CREATOR_NAME);
    await creatorModal.locator('input[type="number"]').fill("50000"); // monto del ciclo, periodicidad queda "Mensual" (default)
    await creatorModal.locator('button:has-text("Crear")').click();
    await expect(page.getByText(CREATOR_NAME)).toBeVisible();

    await logout(page);
  });

  test("R4: admin recibe 403 si intenta la API de usuarios directamente", async ({ page, request }) => {
    test.skip(!SUPERADMIN.password, "Requiere que el test anterior haya creado el admin");

    await login(page, ADMIN.username, ADMIN.newPassword);
    const resp = await page.request.get("/api/users/");
    expect(resp.status()).toBe(403);
    await logout(page);
  });

  test("superadmin vincula un usuario rol creador al creador recién creado (R4: solo superadmin gestiona usuarios)", async ({ page }) => {
    test.skip(!SUPERADMIN.password, "Requiere que el test anterior haya creado el creador");

    await login(page, SUPERADMIN.username, "SuperClaveE2ENueva123!");
    await page.goto("/administracion");
    await page.click('button:has-text("Usuarios")');
    await page.click('button:has-text("Nuevo Usuario")');

    const userModal = page.locator(".fixed.inset-0");
    await userModal.locator('input[type="text"]').nth(0).fill(CREADOR.username);
    await userModal.locator('input[type="text"]').nth(1).fill(CREADOR.fullName);
    await userModal.locator('input[type="email"]').fill(CREADOR.email);
    // El rol por default del select ya es "creador"; solo falta vincular el creador.
    await userModal.locator("select").nth(1).selectOption({ label: CREATOR_NAME });
    await userModal.locator('input[type="password"]').fill(CREADOR.password);
    await userModal.locator('button:has-text("Crear")').click();

    await expect(page.getByRole("cell", { name: CREADOR.username, exact: true })).toBeVisible();
    await logout(page);
  });

  test("creador inicia sesión, ve solo su información (ciclo) y cierra sesión", async ({ page }) => {
    test.skip(!SUPERADMIN.password, "Requiere que el test anterior haya creado el creador");

    await login(page, CREADOR.username, CREADOR.password);
    await changePasswordOnForcedPerfil(page, CREADOR.password, CREADOR.newPassword);

    // Sidebar de un creador: sin Dashboard, Creadores, Validación ni Administración.
    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).not.toContainText("Dashboard");
    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).not.toContainText("Administración");
    await expect(page.getByRole("navigation", { name: "Navegacion de Presupuestos" })).not.toContainText("Validación");

    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/403/);

    await page.goto("/transacciones");
    await expect(page.getByText("Historial de Transacciones")).toBeVisible();

    await page.goto("/perfil");
    await expect(page.getByText("Mi ciclo de presupuesto")).toBeVisible();
    await expect(page.getByText("$50,000.00").first()).toBeVisible();

    await logout(page);
  });

  test("usuario desactivado no puede iniciar sesión", async ({ page, request }) => {
    test.skip(!SUPERADMIN.password, "Requiere que el test anterior haya creado el admin");

    // Login como superadmin para desactivar al admin recién creado.
    await login(page, SUPERADMIN.username, "SuperClaveE2ENueva123!");
    await page.goto("/administracion");
    await page.click('button:has-text("Usuarios")');

    const row = page.locator("tr", { hasText: ADMIN.username });
    await row.getByRole("button", { name: "Desactivar" }).click();
    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(row.getByText("Inactivo")).toBeVisible();
    await logout(page);

    // El admin desactivado ya no puede entrar.
    await login(page, ADMIN.username, ADMIN.newPassword);
    await expect(page.getByText("Usuario o contraseña incorrectos.")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});
