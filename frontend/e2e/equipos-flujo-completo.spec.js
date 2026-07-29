// @ts-check
import { test, expect } from "@playwright/test";
import { contextoDe } from "./helpers/sesiones.mjs";
import { pngReal, firmaPng } from "./helpers/imagen.mjs";

// EN test.fixme HASTA QUE EL SERVIDOR REAL EXISTA. Se escribe ahora (I6)
// porque escribirlo contra el contrato congelado (API_EQUIPOS_v1.md) obliga
// a leerlo de punta a punta y saca los huecos ANTES de construir las 7
// vistas de I4 — cada hueco encontrado aquí cuesta minutos; encontrado en
// la integración real cuesta días. Los huecos que sí se encontraron ya
// están en docs/riesgos/interfaz.md (R-I13 de I3, más los de este archivo).
//
// Condición que lo despierta (quita el test.fixme de la línea del
// describe): los endpoints de API_EQUIPOS_v1.md §2-§6 en pie en el
// servidor real (inventario, préstamos, aprobación, media, empresas) + el
// seed de WP2 (8 equipos + 2 razones sociales, `seed_prestamo_demo.py` o
// equivalente).
//
// Los selectores de abajo son ASPIRACIONALES: describen la interacción tal
// como la exige el contrato (campos, mensajes, badges), pero I4 (las 7
// vistas reales) todavía no existe — nadie ha visto el markup real todavía.
// Cuando I4 aterrice, este archivo necesita una pasada de ajuste de
// selectores, no un rediseño del flujo (el flujo en sí ya está validado
// contra el contrato).

const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
const RUN_ID = Date.now();

// Personas del flujo (WP1/RBAC aditivo todavía no aterriza en el servidor
// real — estos usuarios no se pueden crear hoy vía la UI de Administración,
// que solo sabe de admin/creador. Aspiracional también, a la espera de WP1).
const SOLICITANTE = { usuario: `colaborador.equipos.${RUN_ID}`, password: `ColaboradorEquiposE2E${RUN_ID}!` };
const APROBADORA = { usuario: `melisa.equipos.${RUN_ID}`, password: `AprobadoraEquiposE2E${RUN_ID}!` };
const ADMIN = { usuario: `admin.equipos.${RUN_ID}`, password: `AdminEquiposE2E${RUN_ID}!` };

test.describe("Flujo completo de un préstamo de Equipos (extremo a extremo)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

  // eslint-disable-next-line playwright/no-skipped-test
  test.fixme(
    true,
    "Espera a que el servidor real de Equipos exista: endpoints de " +
      "API_EQUIPOS_v1.md §2-§6 en pie + seed de WP2 (8 equipos, 2 razones " +
      "sociales). Hoy solo existe el mock de I3 (ver equipos-errores.spec.js, " +
      "que sí corre)."
  );

  test("1-2: solicitante crea borrador, agrega equipos, EQUIPO_OCUPADO visible sin perder pasos previos", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/inventario");
    await expect(page.getByRole("heading", { name: /Inventario/i })).toBeVisible();

    await page.getByRole("link", { name: /Nuevo préstamo/i }).click();
    await page.getByLabel(/Motivo/i).fill(`Prueba E2E ${RUN_ID}`);
    await page.getByLabel(/Área/i).fill("Contenido");
    await page.getByRole("button", { name: /Siguiente/i }).click();

    // Dos equipos disponibles.
    await page.getByRole("button", { name: /Agregar equipo/i }).first().click();
    await page.getByRole("button", { name: /Agregar equipo/i }).first().click();

    // Un tercero ya ocupado (fixtures/equipos.json: equipment_id=1 vive en
    // el loan demo CE-0007, estado "prestado").
    await page.getByRole("button", { name: /Agregar equipo/i }).first().click();
    await expect(page.getByText(/ya esta en un prestamo abierto/i)).toBeVisible();
    // Los dos equipos agregados antes del error siguen en la lista — el
    // wizard no se cae ni pierde los pasos previos.
    await expect(page.getByTestId("equipos-seleccionados").locator("li")).toHaveCount(2);

    await context.close();
  });

  test("3-4: sube fotos y accesorios, confirmar con foto faltante da 409 TRANSICION_INVALIDA visible", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/nuevo"); // continúa el borrador (GET /loans/?estado=borrador&mios=1)

    // 2 fotos por equipo (frente y atrás) — solo la de "atrás" del segundo
    // equipo se deja pendiente a propósito, para el 409 del siguiente paso.
    const equipos = page.getByTestId("equipos-seleccionados").locator("li");
    for (let i = 0; i < 2; i++) {
      const item = equipos.nth(i);
      await item.getByLabel(/Foto de frente/i).setInputFiles({ name: `frente-${i}.png`, mimeType: "image/png", buffer: pngReal(400, 300) });
      if (i === 0) {
        await item.getByLabel(/Foto de atrás/i).setInputFiles({ name: `atras-${i}.png`, mimeType: "image/png", buffer: pngReal(400, 300) });
      }
    }
    await page.getByRole("button", { name: /Siguiente/i }).click();

    await page.getByLabel(/Firma de quien entrega/i).setInputFiles({ name: "firma-entrega.png", mimeType: "image/png", buffer: firmaPng() });
    await page.getByLabel(/Firma de quien recibe/i).setInputFiles({ name: "firma-recibe.png", mimeType: "image/png", buffer: firmaPng() });

    await page.getByRole("button", { name: /Confirmar préstamo/i }).click();
    await expect(page.getByText(/Faltan las fotos de atras de 1 equipo/i)).toBeVisible();

    await context.close();
  });

  test("5: completa la foto faltante, firma, confirma → folio + responsiva descargable", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/nuevo");
    const equipos = page.getByTestId("equipos-seleccionados").locator("li");
    await equipos.nth(1).getByLabel(/Foto de atrás/i).setInputFiles({ name: "atras-1.png", mimeType: "image/png", buffer: pngReal(400, 300) });
    await page.getByRole("button", { name: /Confirmar préstamo/i }).click();

    await expect(page.getByText(/CE-\d{4}/)).toBeVisible();
    await expect(page.getByRole("link", { name: /Descargar responsiva/i })).toBeVisible();

    await context.close();
  });

  test("6: la aprobadora autoriza la entrega — estado y autorización son dos badges distintos", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/aprobaciones");
    const fila = page.locator("tr", { hasText: `Prueba E2E ${RUN_ID}` });
    await fila.getByRole("button", { name: /Autorizar entrega/i }).click();

    await expect(fila.getByTestId("badge-estado")).toHaveText(/Prestado/i);
    await expect(fila.getByTestId("badge-autorizacion")).toHaveText(/Autorizada/i);

    await context.close();
  });

  test("7: registra la devolución — 2 fotos por equipo o no_devuelto+nota", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/activos");
    const fila = page.locator("tr", { hasText: `Prueba E2E ${RUN_ID}` });
    await fila.getByRole("button", { name: /Registrar devolución/i }).click();

    const equipos = page.getByTestId("equipos-devolucion").locator("li");
    await equipos.nth(0).getByLabel(/Foto de frente/i).setInputFiles({ name: "dev-frente-0.png", mimeType: "image/png", buffer: pngReal(400, 300) });
    await equipos.nth(0).getByLabel(/Foto de atrás/i).setInputFiles({ name: "dev-atras-0.png", mimeType: "image/png", buffer: pngReal(400, 300) });
    await equipos.nth(1).getByLabel(/No devuelto/i).check();
    await equipos.nth(1).getByLabel(/Nota/i).fill("Se quedó con el cliente por logística, se recoge la próxima semana.");

    await page.getByRole("button", { name: /Registrar devolución/i }).click();
    await expect(page.getByText(/Pendiente de confirmación/i)).toBeVisible();

    await context.close();
  });

  test("8: la aprobadora confirma con una decisión por equipo — 'danado' sin nota es 422", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/aprobaciones");
    const fila = page.locator("tr", { hasText: `Prueba E2E ${RUN_ID}` });
    await fila.getByRole("button", { name: /Confirmar devolución/i }).click();

    const decisiones = page.getByTestId("decisiones-devolucion").locator("li");
    await decisiones.nth(0).getByLabel(/Dañado/i).check();
    await page.getByRole("button", { name: /Guardar decisiones/i }).click();
    await expect(page.getByText(/nota.*obligatoria/i)).toBeVisible();

    await decisiones.nth(0).getByLabel(/Nota/i).fill("Lente rayado, requiere revisión.");
    await decisiones.nth(1).getByLabel(/Ok/i).check();
    await page.getByRole("button", { name: /Guardar decisiones/i }).click();

    await expect(page.getByTestId("badge-estado")).toHaveText(/Incompleto/i);

    await context.close();
  });

  test("9: cerrar-incidencia con nota obligatoria → completado y el equipo vuelve a activo", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password, baseURL: "" });
    const page = await context.newPage();

    await page.goto("/equipos/aprobaciones");
    const fila = page.locator("tr", { hasText: `Prueba E2E ${RUN_ID}` });
    await fila.getByRole("button", { name: /Cerrar incidencia/i }).click();
    await page.getByRole("button", { name: /Confirmar cierre/i }).click();
    await expect(page.getByText(/La nota es obligatoria/i)).toBeVisible();

    await page.getByLabel(/Nota/i).fill("Lente reemplazado, equipo probado y funcional.");
    await page.getByRole("button", { name: /Confirmar cierre/i }).click();
    await expect(fila.getByTestId("badge-estado")).toHaveText(/Completado/i);

    await context.close();
  });

  test("10: caso duro — entrega_autorizada:false nunca llega a completado", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: ADMIN.usuario, password: ADMIN.password, baseURL: "" });
    const page = await context.newPage();

    // Préstamo distinto, nunca autorizado, con devolución ya registrada.
    await page.goto("/equipos/aprobaciones");
    const fila = page.locator("tr", { hasText: /sin-autorizar/i });
    await fila.getByRole("button", { name: /Confirmar devolución/i }).click();
    const decisiones = page.getByTestId("decisiones-devolucion").locator("li");
    for (const d of await decisiones.all()) await d.getByLabel(/Ok/i).check();
    await page.getByRole("button", { name: /Guardar decisiones/i }).click();

    await expect(page.getByText(/no puede llegar a completado sin autorizacion/i)).toBeVisible();
    await expect(fila.getByTestId("badge-estado")).not.toHaveText(/Completado/i);

    await context.close();
  });
});
