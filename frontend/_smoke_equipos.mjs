import { chromium } from "@playwright/test";

const BASE = "http://127.0.0.1:5173";
const SHOTS_DIR = "C:/Users/USUARIO/AppData/Local/Temp/claude/C--Users-USUARIO-drive-Ready2Go/a3c3e291-735f-4760-8ba5-3a2a6efbb2ab/scratchpad";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

page.on("console", (msg) => {
  if (msg.type() === "error") console.log("[console.error]", msg.text());
});
page.on("pageerror", (err) => console.log("[pageerror]", err.message));

await page.goto(BASE + "/login");
await page.fill('input[autocomplete="username"]', "superadmin");
await page.fill('input[autocomplete="current-password"]', "Admin123!");
await Promise.all([
  page.waitForResponse((r) => r.url().includes("/api/auth/login")),
  page.click('button[type="submit"]'),
]);
await page.waitForURL(BASE + "/");
await page.waitForTimeout(800);
await page.screenshot({ path: `${SHOTS_DIR}/01-presupuestos-home.png` });

await page.goto(BASE + "/equipos");
await page.waitForTimeout(1200);
await page.screenshot({ path: `${SHOTS_DIR}/02-equipos-inicio.png` });

await page.goto(BASE + "/equipos/inventario");
await page.waitForTimeout(1200);
await page.screenshot({ path: `${SHOTS_DIR}/03-equipos-inventario.png` });

// Sidebar collapse toggle
await page.locator('button[title="Minimizar menú"]').click();
await page.waitForTimeout(500);
await page.screenshot({ path: `${SHOTS_DIR}/04-equipos-sidebar-collapsed.png` });

// Mobile viewport check (drawer)
await page.setViewportSize({ width: 375, height: 800 });
await page.goto(BASE + "/equipos/historial");
await page.waitForTimeout(1000);
await page.screenshot({ path: `${SHOTS_DIR}/05-equipos-historial-mobile.png` });
await page.click('button[aria-label="Abrir menú"]');
await page.waitForTimeout(400);
await page.screenshot({ path: `${SHOTS_DIR}/06-equipos-mobile-drawer.png` });

await browser.close();
console.log("DONE");
