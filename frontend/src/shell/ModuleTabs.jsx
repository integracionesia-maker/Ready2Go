import GlassNav from "@/design/GlassNav";
import { MODULE_NAV_ITEMS } from "./navItems";

/** Instancia concreta de GlassNav para el cambio de módulo (Presupuestos/Equipos). */
export default function ModuleTabs() {
  return <GlassNav items={MODULE_NAV_ITEMS} ariaLabel="Navegacion principal" />;
}
