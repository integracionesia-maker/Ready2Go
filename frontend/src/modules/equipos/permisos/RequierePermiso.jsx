import { Navigate } from "react-router-dom";
import { usePermisos } from "./usePermisos";

/**
 * Dos modos, uno por uso:
 * - `modo="ui"` (default): envoltorio — renderiza `children` o `fallback`
 *   (nada, por defecto). Para botones y secciones.
 * - `modo="ruta"`: guardia de ruta — redirige a `/403` si no puede. No
 *   duplica `ProtectedRoute` de Presupuestos (ese resuelve sesión/rol); este
 *   resuelve `(modulo, accion)` sobre una sesión que ya existe.
 *
 * La UI SOLO pinta. Esconder un botón no es seguridad, es cortesía — cada
 * endpoint valida por su cuenta.
 */
export default function RequierePermiso({ modulo, accion, modo = "ui", children, fallback = null, userOverride }) {
  const { puede } = usePermisos(userOverride);
  const permitido = puede(modulo, accion);

  if (modo === "ruta") {
    return permitido ? children : <Navigate to="/403" replace />;
  }

  return permitido ? children : fallback;
}
