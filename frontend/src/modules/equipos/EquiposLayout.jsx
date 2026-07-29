import { Outlet } from "react-router-dom";
import EquiposSubNav from "./EquiposSubNav";

/**
 * Chrome del módulo Equipos: sub-nav + contenido. A diferencia de
 * Presupuestos, Equipos no tiene Header/Sidebar propios — el único chrome
 * fijo es el GlassNav de módulos del shell (AppShell), que reserva ~4rem
 * arriba (mismo alto que el Header de Presupuestos, por consistencia).
 */
export default function EquiposLayout() {
  return (
    <div className="min-h-screen pt-16" style={{ background: "var(--go-bg)" }}>
      <div className="mx-auto w-full max-w-7xl px-4 pb-8 sm:px-6 lg:px-8">
        <EquiposSubNav />
        <div className="mt-4">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
