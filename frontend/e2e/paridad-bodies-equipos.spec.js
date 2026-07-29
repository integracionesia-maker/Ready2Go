// @ts-check
import { test, expect } from "@playwright/test";

/**
 * I8 lote 1.4 — paridad de los bodies de escritura del módulo de Equipos.
 *
 * `contrato-fixtures.spec.js` (I3) compara fixtures de LECTURA. Nada cubría
 * lo que el cliente ENVÍA, y por eso el bug de `/devolucion` (camelCase vs
 * snake_case, I8 lote 1.1) sobrevivió a 48/48 pasadas del mock.
 *
 * Cada endpoint de escritura se llama directo (`real/*.js`, sin pasar por el
 * dispatcher mock/real) con `window.fetch` interceptado en el propio
 * navegador — nunca toca la red ni un servidor real. Las llaves esperadas
 * son una copia de lectura de `backend/app/schemas_loans.py` y
 * `schemas_equipment.py` (solo lectura, permitida): si alguien vuelve a
 * mandar una llave en camelCase o inventa un campo, esta prueba las nota
 * como "extra" o "faltante" contra esa copia y falla.
 *
 * Los inputs de cada llamada son el mismo objeto que arma hoy la página o el
 * modal real (`NuevoPrestamoPage.jsx`, `RegistrarDevolucionModal.jsx`, etc.):
 * esta prueba fija esa forma en un lugar barato de correr (nunca navega, no
 * necesita sesión ni servidor), no reemplaza que `equipos-flujo-completo.spec.js`
 * (I8 lote 4) ejercite las páginas de verdad end-to-end.
 */

// ── Llaves aceptadas por cada schema real (fuente: backend/app/schemas_loans.py
//    y schemas_equipment.py, leídos el 2026-07-29 para I8) ──────────────────
const LOAN_CREATE = [
  "responsable_user_id",
  "responsable_nombre",
  "responsable_email",
  "area",
  "empresa",
  "motivo",
  "notas_responsiva",
  "fecha_entrega",
  "fecha_regreso_esperada",
];
const LOAN_ITEM_CREATE = ["equipment_id", "accesorios_seleccionados", "accesorios_otros", "cargador_con"];
const CANCELAR_REQUEST = ["motivo"];
const DEVOLUCION_REQUEST = ["fecha_regreso_real", "items"];
const DEVOLUCION_ITEM = ["loan_item_id", "no_devuelto", "nota_devolucion"];
const CONFIRMAR_DEVOLUCION_REQUEST = ["decisiones"];
const DECISION_ITEM = ["loan_item_id", "decision", "nota"];
const CERRAR_INCIDENCIA_REQUEST = ["nota"];
const BAJA_REQUEST = ["motivo"];

/** Corre `fn` con `window.fetch` capturado (nunca llega a la red) y regresa
 * el body ya parseado de JSON, o `null` si la llamada no mandó body. */
async function capturarBody(page, ruta, llamada) {
  return page.evaluate(
    async ({ ruta, llamada }) => {
      let cuerpo;
      let huboBody = false;
      const fetchOriginal = window.fetch;
      window.fetch = async (_url, opts) => {
        huboBody = Boolean(opts && "body" in opts && opts.body != null);
        cuerpo = huboBody ? JSON.parse(opts.body) : null;
        return new window.Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      };
      try {
        const mod = await import(/* @vite-ignore */ ruta);
        // eslint-disable-next-line no-new-func
        await new Function("mod", `return (${llamada})(mod)`)(mod);
      } finally {
        window.fetch = fetchOriginal;
      }
      return { cuerpo, huboBody };
    },
    { ruta, llamada }
  );
}

function clavesExtra(recibidas, esperadas) {
  return recibidas.filter((k) => !esperadas.includes(k));
}
function clavesConNombreSospechoso(recibidas) {
  // Detector barato de camelCase: cualquier llave con una mayúscula adentro
  // es, por convención de este proyecto, una violación (el contrato entero
  // es snake_case).
  return recibidas.filter((k) => /[A-Z]/.test(k));
}

test.describe("Paridad de bodies de escritura — Equipos vs schemas reales (I8 lote 1.4)", () => {
  test("POST /loans/ (createLoan) — LoanCreate", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.createLoan({
        responsable_user_id: 1, responsable_nombre: "Ana", responsable_email: "a@x.com",
        area: "Contenido", empresa: "MERCASYSTEM", motivo: "Prueba",
        fecha_regreso_esperada: "2026-08-01", notas_responsiva: null,
      })`
    );
    expect(clavesConNombreSospechoso(Object.keys(cuerpo))).toEqual([]);
    expect(clavesExtra(Object.keys(cuerpo), LOAN_CREATE)).toEqual([]);
  });

  test("POST /loans/{id}/items (addLoanItem) — LoanItemCreate", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.addLoanItem(7, { equipmentId: 1, accesoriosSeleccionados: ["Funda"], accesoriosOtros: null, cargadorCon: "responsable" })`
    );
    expect(Object.keys(cuerpo).sort()).toEqual([...LOAN_ITEM_CREATE].sort());
    expect(clavesConNombreSospechoso(Object.keys(cuerpo))).toEqual([]);
  });

  test("POST /loans/{id}/cancelar (cancelLoan) — CancelarRequest, y manda body (bug I8 encontrado y corregido)", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo, huboBody } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.cancelLoan(7)`
    );
    expect(huboBody).toBe(true);
    expect(Object.keys(cuerpo).sort()).toEqual([...CANCELAR_REQUEST].sort());
  });

  test("POST /loans/{id}/devolucion (returnLoan) — DevolucionRequest + DevolucionItem", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.returnLoan(7, { decisionesPorItem: [{ loan_item_id: 11, no_devuelto: false, nota_devolucion: null }] })`
    );
    expect(clavesExtra(Object.keys(cuerpo), DEVOLUCION_REQUEST)).toEqual([]);
    expect(cuerpo.items.length).toBe(1);
    const clavesItem = Object.keys(cuerpo.items[0]);
    expect(clavesConNombreSospechoso(clavesItem)).toEqual([]);
    expect(clavesExtra(clavesItem, DEVOLUCION_ITEM)).toEqual([]);
    expect(clavesItem).toContain("loan_item_id");
  });

  test("POST /loans/{id}/confirmar-devolucion — ConfirmarDevolucionRequest + DecisionItem", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.confirmReturnDecision(7, [{ loan_item_id: 11, decision: "ok", nota: null }])`
    );
    expect(Object.keys(cuerpo)).toEqual(CONFIRMAR_DEVOLUCION_REQUEST);
    const clavesItem = Object.keys(cuerpo.decisiones[0]);
    expect(clavesConNombreSospechoso(clavesItem)).toEqual([]);
    expect(clavesExtra(clavesItem, DECISION_ITEM)).toEqual([]);
  });

  test("POST /loans/{id}/cerrar-incidencia — CerrarIncidenciaRequest", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.closeIncident(7, "Se repara el cable.")`
    );
    expect(Object.keys(cuerpo)).toEqual(CERRAR_INCIDENCIA_REQUEST);
  });

  test("POST /loans/{id}/autorizar-entrega — NO lleva body", async ({ page }) => {
    await page.goto("/login");
    const { huboBody } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.authorizeDelivery(7)`
    );
    expect(huboBody).toBe(false);
  });

  test("POST /loans/{id}/confirmar — NO lleva body", async ({ page }) => {
    await page.goto("/login");
    const { huboBody } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/loans.js",
      `(mod) => mod.confirmLoan(7)`
    );
    expect(huboBody).toBe(false);
  });

  test("POST /equipment/{id}/baja (dischargeEquipment) — BajaRequest, y manda body (mismo bug de I8 en Inventario)", async ({ page }) => {
    await page.goto("/login");
    const { cuerpo, huboBody } = await capturarBody(
      page,
      "/src/modules/equipos/api/real/equipment.js",
      `(mod) => mod.dischargeEquipment(1)`
    );
    expect(huboBody).toBe(true);
    expect(Object.keys(cuerpo).sort()).toEqual([...BAJA_REQUEST].sort());
  });

  test("POST /loans/{id}/media (uploadMedia) — multipart con los 3 campos del contrato, sin Content-Type a mano", async ({ page }) => {
    await page.goto("/login");
    const resultado = await page.evaluate(async () => {
      let campos = null;
      let tipoContenidoForzado = null;
      const fetchOriginal = window.fetch;
      window.fetch = async (_url, opts) => {
        tipoContenidoForzado = opts?.headers && "Content-Type" in opts.headers ? opts.headers["Content-Type"] : null;
        campos = opts?.body instanceof FormData ? [...opts.body.keys()] : null;
        return new window.Response(JSON.stringify({ id: 1, kind: "foto_entrega_frente", sha256: "x" }), { status: 201 });
      };
      try {
        const mod = await import(/* @vite-ignore */ "/src/modules/equipos/api/real/media.js");
        const archivo = new File([new Uint8Array([1, 2, 3])], "foto.jpg", { type: "image/jpeg" });
        await mod.uploadMedia(7, { file: archivo, kind: "foto_entrega_frente", loanItemId: 11 });
      } finally {
        window.fetch = fetchOriginal;
      }
      return { campos, tipoContenidoForzado };
    });
    expect(resultado.tipoContenidoForzado).toBeNull();
    expect(resultado.campos?.sort()).toEqual(["file", "kind", "loan_item_id"].sort());
  });
});
