import { useEffect, useState } from "react";
import { Outlet, Navigate } from "react-router-dom";
import Header from "@/modules/presupuestos/components/Header";
import EquiposSidebar from "./components/EquiposSidebar";
import { useAuth } from "@/context/AuthContext";
import { usePermisos } from "./permisos/usePermisos";
import { fetchLoans } from "./api";

const ESTADOS_ABIERTOS_NO_TERMINALES = ["borrador", "cancelado"];

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
  const { puede } = usePermisos();
  const permisos = user?.permisos || {};

  const tieneEquipos = Object.keys(permisos).some(
    (m) => m.startsWith("equipos_") && permisos[m].length > 0
  );

  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed") === "true"
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  // Badge junto a "Aprobaciones": préstamos con la firma del aprobador
  // pendiente (§1b de loan_state.py — es la notificación en la app que le
  // avisa a Melisa, o a quien tenga el mismo paquete, que hay algo por
  // firmar en cuanto entra). Solo se pide si el usuario puede firmar; nadie
  // más necesita este conteo.
  const esAprobador = puede("equipos_aprobacion", "autorizar_entrega");
  useEffect(() => {
    if (!esAprobador) return;
    let cancelado = false;
    fetchLoans({ limit: 200 })
      .then((data) => {
        if (cancelado) return;
        const count = data.items.filter(
          (l) => l.firma_entrega_pendiente && !ESTADOS_ABIERTOS_NO_TERMINALES.includes(l.estado)
        ).length;
        setPendingCount(count);
      })
      .catch(() => {
        // El badge es informativo — si falla, simplemente no se muestra.
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [esAprobador]);

  if (!tieneEquipos) return <Navigate to="/" replace />;

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
        pendingCount={pendingCount}
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
