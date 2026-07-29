import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.join(__dirname, "..", ".auth");

// Un solo login por persona, storageState cacheado en e2e/.auth/<usuario>.json
// y reusado entre tests — el rate limit de login (30/15min por IP, en
// memoria del backend) se agota rápido con un flujo de 3+ personas
// (colaborador_mkt, APROBADOR_EQUIPO, admin) si cada test vuelve a loguearse.
//
// No depende de `auth.spec.js`: ese archivo rota la contraseña del
// superadmin en su test 2 (no es idempotente) — este helper nunca asume esa
// contraseña, siempre recibe la contraseña explícita de quien lo llama.

function storagePathDe(usuario) {
  return path.join(AUTH_DIR, `${usuario}.json`);
}

/**
 * Devuelve un BrowserContext ya autenticado como `usuario`. Si no existe
 * storageState cacheado, hace el login una vez (asume contraseña ya
 * definitiva, sin cambio forzado — para eso está `sembrar-demo.mjs`, que
 * crea usuarios ya con su contraseña final) y lo guarda para las próximas
 * llamadas, en este archivo o en otro spec.
 */
export async function contextoDe(browser, { usuario, password, baseURL = "", viewport } = {}) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  const storagePath = storagePathDe(usuario);

  if (!fs.existsSync(storagePath)) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    await page.goto(baseURL + "/login");
    await page.fill('input[autocomplete="username"]', usuario);
    await page.fill('input[autocomplete="current-password"]', password);
    await Promise.all([
      page.waitForResponse((r) => r.url().includes("/api/auth/login")),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(300);
    await context.storageState({ path: storagePath });
    await page.close();
    return context;
  }

  return browser.newContext({ storageState: storagePath, viewport });
}

/** Borra la sesión cacheada de `usuario` (para forzar un login fresco tras
 * rotar su contraseña, por ejemplo). */
export function olvidarSesionDe(usuario) {
  const p = storagePathDe(usuario);
  if (fs.existsSync(p)) fs.unlinkSync(p);
}
