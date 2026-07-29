// @ts-check
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Prueba de igualdad del lado del cliente (pedida explícitamente por el
// _nota de prestamo_demo.json: "hay una prueba de igualdad en cada lado").
// Si el contrato cambia arriba sin avisar, esta prueba se pone roja el mismo
// día en vez de descubrirse en el e2e real de Equipos tres semanas después.
//
// No necesita navegador: es una comparación de archivos en disco. Vive en
// e2e/ (no en src/) porque es infraestructura de verificación, no código de
// producción, y así corre junto al resto de la suite con el mismo comando.

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONTRATO_DIR = path.join(__dirname, "..", "..", "docs", "contratos");
const MOCK_DIR = path.join(__dirname, "..", "src", "modules", "equipos", "api", "mock", "fixtures");

const PARES = [
  { contrato: path.join(CONTRATO_DIR, "fixtures", "empresas.json"), mock: path.join(MOCK_DIR, "empresas.json") },
  { contrato: path.join(CONTRATO_DIR, "fixtures", "equipos.json"), mock: path.join(MOCK_DIR, "equipos.json") },
  { contrato: path.join(CONTRATO_DIR, "fixtures", "errores.json"), mock: path.join(MOCK_DIR, "errores.json") },
  { contrato: path.join(CONTRATO_DIR, "fixtures", "prestamo_demo.json"), mock: path.join(MOCK_DIR, "prestamo_demo.json") },
  { contrato: path.join(CONTRATO_DIR, "permisos_catalogo.json"), mock: path.join(MOCK_DIR, "permisos_catalogo.json") },
  { contrato: path.join(CONTRATO_DIR, "auth_me.json"), mock: path.join(MOCK_DIR, "auth_me.json") },
];

test.describe("Fixtures del mock == contrato congelado (copia literal)", () => {
  for (const { contrato, mock } of PARES) {
    const nombre = path.basename(contrato);

    test(`${nombre}: la copia de mock/fixtures/ es igual, campo por campo, a docs/contratos/`, () => {
      expect(fs.existsSync(contrato), `No existe el original: ${contrato}`).toBe(true);
      expect(fs.existsSync(mock), `No existe la copia: ${mock}`).toBe(true);

      const original = JSON.parse(fs.readFileSync(contrato, "utf-8"));
      const copia = JSON.parse(fs.readFileSync(mock, "utf-8"));

      expect(copia).toEqual(original);
    });
  }
});
