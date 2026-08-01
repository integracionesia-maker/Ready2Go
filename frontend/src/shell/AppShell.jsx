import { Outlet } from "react-router-dom";
import GlassFilterDefs from "@/design/GlassFilterDefs";
import { CommandPaletteProvider } from "@/design/CommandPalette";

/**
 * Chrome genérico del shell (B-I04).
 * ModuleTabs ahora vive dentro del Header de cada layout (I2 liquid crystal).
 * GlassFilterDefs se monta una sola vez aquí.
 */
export default function AppShell() {
  return (
    <CommandPaletteProvider>
      <GlassFilterDefs />
      <Outlet />
    </CommandPaletteProvider>
  );
}
