// @ts-check
import { test, expect, request as apiModule } from "@playwright/test";
import { contextoDe } from "./helpers/sesiones.mjs";
import { pngReal } from "./helpers/imagen.mjs";

// I9 (07/09/2026) — los beneficiarios reales de un préstamo de Equipos son
// los creadores: el rol base `creador` gana `equipos_inventario:ver` +
// `equipos_prestamos:{solicitar,ver_propios,registrar_devolucion}` (mismo
// set que `colaborador_mkt`, ver rbac_catalog.py), con el menú reducido a
// 4 vistas (Inicio, Inventario, Nuevo préstamo, Historial — sin Dashboard,
// Activos ni Aprobaciones) y el beneficiario del wizard autoasignado a sí
// mismo, sin elegir nada. Este archivo corre por separado del resto de
// Equipos (mismo motivo que auth.spec.js/presupuesto-flujo-completo.spec.js:
// rate limit de login por IP).

const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
const RUN_ID = Date.now();
const CREADOR = {
  username: `creador.equipos.${RUN_ID}`,
  email: `creador.equipos.${RUN_ID}@test.com`,
  name: `Creador Equipos E2E ${RUN_ID}`,
};
const MOTIVO = `Prueba E2E creador ${RUN_ID}`;

/** A diferencia de `crearUsuarioDefinitivo` (equipos-flujo-completo.spec.js),
 * un creador se crea vía `POST /api/creators/` — es el único endpoint que
 * vincula `creator_id` a un `User` nuevo con rol `creador` (ver
 * routers/creators.py::create_creator). Devuelve `temporary_password`, no se
 * elige una propia. */
async function crearCreadorDefinitivo(request, { username, email, name }) {
  const creado = await request.post("/api/creators/", { data: { name, username, email } });
  expect(creado.ok(), `crear creador ${username}: ${await creado.text()}`).toBeTruthy();
  const cuerpo = await creado.json();
  const tempPassword = cuerpo.temporary_password;
  expect(tempPassword, "el POST de creadores debería devolver temporary_password").toBeTruthy();

  const propio = await apiModule.newContext();
  const login = await propio.post("/api/auth/login", { data: { identificador: username, password: tempPassword } });
  expect(login.ok(), await login.text()).toBeTruthy();
  const cambio = await propio.post("/api/auth/change-password", {
    data: { current_password: tempPassword, new_password: tempPassword },
  });
  expect(cambio.ok(), await cambio.text()).toBeTruthy();
  await propio.dispose();
  return { id: cuerpo.id, userId: cuerpo.user_id, password: tempPassword };
}

test.describe.serial("Creadores como beneficiarios de Equipos (I9, servidor real)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

  let creadorPassword;

  test("bootstrap: superadmin crea un creador real", async ({ request }) => {
    const login = await request.post("/api/auth/login", {
      data: { identificador: "superadmin", password: SUPERADMIN_SEED_PASSWORD },
    });
    expect(login.ok(), await login.text()).toBeTruthy();

    const { password } = await crearCreadorDefinitivo(request, CREADOR);
    creadorPassword = password;
  });

  test("1: el menú de Equipos de un creador muestra solo 4 vistas", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password: creadorPassword });
    const page = await context.newPage();
    await page.goto("/equipos");

    const nav = page.getByRole("navigation", { name: "Navegación de Equipos" });
    await expect(nav.getByRole("link", { name: "Inicio" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Inventario" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Nuevo préstamo" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Historial" })).toBeVisible();
    // Comparten permiso con Inicio/Historial pero se ocultan por rol
    // (EquiposSidebar.jsx: ocultoParaRoles) — la regla no es expresable
    // solo con permisos, ver docs/equipos/creadores-como-beneficiarios.md.
    await expect(nav.getByRole("link", { name: "Dashboard" })).toHaveCount(0);
    await expect(nav.getByRole("link", { name: "Activos" })).toHaveCount(0);
    await expect(nav.getByRole("link", { name: "Aprobaciones" })).toHaveCount(0);

    await context.close();
  });

  test("2: no puede dar de alta equipo — Inventario es de solo lectura", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password: creadorPassword });
    const page = await context.newPage();
    await page.goto("/equipos/inventario");
    await expect(page.getByRole("heading", { name: /Inventario/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Nuevo equipo|Dar de alta/i })).toHaveCount(0);
    await context.close();
  });

  test("3: el beneficiario del wizard se autoasigna, completa su préstamo y lo ve en su Historial", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password: creadorPassword });
    const page = await context.newPage();

    await page.goto("/equipos/nuevo");
    // Sin selector de beneficiario ni inputs de nombre/correo — solo su
    // propio nombre, de solo lectura (NuevoPrestamoPage.jsx: `esCreador`).
    // Aparece más de una vez ("Solicitado por" + "Beneficiario" + el menú de
    // perfil) — basta con que exista, no hace falta que sea único.
    await expect(page.getByText(CREADOR.name).first()).toBeVisible();
    await expect(page.locator("select")).toHaveCount(1); // el único select es "Marca"

    await page.locator('input[type="text"]').nth(0).fill("Contenido"); // Área
    await page.locator("select.go-select").first().selectOption({ index: 1 }); // Marca
    await page.locator('input[type="text"]').nth(1).fill(MOTIVO); // Motivo
    await page.locator('input[type="date"]').fill("2026-09-20");
    await page.locator('button[type="submit"]').click();
    await page.waitForSelector("text=Equipos disponibles", { timeout: 10_000 });

    await page.getByRole("button", { name: "+ Agregar" }).first().click();
    const cargador = page.locator("select.go-select");
    if (await cargador.count()) await cargador.first().selectOption({ index: 1 });
    await page.getByRole("button", { name: "Confirmar" }).click();
    await page.waitForTimeout(600);
    await page.getByRole("button", { name: "Siguiente" }).click();

    await page.waitForSelector('button:has-text("Elegir archivo")', { timeout: 10_000 });
    const totalBotones = await page.getByRole("button", { name: "Elegir archivo" }).count();
    for (let i = 0; i < totalBotones; i++) {
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.getByRole("button", { name: "Elegir archivo" }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles({ name: `foto-${i}.png`, mimeType: "image/png", buffer: pngReal(400, 300) });
      await page.waitForTimeout(700);
    }

    const confirmarPrestamo = page.getByRole("button", { name: "Confirmar préstamo" });
    await expect(confirmarPrestamo).toBeEnabled();
    await confirmarPrestamo.click();
    await page.waitForURL(/\/equipos\/prestamo\//, { timeout: 15_000 });
    // Del URL, no del texto: el toast de éxito ("Folio CE-xxxx — pendiente...")
    // también matchea /CE-\d{4,}/ y su orden en el DOM contra el de la
    // página no es determinista.
    const folio = new URL(page.url()).pathname.split("/").pop();

    // Su propia firma (`firma_responsable`) — el botón ya funciona con el
    // mismo permiso `equipos_prestamos:solicitar` que acaba de ganar.
    await page.getByRole("button", { name: "Completar firma" }).click();
    const dialogoFirma = page.getByRole("dialog");
    const canvas = dialogoFirma.locator("canvas");
    const cajaFirma = await canvas.boundingBox();
    await page.mouse.move(cajaFirma.x + 20, cajaFirma.y + cajaFirma.height / 2);
    await page.mouse.down();
    await page.mouse.move(cajaFirma.x + 100, cajaFirma.y + cajaFirma.height / 2 - 15);
    await page.mouse.up();
    await dialogoFirma.getByRole("button", { name: "Guardar firma" }).click();
    await expect(dialogoFirma).toBeHidden();
    await expect(page.getByRole("button", { name: "Completar firma" })).toHaveCount(0);

    // Aparece en su propio Historial (ver_propios).
    await page.goto("/equipos/historial");
    await expect(page.locator("tbody tr", { hasText: folio })).toBeVisible({ timeout: 10_000 });

    // Registrar su propia devolución — único lugar disponible es la Ficha,
    // no tiene la pestaña "Activos" (docs/equipos/creadores-como-beneficiarios.md).
    await page.goto(`/equipos/prestamo/${folio}`);
    const botonDevolucion = page.getByRole("button", { name: "Registrar devolución" });
    await expect(botonDevolucion).toBeVisible();
    await botonDevolucion.click();

    const items = page.getByTestId("equipos-devolucion").locator("li");
    await expect(items).toHaveCount(1);
    for (let i = 0; i < 2; i++) {
      const fileChooserPromise = page.waitForEvent("filechooser");
      await items.nth(0).getByRole("button", { name: "Elegir archivo" }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles({ name: `dev-${i}.png`, mimeType: "image/png", buffer: pngReal(400, 300) });
      await page.waitForTimeout(700);
    }
    await page.getByRole("dialog").getByRole("button", { name: "Registrar devolución" }).click();
    await expect(page.getByText(/Devolución registrada/i)).toBeVisible();
    await expect(page.getByTestId("badge-estado")).toHaveText(/Pend\. confirmación/i);

    await context.close();
  });
});
