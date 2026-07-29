// Semilla de demo reusable (B-I06). Antes vivía SOLO dentro de
// pantallas.spec.js (1 creador + 1 marca + 1 ticket, hardcodeado) — sacado
// aquí, genérico y parametrizable, para que cualquier spec pueda sembrar
// datos que SÍ pinten (R-I04: seed_demo_year.py deja 355 tickets pendientes
// y ciclos en cero, el dashboard sale en "Sin datos" con la DB "llena").
//
// Solo por la API real (clics reales sobre la UI de Administración/Nuevo
// Ticket, que disparan fetch reales) — nunca una escritura directa a
// presupuesto.db ni un cambio en backend/. Un ticket aprobado por SQL no
// actualiza el ciclo y se vuelve a caer en R-I04 por otro camino.
//
// Idempotente por sufijo: cada corrida usa un sufijo distinto en los
// nombres (default `Date.now()`), así que correrlo dos veces no choca con
// datos de una corrida anterior ni con validación de unicidad.
//
// Asume que `page` YA tiene una sesión con permiso para crear
// creadores/marcas/tickets (admin o superadmin) — el login y el cambio de
// contraseña forzada quedan a cargo de quien llama (varían: auth.spec.js
// rota la contraseña del superadmin, otros specs no).

function ticketFileBuffer(sufijo, indice) {
  return Buffer.from(`%PDF-1.4\n% comprobante de prueba sembrar-demo ${sufijo}-${indice}\n`);
}

async function crearCreador(page, nombre, montoCiclo, ciclo) {
  await page.click('button:has-text("Nuevo Creador")');
  const modal = page.locator(".fixed.inset-0");
  await modal.locator('input[type="text"]').fill(nombre);
  await modal.locator('input[type="number"]').fill(String(montoCiclo));
  await modal.locator("select").selectOption(ciclo);
  await modal.locator('button:has-text("Crear")').click();
  await modal.waitFor({ state: "detached" }).catch(() => {});
  await page.locator("tr", { hasText: nombre }).first().waitFor({ state: "visible" });
}

async function crearMarca(page, nombre, prioridad) {
  await page.click('button:has-text("Nueva Marca")');
  const modal = page.locator(".fixed.inset-0");
  await modal.locator('input[type="text"]').fill(nombre);
  await modal.locator("select").selectOption(prioridad);
  await modal.locator('button:has-text("Crear")').click();
  await modal.waitFor({ state: "detached" }).catch(() => {});
  await page.locator("tr", { hasText: nombre }).first().waitFor({ state: "visible" });
}

async function crearTicket(page, { creatorName, brandName, monto, sufijo, indice }) {
  await page.click('button:has-text("Nuevo Ticket")');
  const modal = page.locator(".fixed.inset-0");
  // La opción de creador lleva un sufijo "— Restante del ciclo: $X" (no es
  // solo el nombre): selectOption({label}) exacto no la encuentra — se
  // ubica por texto parcial y se selecciona por su value real.
  const creatorOptionValue = await modal
    .locator("select")
    .nth(0)
    .locator("option", { hasText: creatorName })
    .getAttribute("value");
  await modal.locator("select").nth(0).selectOption(creatorOptionValue);
  await modal.locator("select").nth(1).selectOption({ label: brandName });
  await modal.locator('input[type="number"]').fill(String(monto));
  await modal.locator('input[type="file"]').setInputFiles({
    name: `comprobante-demo-${sufijo}-${indice}.pdf`,
    mimeType: "application/pdf",
    buffer: ticketFileBuffer(sufijo, indice),
  });
  await modal.locator('button:has-text("Registrar Ticket")').click();
  await modal.getByText("Ticket registrado exitosamente.").waitFor({ state: "visible" });
  await modal.waitFor({ state: "detached" }).catch(() => {});
}

/**
 * Siembra `numCreadores` creadores + `numMarcas` marcas + `numTickets`
 * tickets (repartidos round-robin entre los creadores/marcas creados),
 * todo vía la API real. Los tickets nacen de quien esté logueado en `page`
 * — si es admin/superadmin, se auto-aprueban y sí actualizan el ciclo.
 *
 * Devuelve los nombres reales creados, por si el spec que llama necesita
 * referenciarlos (buscar una fila, filtrar una tabla, etc.).
 */
export async function sembrarDemo(page, {
  sufijo = Date.now(),
  numCreadores = 1,
  numMarcas = 1,
  numTickets = 1,
  montoCiclo = 5000,
  cicloPeriodo = "mensual",
  prioridadMarca = "alta",
  montoTicket = 750,
} = {}) {
  const creadores = [];
  const marcas = [];

  await page.goto("/administracion");
  await page.click('button:has-text("Creadores")');
  for (let i = 0; i < numCreadores; i++) {
    const nombre = `Creador Demo ${sufijo}-${i}`;
    await crearCreador(page, nombre, montoCiclo, cicloPeriodo);
    creadores.push(nombre);
  }

  await page.click('button:has-text("Marcas")');
  for (let i = 0; i < numMarcas; i++) {
    const nombre = `Marca Demo ${sufijo}-${i}`;
    await crearMarca(page, nombre, prioridadMarca);
    marcas.push(nombre);
  }

  await page.goto("/");
  for (let i = 0; i < numTickets; i++) {
    const creatorName = creadores[i % creadores.length];
    const brandName = marcas[i % marcas.length];
    await crearTicket(page, { creatorName, brandName, monto: montoTicket, sufijo, indice: i });
  }

  return { creadores, marcas };
}
