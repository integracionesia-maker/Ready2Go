import { Outlet } from "react-router-dom";
import GlassFilterDefs from "@/design/GlassFilterDefs";
import { CommandPaletteProvider } from "@/design/CommandPalette";
import ModuleTabs from "./ModuleTabs";

/**
 * Chrome genérico del shell (B-I04): solo GlassNav de módulos + <Outlet />.
 * Nada de lógica de Presupuestos aquí — eso vive en PresupuestosLayout,
 * renderizado como contenido de la ruta hija.
 *
 * El nav de módulos se monta como overlay centrado sobre la fila del Header
 * de Presupuestos (que queda "tal cual" — I1 no re-piela vistas, eso es I2)
 * en vez de agregar una segunda barra fija: Header ya deja el centro de su
 * fila vacío (justify-between con logo a la izquierda y controles a la
 * derecha), así que este overlay no tapa nada y no exige tocar Header.jsx
 * ni Sidebar.jsx para correr sus offsets. Es una convivencia transicional
 * a propósito — I2 decide cómo se ve la piel unificada.
 *
 * GlassFilterDefs se monta una sola vez aquí: es el único punto del árbol
 * donde vive el shell completo (login no lo necesita).
 */
export default function AppShell() {
  return (
    <CommandPaletteProvider>
      <GlassFilterDefs />
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-50 flex items-center justify-center"
        style={{ height: "4rem" }}
      >
        <div className="pointer-events-auto">
          <ModuleTabs />
        </div>
      </div>
      <Outlet />
    </CommandPaletteProvider>
  );
}
