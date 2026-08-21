import { useMemo } from "react";
import GlassNav from "@/design/GlassNav";
import { MODULE_NAV_ITEMS } from "./navItems";
import { useAuth } from "@/context/AuthContext";

/**
 * Switch Presupuestos / Equipos / Gastos Operativos.
 * Solo muestra los tabs de los módulos a los que el usuario tiene acceso; si
 * solo tiene uno, el switch no se renderiza.
 *
 * Para marketing_basico, el tab de Equipos apunta a /equipos/nuevo
 * (no tienen dashboard de Equipos, solo pueden solicitar préstamos).
 */
export default function ModuleTabs() {
  const { user } = useAuth();
  const permisos = user?.permisos || {};

  const acceso = useMemo(
    () => ({
      presupuestos: (permisos.presupuestos || []).length > 0,
      equipos: Object.keys(permisos).some((m) => m.startsWith("equipos_") && permisos[m].length > 0),
      gastos_operativos: (permisos.gastos_operativos || []).length > 0,
    }),
    [permisos]
  );

  // marketing_basico: solo solicitar préstamos y ver propios — sin dashboard.
  const equiposDashboard =
    permisos.equipos_inventario?.includes("ver") ||
    permisos.equipos_prestamos?.some((a) => a !== "solicitar" && a !== "ver_propios");

  const items = useMemo(() => {
    const visibles = MODULE_NAV_ITEMS.filter((item) => acceso[item.moduleKey]);
    return visibles.map((item) =>
      item.to === "/equipos" && !equiposDashboard ? { ...item, to: "/equipos/nuevo" } : item
    );
  }, [acceso, equiposDashboard]);

  // Con acceso a un solo módulo, no hay nada que conmutar.
  if (items.length < 2) return null;

  return <GlassNav items={items} ariaLabel="Navegacion principal" transparent />;
}
