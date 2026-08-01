import { useState } from "react";
import { Outlet, Navigate } from "react-router-dom";
import Header from "@/modules/presupuestos/components/Header";
import EquiposSidebar from "./components/EquiposSidebar";
import { useAuth } from "@/context/AuthContext";

/**
 * Chrome del módulo Equipos — estructuralmente idéntico a
 * `PresupuestosLayout` (Header + Sidebar colapsable + main con offset).
 * Reusa el `Header` de Presupuestos con su propio subtítulo; el Sidebar es
 * propio (items y permisos de Equipos) pero mismas dimensiones/comportamiento.
 *
 * Si el usuario no tiene ningún permiso de Equipos, se redirige a la raíz.
 */
export default function EquiposLayout() {
  const { user } = useAuth();
  const permisos = user?.permisos || {};

  const tieneEquipos = Object.keys(permisos).some(
    (m) => m.startsWith("equipos_") && permisos[m].length > 0
  );

  if (!tieneEquipos) return <Navigate to="/" replace />;

  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed") === "true"
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", next ? "true" : "false");
      return next;
    });
  };

  return (
    <div className="min-h-screen">
      <Header onToggleMobileMenu={() => setMobileMenuOpen((v) => !v)} mobileMenuOpen={mobileMenuOpen} subtitle="Control de Equipos" />
      <EquiposSidebar
        collapsed={sidebarCollapsed}
        onToggle={handleToggleSidebar}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <main
        className={`min-h-screen pt-20 transition-all duration-300 ${
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
