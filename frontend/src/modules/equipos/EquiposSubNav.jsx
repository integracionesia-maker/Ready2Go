import GlassNav from "@/design/GlassNav";
import { usePermisos } from "./permisos/usePermisos";

const TODOS_LOS_ITEMS = [
  { to: "/equipos", label: "Inicio", end: true, permiso: ["equipos_inventario", "ver"] },
  { to: "/equipos/inventario", label: "Inventario", permiso: ["equipos_inventario", "ver"] },
  { to: "/equipos/nuevo", label: "Nuevo préstamo", permiso: ["equipos_prestamos", "solicitar"] },
  { to: "/equipos/activos", label: "Activos", permiso: ["equipos_prestamos", "ver_propios"] },
  { to: "/equipos/aprobaciones", label: "Aprobaciones", permiso: ["equipos_aprobacion", "autorizar_entrega"] },
  { to: "/equipos/historial", label: "Historial", permiso: ["equipos_prestamos", "ver_propios"] },
];

/**
 * Sub-nav del módulo Equipos (bajo el GlassNav de módulos del shell). La UI
 * solo pinta: cada endpoint valida el permiso por su cuenta — esconder una
 * pestaña es cortesía, no seguridad.
 */
export default function EquiposSubNav() {
  const { puede } = usePermisos();
  const items = TODOS_LOS_ITEMS.filter(({ permiso }) => puede(permiso[0], permiso[1])).map(
    ({ to, label, end }) => ({ to, label, end })
  );

  if (items.length === 0) return null;

  // go-table-scroll-wrapper/go-table-scroll (index.css): mismo patron que las
  // tablas con overflow horizontal. Con 6 pestañas el GlassNav (pensado para
  // 2 items) no cabe en 320-390px — sin esto, `justify-center` recortaba
  // "Inicio" fuera de la pantalla sin forma de llegar a el.
  return (
    <div className="go-table-scroll-wrapper flex justify-center py-2 sm:justify-start">
      <div className="overflow-x-auto go-table-scroll">
        <GlassNav items={items} ariaLabel="Navegación de Equipos" refract={false} />
      </div>
    </div>
  );
}
