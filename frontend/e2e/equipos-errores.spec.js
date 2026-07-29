// @ts-check
import { test, expect } from "@playwright/test";
import { contextoDe } from "./helpers/sesiones.mjs";

// Los cinco códigos feos del contrato de Equipos, probados HOY contra el
// mock de I3 (VITE_EQUIPOS_MOCK=1) — a diferencia de
// equipos-flujo-completo.spec.js (fixme, espera al servidor real), esto
// corre desde el día 1 porque el mock ya existe. Usa DevMockHarness.jsx
// (I3) como "UI" de prueba: es lo único que hoy reacciona visiblemente a
// estos códigos, ya que las 7 vistas reales de Equipos son I4. Cuando I4
// aterrice, este archivo se reescribe para apuntar a la UI real (queda
// anotado en docs/backlog_interfaz.md).
//
// Requiere: `npx vite` corriendo con VITE_EQUIPOS_MOCK=1 (si no, la ruta
// /equipos/_mock-harness ni siquiera existe — es dev-only).

const SUPERADMIN_USERNAME = "superadmin";
const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";

const CODIGOS = [
  { boton: /EQUIPO_OCUPADO/, status: 409, codigo: "EQUIPO_OCUPADO" },
  { boton: /SIN_PERMISO/, status: 403, codigo: "SIN_PERMISO" },
  { boton: /PERMISOS_NO_DISPONIBLES/, status: 503, codigo: "PERMISOS_NO_DISPONIBLES" },
  { boton: /MEDIA_MUY_GRANDE/, status: 413, codigo: "MEDIA_MUY_GRANDE" },
  { boton: /a mitad del wizard/, status: 401, codigo: null }, // SESION_EXPIRADA: el fixture trae codigo:null
];

test.describe.serial("Códigos feos del contrato de Equipos, contra el mock (I3)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

  test("bootstrap: sesión con contraseña ya definitiva", async ({ browser }) => {
    // El harness no filtra por permiso (es diagnóstico crudo, no una vista
    // real) — cualquier sesión autenticada de Presupuestos alcanza. Pero el
    // login de superadmin fuerza cambio de contraseña en su primer uso, y
    // sesiones.mjs no lo resuelve (asume contraseña definitiva) — se hace
    // aquí, una vez, y se cachea para el resto de los tests de este archivo.
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto("/login");
    await page.fill('input[autocomplete="username"]', SUPERADMIN_USERNAME);
    await page.fill('input[autocomplete="current-password"]', SUPERADMIN_SEED_PASSWORD);
    await Promise.all([
      page.waitForResponse((r) => r.url().includes("/api/auth/login")),
      page.click('button[type="submit"]'),
    ]);
    // El login resuelve la respuesta de red antes de que el SPA navegue a
    // /perfil (esa navegación es un `navigate()` posterior, del lado del
    // cliente) — esperar la URL explícitamente, no leerla de inmediato.
    await page.waitForURL(/\/perfil/, { timeout: 5000 }).catch(() => {});
    if (page.url().includes("/perfil")) {
      const pw = page.locator('input[type="password"]');
      await pw.nth(0).fill(SUPERADMIN_SEED_PASSWORD);
      await pw.nth(1).fill("SuperEquiposErroresE2E123!");
      await pw.nth(2).fill("SuperEquiposErroresE2E123!");
      await page.click('button:has-text("Actualizar contraseña")');
      await expect(page.getByText("Contraseña actualizada.")).toBeVisible();
    }
    await context.storageState({ path: "e2e/.auth/superadmin.json" });
    await context.close();
  });

  for (const { boton, status, codigo } of CODIGOS) {
    test(`${status} ${codigo ?? "(sin código)"}: la UI pinta status/código/mensaje reales, sin caerse`, async ({ browser }) => {
      const context = await contextoDe(browser, {
        usuario: "superadmin",
        password: "SuperEquiposErroresE2E123!",
        baseURL: "http://127.0.0.1:5173",
      });
      const page = await context.newPage();
      await page.goto("/equipos/_mock-harness", { waitUntil: "networkidle" });

      await page.getByRole("button", { name: boton }).click();
      await page.waitForTimeout(400);

      // El bloque "Último resultado" de DevMockHarness pinta el JSON crudo
      // del error — se lee de ahí en vez de parsear el texto del Toast,
      // que es más frágil.
      const resultadoTexto = await page.locator("pre").textContent();
      const resultado = JSON.parse(resultadoTexto);

      expect(resultado.status).toBe(status);
      expect(resultado.codigo ?? null).toBe(codigo);
      expect(typeof resultado.message).toBe("string");
      expect(resultado.message.length).toBeGreaterThan(0);

      // La regla dura del pool: un 503 JAMÁS desloguea. Confirmarlo
      // explícitamente para ESE caso, no solo inferirlo de que la página
      // sigue viva.
      if (status === 503) {
        await expect(page).not.toHaveURL(/\/login/);
      }

      await context.close();
    });
  }
});
