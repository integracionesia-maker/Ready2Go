import { Outlet } from "react-router-dom";
import GlassFilterDefs from "@/design/GlassFilterDefs";
import ModuleTabs from "./ModuleTabs";

/**
 * Chrome genérico del shell (B-I04).
 * ModuleTabs en header (desktop) y flotante abajo (móvil).
 * GlassFilterDefs se monta una sola vez aquí.
 */
export default function AppShell() {
  return (
    <>
      <GlassFilterDefs />
      <Outlet />
      {/* Mobile: floating module switch pinned to bottom */}
      <div className="fixed bottom-3 left-2 right-2 z-50 flex justify-center sm:hidden">
        <ModuleTabs />
      </div>
    </>
  );
}
