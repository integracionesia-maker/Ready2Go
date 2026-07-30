import { useState } from "react";
import { Outlet } from "react-router-dom";
import Header from "@/modules/presupuestos/components/Header";
import EquiposSidebar from "./components/EquiposSidebar";

/**
 * Chrome del módulo Equipos — estructuralmente idéntico a
 * `PresupuestosLayout` (Header + Sidebar colapsable + main con offset).
 * Reusa el `Header` de Presupuestos con su propio subtítulo; el Sidebar es
 * propio (items y permisos de Equipos) pero mismas dimensiones/comportamiento.
 * Clave de colapso en localStorage separada para no pisar la de Presupuestos.
 */
export default function EquiposLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed-equipos") === "true"
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed-equipos", next ? "true" : "false");
      return next;
    });
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--go-bg)" }}>
      <Header onOpenMobileMenu={() => setMobileMenuOpen(true)} subtitle="Control de Equipos" />
      <EquiposSidebar
        collapsed={sidebarCollapsed}
        onToggle={handleToggleSidebar}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <main
        className={`min-h-screen pt-16 transition-all duration-300 ${
          sidebarCollapsed ? "md:ml-16" : "md:ml-60"
        }`}
      >
        <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
