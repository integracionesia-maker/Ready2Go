// @ts-check
import { test, expect, request as apiModule } from "@playwright/test";
import { contextoDe } from "./helpers/sesiones.mjs";
import { pngReal, firmaPng } from "./helpers/imagen.mjs";

// I8 lote 4 — el servidor real de Equipos ya existe (S0..S7 aterrizaron en
// BeniBranch) y WP1 (RBAC aditivo) también: este archivo se despierta
// (se quita el test.fixme) y sus selectores se ajustan a las 7 vistas
// reales de I4, verificadas a mano en I8 lotes 1-3. El flujo de negocio en
// sí (qué paso sigue a cuál, qué códigos de error esperar) no cambió — el
// contrato ya lo tenía bien.
//
// Dos ajustes de fondo, no solo de selector, encontrados al escribir esto:
//
// 1. La UI real tiene guardas del lado del cliente que el archivo
//    aspiracional no anticipaba: el botón "Confirmar préstamo" del paso 3
//    (Fotos) está DESHABILITADO mientras falte una sola foto de cualquier
//    equipo (`disabled={!loan.items.every(itemListo)}`), y
//    `ConfirmarDevolucionModal` ni siquiera pinta el formulario de
//    decisiones si `entrega_autorizada` es falso (solo una advertencia,
//    sin footer con botones). Ambas reglas SÍ existen en el servidor (409
//    TRANSICION_INVALIDA en los dos casos), pero un clic real nunca las
//    dispara porque el cliente ya las bloquea antes. Se verifica cada
//    regla por los dos lados: la guarda del cliente (UI) y el 409 del
//    servidor (llamada directa a la API con el `request` fixture,
//    exactamente el mismo body que mandaría el cliente si el botón no
//    estuviera deshabilitado).
//    Revisión 2 (firma-pendiente): `confirmar` ya NO exige ninguna firma —
//    el wizard de 3 pasos (Datos/Equipos/Fotos) ya no tiene un cuarto paso
//    de Firmas; ambas se completan después, cada una por su lado. El paso 1
//    ahora también pide los datos del Beneficiario (nombre/correo, texto
//    libre) antes de Área/Motivo.
// 2. El rol base `admin` NO tiene ningún permiso de `equipos_aprobacion`
//    (`rbac_catalog.py`: "Sin aprobacion de equipos") — un admin real
//    jamás puede autorizar entregas ni confirmar devoluciones. La persona
//    ADMIN de este archivo se usa para lo que el rol sí puede hacer
//    (solicitar préstamos, `equipos_prestamos:solicitar`): crea el
//    préstamo competidor de la carrera EQUIPO_OCUPADO y el préstamo nunca
//    autorizado del caso 10.

const SUPERADMIN_SEED_PASSWORD = process.env.E2E_SUPERADMIN_PASSWORD || "";
const RUN_ID = Date.now();

const SOLICITANTE = { usuario: `colaborador.equipos.${RUN_ID}`, password: `ColaboradorEquiposE2E${RUN_ID}!` };
const APROBADORA = { usuario: `melisa.equipos.${RUN_ID}`, password: `AprobadoraEquiposE2E${RUN_ID}!` };
const ADMIN = { usuario: `admin.equipos.${RUN_ID}`, password: `AdminEquiposE2E${RUN_ID}!` };
const MOTIVO = `Prueba E2E ${RUN_ID}`;
const MOTIVO_SIN_AUTORIZAR = `Prueba E2E sin-autorizar ${RUN_ID}`;

/** Crea un usuario ya con contraseña definitiva (sin el cambio forzado del
 * primer login) — el bootstrap lo resuelve una vez por su cuenta en vez de
 * dejárselo a cada test, igual que hace `auth.spec.js` con sus personas. */
async function crearUsuarioDefinitivo(request, { usuario, password, email, fullName, role }) {
  const creado = await request.post("/api/users/", {
    data: { username: usuario, email, full_name: fullName, role, password },
  });
  expect(creado.ok(), `crear ${usuario}: ${await creado.text()}`).toBeTruthy();
  const { id } = await creado.json();

  const propio = await apiModule.newContext();
  const login = await propio.post("/api/auth/login", { data: { identificador: usuario, password } });
  expect(login.ok()).toBeTruthy();
  const cambio = await propio.post("/api/auth/change-password", {
    data: { current_password: password, new_password: password },
  });
  expect(cambio.ok()).toBeTruthy();
  await propio.dispose();
  return id;
}

/** Fila de un préstamo dentro de UNA cola de Aprobaciones, identificada por
 * su `data-testid` — un mismo préstamo (p.ej. nunca autorizado + con
 * devolución ya registrada, o autorización pendiente + firma pendiente)
 * puede aparecer en más de una cola a la vez, así que matchear "li con este
 * texto" en toda la página es ambiguo. */
function filaEnSeccion(page, testId, texto) {
  return page.getByTestId(testId).locator("li", { hasText: texto });
}

test.describe.serial("Flujo completo de un préstamo de Equipos (extremo a extremo, servidor real)", () => {
  test.skip(!SUPERADMIN_SEED_PASSWORD, "Define E2E_SUPERADMIN_PASSWORD con la contraseña sembrada por seed_auth.py");

  let idAprobadora;
  let idEquipoOcupado; // id real del 3er equipo de la lista, usado en la carrera EQUIPO_OCUPADO

  test("bootstrap: superadmin crea las 3 personas reales y concede APROBADOR_EQUIPO por API", async ({ request }) => {
    const login = await request.post("/api/auth/login", {
      data: { identificador: "superadmin", password: SUPERADMIN_SEED_PASSWORD },
    });
    expect(login.ok(), await login.text()).toBeTruthy();

    await crearUsuarioDefinitivo(request, {
      usuario: SOLICITANTE.usuario,
      password: SOLICITANTE.password,
      email: `${SOLICITANTE.usuario}@test.com`,
      fullName: "Colaborador Equipos E2E",
      role: "colaborador_mkt",
    });
    idAprobadora = await crearUsuarioDefinitivo(request, {
      usuario: APROBADORA.usuario,
      password: APROBADORA.password,
      email: `${APROBADORA.usuario}@test.com`,
      fullName: "Melisa Aprobadora E2E",
      role: "colaborador_mkt",
    });
    await crearUsuarioDefinitivo(request, {
      usuario: ADMIN.usuario,
      password: ADMIN.password,
      email: `${ADMIN.usuario}@test.com`,
      fullName: "Admin Equipos E2E",
      role: "admin",
    });

    // Paquete aditivo (WP1/RBAC): un rol base nunca gana permisos de
    // aprobación por sí solo — melisa necesita el paquete concedido
    // explícitamente, exactamente como lo haría un superadmin real desde
    // /administracion cuando esa pantalla exista.
    const grant = await request.post(`/api/users/${idAprobadora}/roles`, {
      data: { role_name: "APROBADOR_EQUIPO" },
    });
    expect(grant.ok(), await grant.text()).toBeTruthy();
    const permisos = (await grant.json()).permisos_efectivos;
    expect(permisos.equipos_aprobacion).toEqual(
      expect.arrayContaining(["autorizar_entrega", "confirmar_devolucion", "cerrar_incidencia"])
    );

    // `firma_entrega` es identidad, no permiso (ver
    // routers/loans.py::subir_media): solo la titular del paquete SINGLETON
    // TITULAR_FIRMA_EQUIPO puede subirla, ni siquiera con APROBADOR_EQUIPO
    // alcanza. Sin este segundo grant, melisa dejaría de poder firmar en los
    // casos 9 y 10 de más abajo.
    const grantTitular = await request.post(`/api/users/${idAprobadora}/roles`, {
      data: { role_name: "TITULAR_FIRMA_EQUIPO" },
    });
    expect(grantTitular.ok(), await grantTitular.text()).toBeTruthy();

    // El 3er equipo disponible en el listado real (mismo orden que pinta
    // el picker del paso 2: GET /equipment/?disponible=true, sin params de
    // orden propios) es el que se usa para forzar EQUIPO_OCUPADO más
    // abajo — se resuelve aquí por id real, no por posición asumida.
    const equipos = await (await request.get("/api/equipment/?disponible=true&limit=200")).json();
    expect(equipos.items.length).toBeGreaterThanOrEqual(3);
    idEquipoOcupado = equipos.items[2].id;
  });

  test("1-2: solicitante crea un préstamo, agrega 2 equipos, un 3ro se marca EQUIPO_OCUPADO sin perder los 2 ya agregados", async ({ browser, request }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password });
    const page = await context.newPage();

    await page.goto("/equipos/inventario");
    await expect(page.getByRole("heading", { name: /Inventario/i })).toBeVisible();

    await page.goto("/equipos/nuevo");
    // Revisión 2: el paso 1 ahora pide Beneficiario (nombre + correo) ANTES
    // de Área/Motivo — desplaza los índices de `input[type="text"]`. Se
    // usa el mismo nombre del solicitante como beneficiario a propósito:
    // las aserciones de más abajo (Activos, Aprobaciones) buscan filas por
    // "Colaborador Equipos E2E", que ahora es el nombre del BENEFICIARIO,
    // no el de quien llena el formulario (son roles distintos desde este
    // cambio, aunque aquí coincidan en la misma persona).
    await page.locator('input[type="text"]').nth(0).fill("Colaborador Equipos E2E"); // Beneficiario · nombre
    await page.locator('input[type="email"]').fill(`${SOLICITANTE.usuario}@test.com`); // Beneficiario · correo
    await page.locator('input[type="text"]').nth(1).fill("Contenido"); // Área
    await page.locator("select.go-select").first().selectOption({ index: 1 }); // Marca
    await page.locator('input[type="text"]').nth(2).fill(MOTIVO); // Motivo
    await page.locator('input[type="date"]').fill("2026-09-15");
    await page.locator('button[type="submit"]').click();
    await page.waitForSelector("text=Equipos disponibles", { timeout: 10_000 });

    async function agregarPrimeroDisponible() {
      await page.getByRole("button", { name: "+ Agregar" }).first().click();
      const cargador = page.locator("select.go-select");
      if (await cargador.count()) await cargador.first().selectOption({ index: 1 });
      await page.getByRole("button", { name: "Confirmar" }).click();
      await page.waitForTimeout(600);
    }

    // Dos equipos disponibles se agregan sin problema.
    await agregarPrimeroDisponible();
    await agregarPrimeroDisponible();
    await expect(page.getByTestId("equipos-seleccionados").locator("li")).toHaveCount(2);

    // El tercero: se abre su selector de accesorios en la UI (todavía
    // aparece disponible, la lista no se refresca sola), pero ANTES de
    // confirmarlo alguien más (ADMIN, sesión real distinta) se lo lleva
    // primero por la API — la misma carrera que produciría dos pestañas
    // reales compitiendo por el mismo equipo.
    await page.getByRole("button", { name: "+ Agregar" }).first().click();
    const cargador3 = page.locator("select.go-select");
    if (await cargador3.count()) await cargador3.first().selectOption({ index: 1 });

    const loginAdmin = await request.post("/api/auth/login", {
      data: { identificador: ADMIN.usuario, password: ADMIN.password },
    });
    expect(loginAdmin.ok()).toBeTruthy();
    const prestamoCompetidor = await (
      await request.post("/api/loans/", {
        data: {
          responsable_user_id: (await loginAdmin.json()).user.id,
          responsable_nombre: "Admin Equipos E2E",
          responsable_email: `${ADMIN.usuario}@test.com`,
          area: "QA",
          empresa: "MERCASYSTEM SA DE CV",
          motivo: `Competidor EQUIPO_OCUPADO ${RUN_ID}`,
          fecha_regreso_esperada: "2026-09-20",
        },
      })
    ).json();
    const seLoLlevo = await request.post(`/api/loans/${prestamoCompetidor.id}/items`, {
      data: { equipment_id: idEquipoOcupado, accesorios_seleccionados: [], accesorios_otros: null, cargador_con: "empresa" },
    });
    expect(seLoLlevo.ok(), await seLoLlevo.text()).toBeTruthy();

    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page.getByText(/ya no está disponible/i)).toBeVisible();
    // Los 2 equipos agregados antes de la carrera siguen ahí — el wizard
    // no se cae ni pierde los pasos previos.
    await expect(page.getByTestId("equipos-seleccionados").locator("li")).toHaveCount(2);

    await context.close();
  });

  test("3: sube fotos y confirma → folio real; el 409 TRANSICION_INVALIDA por foto faltante se verifica en ambos lados", async ({ browser, request }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password });
    const page = await context.newPage();

    await page.goto("/equipos/nuevo"); // continúa el borrador (GET /loans/?estado=borrador&mios=1)
    await page.getByRole("button", { name: "Continuar borrador" }).click({ timeout: 10_000 });
    await page.waitForSelector('button:has-text("Elegir archivo")', { timeout: 10_000 });

    // Lado del cliente: mientras falte UNA foto de CUALQUIER equipo,
    // "Confirmar préstamo" queda deshabilitado — no hay forma de confirmar
    // con un renglón a medias desde la UI. Revisión 2: ya no hay paso de
    // Firmas, así que este es el único botón de avance del paso 3.
    const confirmarPrestamo = page.getByRole("button", { name: "Confirmar préstamo" });
    await expect(confirmarPrestamo).toBeDisabled();

    const totalBotones = await page.getByRole("button", { name: "Elegir archivo" }).count();
    for (let i = 0; i < totalBotones; i++) {
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.getByRole("button", { name: "Elegir archivo" }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles({ name: `foto-${i}.png`, mimeType: "image/png", buffer: pngReal(400, 300) });
      await page.waitForTimeout(700);
    }
    await expect(confirmarPrestamo).toBeEnabled();

    // Lado del servidor: el mismo 409 que el cliente ya no deja disparar
    // por clic. El borrador de este test ya quedó completo (todas las
    // fotos subidas) para no interferir con el folio que 6-9 necesitan
    // intacto, así que la regla se reproduce contra un préstamo nuevo,
    // mínimo, creado solo para esta verificación puntual — a quién
    // pertenece no importa, se reusa la sesión de superadmin (ya definida
    // arriba) en vez de gastar un login extra en el solicitante.
    const loginSuperadmin = await request.post("/api/auth/login", {
      data: { identificador: "superadmin", password: SUPERADMIN_SEED_PASSWORD },
    });
    const superadminId = (await loginSuperadmin.json()).user.id;
    const equiposLibres = await (await request.get("/api/equipment/?disponible=true&limit=200")).json();
    const prestamoIncompleto = await (
      await request.post("/api/loans/", {
        data: {
          responsable_user_id: superadminId,
          responsable_nombre: "Superadministrador",
          responsable_email: "superadmin@grupo-ortiz.com",
          area: "QA",
          empresa: "MERCASYSTEM SA DE CV",
          motivo: `Foto faltante ${RUN_ID}`,
          fecha_regreso_esperada: "2026-09-20",
        },
      })
    ).json();
    await request.post(`/api/loans/${prestamoIncompleto.id}/items`, {
      data: { equipment_id: equiposLibres.items[0].id, accesorios_seleccionados: [], accesorios_otros: null, cargador_con: "responsable" },
    });
    const confirmarSinFotos = await request.post(`/api/loans/${prestamoIncompleto.id}/confirmar`);
    expect(confirmarSinFotos.status()).toBe(409);
    const cuerpoError = await confirmarSinFotos.json();
    expect(cuerpoError.codigo).toBe("TRANSICION_INVALIDA");
    expect(cuerpoError.detail).toMatch(/Faltan las fotos de frente de 1 equipo/i);
    // Revisión 2: `confirmar` ya no exige ninguna firma (ambas quedan
    // pendientes después, cada una por su lado) — solo las fotos bloquean.

    // De vuelta al flujo real: confirmar directo, sin firmas en el wizard.
    await confirmarPrestamo.click();
    await page.waitForURL(/\/equipos\/prestamo\//, { timeout: 15_000 });
    await expect(page.getByText(/CE-\d{4,}/)).toBeVisible();
    await expect(page.getByRole("button", { name: /Ver responsiva/i })).toBeVisible();

    await context.close();
  });

  test("6: la aprobadora autoriza la entrega — estado y autorización son dos badges distintos", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password });
    const page = await context.newPage();

    await page.goto("/equipos/aprobaciones");
    // Revisión 2: este préstamo también aparece en "Firmas pendientes" (le
    // falta firma_entrega, la de la propia aprobadora) — se escopa a
    // "Autorizaciones de entrega" explícitamente para no ser ambiguo.
    const fila = filaEnSeccion(page, "cola-autorizaciones", MOTIVO);
    await expect(fila).toBeVisible();
    // El folio se captura ANTES de autorizar: la fila sale de esta cola en
    // cuanto entrega_autorizada pasa a true (deja de matchear el filtro de
    // "Autorizaciones de entrega pendientes"), así que después del clic el
    // locator queda apuntando a un elemento que ya no está en el DOM.
    const folio = (await fila.locator("a.font-mono").textContent()).trim();
    await fila.getByRole("button", { name: /Autorizar entrega/i }).click();
    await expect(page.getByText(/Entrega autorizada/i)).toBeVisible();

    await page.goto(`/equipos/prestamo/${folio}`);
    await expect(page.getByTestId("badge-estado")).toHaveText(/Prestado/i);
    await expect(page.getByTestId("badge-autorizacion")).toHaveText(/Entrega autorizada/i);

    await context.close();
  });

  test("7: el solicitante registra la devolución — 2 fotos en un equipo, no_devuelto+nota en el otro", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: SOLICITANTE.usuario, password: SOLICITANTE.password });
    const page = await context.newPage();

    await page.goto("/equipos/activos");
    const fila = page.locator("tbody tr", { hasText: "Colaborador Equipos E2E" });
    await expect(fila).toBeVisible({ timeout: 10_000 });
    await fila.getByRole("button", { name: /Registrar devolución/i }).click();

    const items = page.getByTestId("equipos-devolucion").locator("li");
    await expect(items).toHaveCount(2);

    // Sube ambas fotos del primer equipo.
    for (let i = 0; i < 2; i++) {
      const fileChooserPromise = page.waitForEvent("filechooser");
      await items.nth(0).getByRole("button", { name: "Elegir archivo" }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles({ name: `dev-${i}.png`, mimeType: "image/png", buffer: pngReal(400, 300) });
      await page.waitForTimeout(700);
    }

    await items.nth(1).locator('input[type="checkbox"]').check();
    await items.nth(1).locator("textarea").fill("Se quedó con el cliente por logística, se recoge la próxima semana.");

    // El botón del pie del modal repite el texto del botón que lo abrió
    // ("Registrar devolución") — se escopa al diálogo para no ambigüar.
    await page.getByRole("dialog").getByRole("button", { name: "Registrar devolución" }).click();
    await expect(page.getByText(/Devolución registrada/i)).toBeVisible();

    await context.close();
  });

  test("8: la aprobadora confirma con una decisión por equipo — 'Dañado' sin nota no deja enviar, con nota sí", async ({ browser }) => {
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password });
    const page = await context.newPage();

    await page.goto("/equipos/aprobaciones");
    // "Devoluciones por confirmar" solo pinta responsable, no motivo (a
    // diferencia de "Autorizaciones de entrega") — se matchea por nombre,
    // escopado a su sección.
    const fila = filaEnSeccion(page, "cola-devoluciones", "Colaborador Equipos E2E");
    await fila.getByRole("button", { name: /Confirmar devolución/i }).click();

    const decisiones = page.getByTestId("decisiones-devolucion").locator("li");
    await expect(decisiones).toHaveCount(2);

    // "Confirmar" (footer del modal) es substring de "Confirmar devolución"
    // (el botón que abrió el modal, todavía en el DOM detrás) — se escopa
    // al diálogo, exact:true de más, para no ambigüar entre los dos.
    const dialogo = page.getByRole("dialog");
    await decisiones.nth(0).locator("select").selectOption("danado");
    await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(page.getByText(/Falta la nota en uno o más equipos/i)).toBeVisible();

    await decisiones.nth(0).locator("textarea").fill("Lente rayado, requiere revisión.");
    // El segundo ya nace en "ok" por default — no hace falta tocarlo.
    await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(page.getByText(/Devolución confirmada/i)).toBeVisible();

    await context.close();
  });

  test("9: cerrar-incidencia con nota obligatoria → completado y el equipo vuelve a activo", async ({ browser, request }) => {
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password });
    const page = await context.newPage();

    // Revisión 2: `cerrar-incidencia` es una de las dos únicas rutas a
    // `completado` y `firmas_completas` la bloquea igual que a
    // `confirmar-devolucion` — este préstamo llegó hasta aquí sin ninguna
    // firma (nunca se piden en el wizard). Se completan las dos por API
    // antes de cerrar la incidencia; el rol de la aprobadora (`colaborador_mkt`
    // + paquete `APROBADOR_EQUIPO`) ya cubre ambos permisos de `/media`
    // (`solicitar` para `firma_responsable`, `autorizar_entrega` para
    // `firma_entrega`), así que la misma sesión alcanza para las dos.
    const loans = await (await context.request.get("/api/loans/?limit=200")).json();
    const loanIncidencia = loans.items.find((l) => l.motivo === MOTIVO);
    for (const kind of ["firma_entrega", "firma_responsable"]) {
      const subida = await context.request.post(`/api/loans/${loanIncidencia.id}/media`, {
        multipart: { file: { name: `${kind}.png`, mimeType: "image/png", buffer: Buffer.from(firmaPng()) }, kind },
      });
      expect(subida.ok(), await subida.text()).toBeTruthy();
    }

    await page.goto("/equipos/aprobaciones");
    // "Incidencias abiertas" tampoco pinta motivo, solo responsable.
    const fila = filaEnSeccion(page, "cola-incidencias", "Colaborador Equipos E2E");
    await expect(fila).toBeVisible();
    await fila.getByRole("button", { name: /Cerrar incidencia/i }).click();

    // El botón del pie del modal repite el mismo texto que el botón que lo
    // abrió ("Cerrar incidencia") — se escopa al `role="dialog"` para no
    // ambigüar entre los dos.
    const dialogo = page.getByRole("dialog");
    await dialogo.getByRole("button", { name: /Cerrar incidencia/i }).click();
    await expect(page.getByText(/La nota es obligatoria/i)).toBeVisible();

    await dialogo.locator("textarea").fill("Lente reemplazado, equipo probado y funcional.");
    await dialogo.getByRole("button", { name: /Cerrar incidencia/i }).click();
    await expect(page.getByText(/Incidencia cerrada/i)).toBeVisible();

    await context.close();
  });

  test("10: caso duro — entrega_autorizada:false nunca llega a completado (cliente Y servidor)", async ({ browser, request }) => {
    // Préstamo distinto, creado por ADMIN (rol sin permiso de aprobación,
    // usado aquí solo como "solicitante" alterno), nunca autorizado, con
    // devolución ya registrada.
    const loginAdmin = await request.post("/api/auth/login", {
      data: { identificador: ADMIN.usuario, password: ADMIN.password },
    });
    const adminId = (await loginAdmin.json()).user.id;
    const equiposLibres = await (await request.get("/api/equipment/?disponible=true&limit=200")).json();
    expect(equiposLibres.items.length).toBeGreaterThan(0);

    const prestamo = await (
      await request.post("/api/loans/", {
        data: {
          responsable_user_id: adminId,
          responsable_nombre: "Admin Equipos E2E",
          responsable_email: `${ADMIN.usuario}@test.com`,
          area: "QA",
          empresa: "MERCASYSTEM SA DE CV",
          motivo: MOTIVO_SIN_AUTORIZAR,
          fecha_regreso_esperada: "2026-09-20",
        },
      })
    ).json();
    const conItem = await (
      await request.post(`/api/loans/${prestamo.id}/items`, {
        data: { equipment_id: equiposLibres.items[0].id, accesorios_seleccionados: [], accesorios_otros: null, cargador_con: "responsable" },
      })
    ).json();
    const idItemSinAutorizar = conItem.items[0].id;

    for (const kind of ["foto_entrega_frente", "foto_entrega_atras"]) {
      await request.post(`/api/loans/${prestamo.id}/media`, {
        multipart: { file: { name: `${kind}.png`, mimeType: "image/png", buffer: Buffer.from(pngReal(300, 300)) }, kind, loan_item_id: String(idItemSinAutorizar) },
      });
    }
    // Revisión 2: `confirmar` ya no exige ninguna firma — este préstamo llega
    // a `prestado` sin firma_entrega ni firma_responsable. Lo que este test
    // verifica es exclusivamente el candado de `entrega_autorizada`, que
    // corre antes que el de firmas completas en `_exigir_autorizacion` /
    // `approvals.py`, así que da igual que las firmas sigan pendientes.
    await request.post(`/api/loans/${prestamo.id}/confirmar`);
    for (const kind of ["foto_dev_frente", "foto_dev_atras"]) {
      await request.post(`/api/loans/${prestamo.id}/media`, {
        multipart: { file: { name: `${kind}.png`, mimeType: "image/png", buffer: Buffer.from(pngReal(300, 300)) }, kind, loan_item_id: String(idItemSinAutorizar) },
      });
    }
    await request.post(`/api/loans/${prestamo.id}/devolucion`, {
      data: { items: [{ loan_item_id: idItemSinAutorizar, no_devuelto: false, nota_devolucion: null }] },
    });

    // Servidor: confirmar-devolucion sin autorizar entrega es 409, siempre
    // — se prueba con la sesión de la aprobadora (ADMIN no tiene ningún
    // permiso de equipos_aprobacion, así que con su sesión esto daría 403
    // antes de llegar a la regla de negocio que se quiere verificar aquí).
    await request.post("/api/auth/login", { data: { identificador: APROBADORA.usuario, password: APROBADORA.password } });
    const confirmarDirecto = await request.post(`/api/loans/${prestamo.id}/confirmar-devolucion`, {
      data: { decisiones: [{ loan_item_id: idItemSinAutorizar, decision: "ok", nota: null }] },
    });
    expect(confirmarDirecto.status()).toBe(409);
    expect((await confirmarDirecto.json()).codigo).toBe("TRANSICION_INVALIDA");

    // Cliente: la aprobadora ni siquiera ve el formulario de decisiones —
    // solo la advertencia — así que tampoco puede llegar a completado por
    // un clic real.
    const context = await contextoDe(browser, { usuario: APROBADORA.usuario, password: APROBADORA.password });
    const page = await context.newPage();
    await page.goto("/equipos/aprobaciones");
    // Este préstamo aparece en DOS colas a la vez (nunca autorizado +
    // devolución ya registrada) — se escopa a "Devoluciones por confirmar"
    // explícitamente, no basta con el nombre del responsable.
    const fila = filaEnSeccion(page, "cola-devoluciones", "Admin Equipos E2E");
    await expect(fila).toBeVisible();
    await fila.getByRole("button", { name: /Confirmar devolución/i }).click();
    await expect(page.getByText(/todavía no tiene autorizada su entrega/i)).toBeVisible();
    // exact:true — sin él, "Confirmar" matchea por substring el botón
    // "Confirmar devolución" que abrió el modal (sigue en el DOM detrás).
    await expect(page.getByRole("dialog").getByRole("button", { name: "Confirmar", exact: true })).toHaveCount(0);

    await context.close();
  });
});
