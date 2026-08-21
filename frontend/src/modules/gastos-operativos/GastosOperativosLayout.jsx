import { useState } from "react";
import { Outlet, Navigate, Routes, Route } from "react-router-dom";
import Header from "@/modules/presupuestos/components/Header";
import { NotFoundPage } from "@/design";
import { useAuth } from "@/context/AuthContext";
import OperativosSidebar from "./components/OperativosSidebar";
import InicioPage from "./pages/InicioPage";
import RegistroPage from "./pages/RegistroPage";
import DashboardOperativoPage from "./pages/DashboardOperativoPage";
import RubrosPage from "./pages/RubrosPage";

/**
 * Chrome del módulo Gastos Operativos — mismo patrón que EquiposLayout
 * (Header + sidebar colapsable + main con offset). Los hooks van SIEMPRE antes
 * del posible redirect: llamar hooks después de un `return` condicional rompe
 * las reglas de hooks (bug que arrastraba EquiposLayout; aquí no se repite).
 */
export default function GastosOperativosLayout() {
  const { user } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed") === "true"
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const permisos = user?.permisos?.gastos_operativos || [];
  const tieneAcceso = permisos.length > 0;
  const puedeGestionarRubros = permisos.includes("gestionar_rubros");

  if (!tieneAcceso) return <Navigate to="/" replace />;

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", next ? "true" : "false");
      return next;
    });
  };

  return (
    <div className="min-h-screen">
      <Header
        onToggleMobileMenu={() => setMobileMenuOpen((v) => !v)}
        mobileMenuOpen={mobileMenuOpen}
        subtitle="Gastos Operativos"
      />
      <OperativosSidebar
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
          <Routes>
            <Route index element={<InicioPage />} />
            <Route path="registro" element={<RegistroPage />} />
            <Route path="dashboard" element={<DashboardOperativoPage />} />
            <Route
              path="rubros"
              element={puedeGestionarRubros ? <RubrosPage /> : <Navigate to="/gastos-operativos" replace />}
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
