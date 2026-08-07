import { forwardRef } from "react";

/**
 * Superficie de cristal genérica — receta única de DESIGN_SYSTEM.md (.glass en
 * glass.css). Capa única: el glass mismo es la superficie de texto (88% opaco),
 * sin velo adicional por defecto. El prop `veiled` se mantiene por compatibilidad
 * con usos legacy que aún requieren capa separada (LoginPage, modales viejos).
 *
 * No usar en filas de tabla, listas largas ni contenedores con scroll.
 */
const GlassPanel = forwardRef(function GlassPanel(
  { as: Component = "div", refract = false, veiled = false, className = "", veilClassName = "", children, ...rest },
  ref,
) {
  return (
    <Component ref={ref} className={`glass ${refract ? "glass--refract" : ""} ${className}`.trim()} {...rest}>
      {veiled ? <div className={`veil h-full w-full ${veilClassName}`.trim()}>{children}</div> : children}
    </Component>
  );
});

export default GlassPanel;
