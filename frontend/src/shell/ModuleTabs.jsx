import { useMemo } from "react";
import GlassNav from "@/design/GlassNav";
import { MODULE_NAV_ITEMS } from "./navItems";
import { useAuth } from "@/context/AuthContext";

/**
 * Switch Presupuestos / Equipos.
 * Solo muestra los tabs de módulos a los que el usuario realmente tiene acceso.
 * Si el usuario solo tiene acceso a un módulo, el switch no se renderiza.
 *
 * Para marketing_basico, el tab de Equipos apunta a /equipos/nuevo
 * (no tienen dashboard de Equipos, solo pueden solicitar préstamos).
 */
export default function ModuleTabs() {
  const { user } = useAuth();
  const permisos = user?.permisos || {};

  const tienePresupuestos = Object.keys(permisos).some(
    (m) => m === "presupuestos" && permisos[m].length > 0
  );
  const tieneEquipos = Object.keys(permisos).some(
    (m) => m.startsWith("equipos_") && permisos[m].length > 0
  );

  // Si solo tiene acceso a un módulo, no mostramos el switch
  if (!tienePresupuestos || !tieneEquipos) return null;

  // marketing_basico: solo solicitar préstamos y ver propios — sin dashboard.
  // El tab de Equipos debe llevarlos directo a /equipos/nuevo.
  const equiposDashboard =
    permisos.equipos_inventario?.includes("ver") ||
    permisos.equipos_prestamos?.some((a) => a !== "solicitar" && a !== "ver_propios");

  const items = useMemo(
    () =>
      MODULE_NAV_ITEMS.map((item) =>
        item.to === "/equipos" && !equiposDashboard
          ? { ...item, to: "/equipos/nuevo" }
          : item
      ),
    [equiposDashboard]
  );

  return <GlassNav items={items} ariaLabel="Navegacion principal" transparent />;
}
