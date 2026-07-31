import GlassNav from "@/design/GlassNav";
import { MODULE_NAV_ITEMS } from "./navItems";

/** Instancia concreta de GlassNav para el cambio de módulo (Presupuestos/Equipos).
 * Con `transparent` el nav deja pasar el brillo liquid crystal del header
 * que está detrás — no es un elemento aislado, es parte del cristal. */
export default function ModuleTabs() {
  return <GlassNav items={MODULE_NAV_ITEMS} ariaLabel="Navegacion principal" transparent />;
}
