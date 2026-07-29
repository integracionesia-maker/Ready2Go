// @ts-check
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { RUTAS, ANCHOS, medirPantalla, pantallaVacia, dashboardSinGraficos } from "./helpers/pantallas.mjs";
import { ratio, alphaDe } from "./helpers/contraste.mjs";

// Formaliza el verificador de capturas (B-I05): recorre las 10 rutas en
// 1280x800 y 390x844 (20 capturas), falla si una pantalla sale vacía o si
// el dashboard monta cero gráficos Apex (R-I04), y mide el contraste real
// del velo de cada superficie de cristal del shell. Un solo login con
// storageState para las 20 capturas (rate limit 30/15min por IP).

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.join(__dirname, ".auth");
const SCREENSHOTS_DIR = path.join(__dirname, ".screenshots");
const STORAGE_STATE_PATH = path.join(AUTH_DIR, "pantallas-admin.json");

const SUPERADMIN_USERNAME = "superadmin";
const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
const RUN_ID = Date.now();
const SUPERADMIN_NEW_PASSWORD = `SuperPantallasE2E${RUN_ID}!`;

const CREATOR_NAME = `Creador Pantallas ${RUN_ID}`;
const BRAND_NAME = `Marca Pantallas ${RUN_ID}`;

function ticketFileBuffer() {
  return Buffer.from(`%PDF-1.4\n% comprobante de prueba E2E pantallas ${RUN_ID}\n`);
}

async function login(page, identificador, password) {
  await page.goto("/login");
  await page.fill('input[autocomplete="username"]', identificador);
  await page.fill('input[autocomplete="current-password"]', password);
  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes("/api/auth/login")),
    page.click('button[type="submit"]'),
  ]);
}

test.describe.serial("Verificador de pantallas (B-I05)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

  test("bootstrap: sesión + datos reales (evita R-I04), guarda storageState", async ({ page }) => {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

    await login(page, SUPERADMIN_USERNAME, SUPERADMIN_SEED_PASSWORD);
    await expect(page).toHaveURL(/\/perfil/);
    const pw = page.locator('input[type="password"]');
    await pw.nth(0).fill(SUPERADMIN_SEED_PASSWORD);
    await pw.nth(1).fill(SUPERADMIN_NEW_PASSWORD);
    await pw.nth(2).fill(SUPERADMIN_NEW_PASSWORD);
    await page.click('button:has-text("Actualizar contraseña")');
    await expect(page.getByText("Contraseña actualizada.")).toBeVisible();

    // Un creador + marca + ticket real (auto-aprobado por venir de
    // superadmin) para que /dashboard tenga algo que graficar en vez de
    // pintar el estado "Sin datos" con la DB "llena" (R-I04, trampa ya
    // pagada en I0: hay que aprobar por la API real, no tocar la DB).
    await page.goto("/administracion");
    await page.click('button:has-text("Creadores")');
    await page.click('button:has-text("Nuevo Creador")');
    let modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').fill(CREATOR_NAME);
    await modal.locator('input[type="number"]').fill("5000");
    await modal.locator("select").selectOption("mensual");
    await modal.locator('button:has-text("Crear")').click();
    await expect(page.locator("tr", { hasText: CREATOR_NAME })).toBeVisible();

    await page.click('button:has-text("Marcas")');
    await page.click('button:has-text("Nueva Marca")');
    modal = page.locator(".fixed.inset-0");
    await modal.locator('input[type="text"]').fill(BRAND_NAME);
    await modal.locator("select").selectOption("alta");
    await modal.locator('button:has-text("Crear")').click();
    await expect(page.locator("tr", { hasText: BRAND_NAME })).toBeVisible();

    await page.goto("/");
    await page.click('button:has-text("Nuevo Ticket")');
    modal = page.locator(".fixed.inset-0");
    // La opción de creador lleva un sufijo "— Restante del ciclo: $X" (no es
    // solo el nombre), así que selectOption({label}) exacto no la encuentra:
    // se ubica por texto parcial y se selecciona por su value real.
    const creatorOptionValue = await modal
      .locator("select")
      .nth(0)
      .locator("option", { hasText: CREATOR_NAME })
      .getAttribute("value");
    await modal.locator("select").nth(0).selectOption(creatorOptionValue);
    await modal.locator("select").nth(1).selectOption({ label: BRAND_NAME });
    await modal.locator('input[type="number"]').fill("750");
    await modal.locator('input[type="file"]').setInputFiles({
      name: "comprobante-pantallas.pdf",
      mimeType: "application/pdf",
      buffer: ticketFileBuffer(),
    });
    await modal.locator('button:has-text("Registrar Ticket")').click();
    await expect(modal.getByText("Ticket registrado exitosamente.")).toBeVisible();

    await page.context().storageState({ path: STORAGE_STATE_PATH });
  });

  for (const ancho of ANCHOS) {
    test(`pantalla /login en ${ancho.nombre} (sin sesión)`, async ({ browser }) => {
      const context = await browser.newContext({ viewport: { width: ancho.width, height: ancho.height } });
      const page = await context.newPage();
      await page.goto("/login", { waitUntil: "networkidle" });
      await page.waitForTimeout(300);

      const medicion = await medirPantalla(page);
      expect(pantallaVacia(medicion), `/login vacía en ${ancho.nombre}: ${JSON.stringify(medicion)}`).toBe(false);

      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, `login-${ancho.nombre}.png`) });
      await context.close();
    });

    for (const ruta of RUTAS.filter((r) => r !== "/login")) {
      const nombreArchivo = ruta === "/" ? "home" : ruta.replace("/", "");

      test(`pantalla ${ruta} en ${ancho.nombre}`, async ({ browser }) => {
        const context = await browser.newContext({
          storageState: STORAGE_STATE_PATH,
          viewport: { width: ancho.width, height: ancho.height },
        });
        const page = await context.newPage();
        await page.goto(ruta, { waitUntil: "networkidle" });
        await page.waitForTimeout(300);

        const medicion = await medirPantalla(page);
        expect(pantallaVacia(medicion), `${ruta} vacía en ${ancho.nombre}: ${JSON.stringify(medicion)}`).toBe(false);
        expect(
          dashboardSinGraficos(ruta, medicion),
          `${ruta} sin gráficos Apex en ${ancho.nombre}: ${JSON.stringify(medicion)}`
        ).toBe(false);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, `${nombreArchivo}-${ancho.nombre}.png`) });
        await context.close();
      });
    }
  }

  // "/" tiene el nav de módulos del shell; "/dashboard" agrega las 2 KpiTile
  // con glass=true (I2) — cristal nuevo que este mismo verificador todavía
  // no habia visitado. Medir ahi tambien, no solo asumir que el patron de "/"
  // se sostiene en toda pantalla que use .glass.
  for (const ruta of ["/", "/dashboard"]) {
    test(`contraste medido en ${ruta}: velo de cada superficie de cristal >= 4.5:1`, async ({ browser }) => {
      const context = await browser.newContext({
        storageState: STORAGE_STATE_PATH,
        viewport: { width: 1280, height: 800 },
      });
      const page = await context.newPage();
      await page.goto(ruta, { waitUntil: "networkidle" });

      const glassSurfaces = await page.locator(".glass").all();
      expect(glassSurfaces.length, `Ninguna superficie .glass montada en ${ruta}`).toBeGreaterThan(0);

      for (const glass of glassSurfaces) {
        // El velo puede ser hijo (GlassPanel/GlassModal/Toast) o hermano en
        // capa de fondo (GlassNav, con -z-10) — se busca dentro del propio
        // contenedor .glass, no se asume una relación padre-hijo fija.
        const { veilBg, textColor } = await glass.evaluate((el) => {
          const veil = el.querySelector(".veil") || el;
          // El nodo que de verdad pinta el texto visible es el más profundo
          // con un nodo de texto propio — un <a> que envuelve un <span> con
          // color explícito matchea el selector primero por orden de
          // documento, pero su color computado no es el que se ve en pantalla.
          const candidates = Array.from(el.querySelectorAll("span, p, h1, h2, h3, button, a")).reverse();
          const leaf = candidates.find((node) =>
            Array.from(node.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim())
          );
          const textEl = leaf || el;
          return {
            veilBg: getComputedStyle(veil).backgroundColor,
            textColor: getComputedStyle(textEl).color,
          };
        });

        expect(alphaDe(veilBg), `Velo translúcido (alpha != 1): ${veilBg}`).toBe(1);

        const contraste = ratio(textColor, veilBg);
        expect(
          contraste,
          `Contraste ${contraste.toFixed(2)}:1 insuficiente — texto ${textColor} sobre velo ${veilBg}`
        ).toBeGreaterThanOrEqual(4.5);
      }

      await context.close();
    });
  }
});
