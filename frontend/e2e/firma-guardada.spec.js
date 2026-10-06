// @ts-check
import { test, expect, request as apiModule } from "@playwright/test";
import { contextoDe } from "./helpers/sesiones.mjs";
import { pngReal } from "./helpers/imagen.mjs";

// Firma predeterminada del perfil (docs/equipos/firma-guardada.md): se guarda
// una vez en el Perfil y se usa para firmar un préstamo con un solo botón; al
// dibujar, una casilla permite guardarla. Corre por separado del resto (rate
// limit de login por IP). Necesita 3 equipos disponibles en el inventario.

const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
const RUN_ID = Date.now();
const CREADOR = {
  username: `creador.firma.${RUN_ID}`,
  email: `creador.firma.${RUN_ID}@test.com`,
  name: `Creador Firma E2E ${RUN_ID}`,
};

async function crearCreadorDefinitivo(request, { username, email, name }) {
  const creado = await request.post("/api/creators/", { data: { name, username, email } });
  expect(creado.ok(), `crear creador ${username}: ${await creado.text()}`).toBeTruthy();
  const tempPassword = (await creado.json()).temporary_password;
  const propio = await apiModule.newContext();
  const login = await propio.post("/api/auth/login", { data: { identificador: username, password: tempPassword } });
  expect(login.ok(), await login.text()).toBeTruthy();
  const cambio = await propio.post("/api/auth/change-password", {
    data: { current_password: tempPassword, new_password: tempPassword },
  });
  expect(cambio.ok(), await cambio.text()).toBeTruthy();
  await propio.dispose();
  return tempPassword;
}

/** Préstamo ya confirmado (con fotos) por API, desde la sesión del propio
 * creador — el wizard completo ya lo cubre equipos-creador.spec.js. */
async function prestamoConfirmado(context) {
  const api = context.request;
  // Siempre un equipo libre: cada préstamo confirmado ocupa el suyo, y así el
  // spec no depende de una base recién sembrada ni de ids concretos.
  const libres = await api.get("/api/equipment/?disponible=true");
  expect(libres.ok(), await libres.text()).toBeTruthy();
  const equipmentId = (await libres.json()).items[0]?.id;
  expect(equipmentId, "no queda ningún equipo disponible en el inventario").toBeTruthy();

  const borrador = await api.post("/api/loans/", { data: { motivo: `E2E firma guardada ${RUN_ID}` } });
  expect(borrador.ok(), await borrador.text()).toBeTruthy();
  const { id } = await borrador.json();

  const conItem = await api.post(`/api/loans/${id}/items`, {
    data: { equipment_id: equipmentId, accesorios_seleccionados: [], cargador_con: "responsable" },
  });
  expect(conItem.ok(), await conItem.text()).toBeTruthy();
  const itemId = (await conItem.json()).items.at(-1).id;

  for (const kind of ["foto_entrega_frente", "foto_entrega_atras"]) {
    const foto = await api.post(`/api/loans/${id}/media`, {
      multipart: {
        kind,
        loan_item_id: String(itemId),
        file: { name: `${kind}.png`, mimeType: "image/png", buffer: pngReal(400, 300) },
      },
    });
    expect(foto.ok(), await foto.text()).toBeTruthy();
  }
  const confirmado = await api.post(`/api/loans/${id}/confirmar`);
  expect(confirmado.ok(), await confirmado.text()).toBeTruthy();
  return (await confirmado.json()).folio;
}

async function dibujar(page, contenedor) {
  const canvas = contenedor.locator("canvas");
  // En el Perfil el canvas puede quedar fuera de la ventana: las coordenadas
  // del mouse son de viewport, así que primero se lo trae a la vista.
  await canvas.scrollIntoViewIfNeeded();
  const caja = await canvas.boundingBox();
  await page.mouse.move(caja.x + 20, caja.y + caja.height / 2);
  await page.mouse.down();
  await page.mouse.move(caja.x + 120, caja.y + caja.height / 2 - 20, { steps: 5 });
  await page.mouse.move(caja.x + 160, caja.y + caja.height / 2 + 10, { steps: 5 });
  await page.mouse.up();
}

test.describe.serial("Firma predeterminada del perfil (servidor real)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

  let password;

  test("bootstrap: superadmin crea un creador", async ({ request }) => {
    const login = await request.post("/api/auth/login", {
      data: { identificador: "superadmin", password: SUPERADMIN_SEED_PASSWORD },
    });
    expect(login.ok(), await login.text()).toBeTruthy();
    password = await crearCreadorDefinitivo(request, CREADOR);
  });

  test("1: sin firma guardada, el Perfil muestra el pad y el modal de firma no ofrece la guardada", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password });
    const page = await context.newPage();

    await page.goto("/perfil");
    const panel = page.getByTestId("panel-mi-firma");
    await expect(panel.locator("canvas")).toBeVisible();
    await expect(page.getByTestId("mi-firma-preview")).toHaveCount(0);

    const folio = await prestamoConfirmado(context);
    await page.goto(`/equipos/prestamo/${folio}`);
    await page.getByRole("button", { name: "Completar firma" }).click();
    const dialogo = page.getByRole("dialog");
    await expect(dialogo.locator("canvas")).toBeVisible();
    await expect(dialogo.getByTestId("firma-usar-guardada")).toHaveCount(0);
    // Para el beneficiario (él mismo) sí se ofrece guardar lo que dibuje.
    await expect(dialogo.getByTestId("firma-guardar-predeterminada")).toBeVisible();
    await context.close();
  });

  test("2: guardar la firma en el Perfil", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password });
    const page = await context.newPage();
    await page.goto("/perfil");

    const panel = page.getByTestId("panel-mi-firma");
    await panel.getByTestId("guardar-mi-firma").click(); // vacío
    await expect(panel.getByText("Dibuja tu firma antes de guardar.")).toBeVisible();

    await dibujar(page, panel);
    await panel.getByTestId("guardar-mi-firma").click();
    await expect(page.getByTestId("mi-firma-preview")).toBeVisible();
    await expect(panel.getByText(/Firma guardada/)).toBeVisible();

    // Persiste tras recargar y se sirve como imagen real, solo a su dueño.
    await page.reload();
    const preview = page.getByTestId("mi-firma-preview");
    await expect(preview).toBeVisible();
    await expect.poll(() => preview.evaluate((img) => /** @type {HTMLImageElement} */ (img).naturalWidth)).toBeGreaterThan(0);
    await context.close();
  });

  test("3: firmar un préstamo con la firma guardada, con un solo botón", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password });
    const page = await context.newPage();
    const folio = await prestamoConfirmado(context);

    await page.goto(`/equipos/prestamo/${folio}`);
    await page.getByRole("button", { name: "Completar firma" }).click();
    const dialogo = page.getByRole("dialog");
    await expect(dialogo.getByTestId("firma-guardada-preview")).toBeVisible();
    await expect(dialogo.locator("canvas")).toHaveCount(0);

    await dialogo.getByRole("button", { name: "Firmar con mi firma guardada" }).click();
    await expect(dialogo).toBeHidden();
    await expect(page.getByRole("button", { name: "Completar firma" })).toHaveCount(0);
    // La firma del beneficiario ya aparece en la ficha.
    await expect(page.getByRole("img", { name: "Firma del beneficiario" }).or(page.getByLabel("Firma del beneficiario")).first()).toBeVisible();
    await context.close();
  });

  test("4: 'Dibujar otra' vuelve al pad, y se puede reemplazar la predeterminada al firmar", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password });
    const page = await context.newPage();
    const folio = await prestamoConfirmado(context);

    await page.goto(`/equipos/prestamo/${folio}`);
    await page.getByRole("button", { name: "Completar firma" }).click();
    const dialogo = page.getByRole("dialog");
    await dialogo.getByTestId("firma-dibujar-otra").click();
    await expect(dialogo.locator("canvas")).toBeVisible();
    await expect(dialogo.getByTestId("firma-usar-guardada")).toBeVisible();
    await dibujar(page, dialogo);
    await dialogo.getByTestId("firma-guardar-predeterminada").check();
    await dialogo.getByRole("button", { name: "Guardar firma" }).click();
    await expect(dialogo).toBeHidden();
    await context.close();
  });

  test("5: eliminar la firma del Perfil", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: CREADOR.username, password });
    const page = await context.newPage();
    await page.goto("/perfil");
    await expect(page.getByTestId("mi-firma-preview")).toBeVisible();

    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Eliminar" }).click();
    await expect(page.getByTestId("panel-mi-firma").locator("canvas")).toBeVisible();
    await expect(page.getByTestId("mi-firma-preview")).toHaveCount(0);
    await context.close();
  });
});
