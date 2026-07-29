import { ApiError } from "@/api";
import errores from "./fixtures/errores.json";

/** Lanza el ApiError exacto que documenta fixtures/errores.json para `codigo`. */
export function throwFixtureError(codigo) {
  const entry = errores[codigo];
  throw new ApiError(entry.body.detail, {
    status: entry.http,
    codigo: entry.body.codigo,
    detail: entry.body.detail,
  });
}

export function throwNotFound(mensaje = "No encontrado.") {
  throw new ApiError(mensaje, { status: 404, codigo: "NO_ENCONTRADO", detail: mensaje });
}
