// @ts-check
import { test, expect } from "@playwright/test";

/**
 * Página 404 (lote de calidad 2026-08-18).
 *
 * Antes: una ruta inexistente redirigía a `/` en silencio (Presupuestos) o
 * dejaba el contenido vacío (Equipos). Ahora ambos módulos muestran una
 * 404 dentro del shell autenticado, con CTA de regreso.
 *
 * Requiere backend + frontend corriendo y la contraseña sembrada del
 * superadmin (mismo contrato que `pantallas.spec.js`).
 */

const SUPERADMIN_USERNAME = "superadmin";
const SUPERADMIN_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";

test.describe("Página 404 dentro del shell", () => {
  test.skip(
    !SUPERADMIN_PASSWORD,
    "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py"
  );

  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[autocomplete="username"]', SUPERADMIN_USERNAME);
    await page.fill('input[autocomplete="current-password"]', SUPERADMIN_PASSWORD);
    await Promise.all([
      page.waitForResponse((resp) => resp.url().includes("/api/auth/login")),
      page.click('button[type="submit"]'),
    ]);
    // El destino post-login depende del estado de la cuenta (cambio de
    // contraseña pendiente o no); lo único que importa es no quedar en /login.
    await expect(page).not.toHaveURL(/\/login/);
  });

  test("ruta inexistente de Presupuestos muestra el 404 dentro del shell", async ({ page }) => {
    await page.goto("/ruta-que-no-existe");
    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByText("Página no encontrada")).toBeVisible();
    await expect(page.getByRole("link", { name: "Volver al inicio" })).toBeVisible();
  });

  test("ruta inexistente de Equipos muestra el 404 dentro del shell", async ({ page }) => {
    await page.goto("/equipos/ruta-que-no-existe");
    await expect(page.getByText("Página no encontrada")).toBeVisible();
    await expect(page.getByRole("link", { name: "Volver al inicio" })).toBeVisible();
  });

  test("el CTA regresa a la portada", async ({ page }) => {
    await page.goto("/ruta-que-no-existe");
    await page.getByRole("link", { name: "Volver al inicio" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByText("Página no encontrada")).toBeHidden();
  });
});
