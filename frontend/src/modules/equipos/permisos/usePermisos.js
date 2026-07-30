import { useMemo } from "react";
import { useAuth } from "@/context/AuthContext";
import { accionExiste } from "./catalogo";

// Dedupe por clave: cada (modulo, accion) desconocida se avisa una sola vez
// por sesión de página, no en cada render/click.
const advertidas = new Set();

function advertirClaveDesconocida(modulo, accion) {
  if (!import.meta.env.DEV) return;
  const key = `${modulo}:${accion}`;
  if (advertidas.has(key)) return;
  advertidas.add(key);
  // eslint-disable-next-line no-console
  console.warn(`[permisos] clave desconocida: ${key}`);
}

/**
 * Lee `user.permisos` de `/auth/me` vía AuthContext — nunca con un fetch
 * propio. Deny-by-default: `(modulo, accion)` que no aparece, no se puede.
 * La UI SOLO PINTA con esto; el control de acceso real vive en cada
 * endpoint del servidor.
 *
 * `userOverride` es para pruebas/demo (PermisosDemo.jsx, capturas de
 * cierre de I5) — simular un usuario sin necesitar una sesión real con ese
 * rol exacto. En producción nunca se pasa: el default es `useAuth().user`.
 */
export function usePermisos(userOverride) {
  const { user: authUser } = useAuth();
  const user = userOverride !== undefined ? userOverride : authUser;

  // I8 lote 5 (B-I14): confirmado que /auth/me manda `permisos` con
  // contenido real para los 4 roles base (superadmin, admin, creador,
  // colaborador_mkt) — WP1 aterrizó. Se retiró `fallbackPorRol.js`, el
  // respaldo temporal que derivaba permisos del rol base cuando el
  // servidor mandaba `{}`; deny-by-default ahora aplica también si por
  // algún motivo `permisos` llegara vacío (nunca debería, salvo un bug).
  const permisos = useMemo(() => user?.permisos ?? {}, [user]);

  function permisosDe(modulo) {
    if (permisos === "*") return ["*"];
    return permisos[modulo] || [];
  }

  function puede(modulo, accion) {
    // Deny-by-default también contra el catálogo: una clave que el
    // contrato ya no reconoce no puede otorgar acceso a nada, aunque el
    // usuario tenga el paquete que antes la incluía. El aviso es
    // específicamente para ESTE caso (clave que ya no existe) — advertir
    // en cada llamada, exista o no la clave, sería ruido, no diagnóstico.
    if (!accionExiste(modulo, accion)) {
      advertirClaveDesconocida(modulo, accion);
      return false;
    }

    if (permisos === "*") return true;
    const acciones = permisos[modulo];
    if (acciones === "*") return true;
    return Array.isArray(acciones) && acciones.includes(accion);
  }

  return { puede, permisosDe };
}
