/**
 * Superficie de cristal genérica — receta única de DESIGN_SYSTEM.md (.glass en
 * glass.css). `veiled` (default true) agrega el velo sólido detrás del
 * contenido: casi todo lo que se pone dentro de un GlassPanel es texto, y el
 * contraste medido 4.5:1 exige alpha 1 detrás de él.
 *
 * No usar en filas de tabla, listas largas ni contenedores con scroll (regla
 * dura DESIGN_SYSTEM.md §Reglas duras #2), y máximo 3-4 en pantalla a la vez.
 */
export default function GlassPanel({
  as: Component = "div",
  refract = false,
  veiled = true,
  className = "",
  veilClassName = "",
  children,
  ...rest
}) {
  return (
    <Component className={`glass ${refract ? "glass--refract" : ""} ${className}`.trim()} {...rest}>
      {veiled ? <div className={`veil h-full w-full ${veilClassName}`.trim()}>{children}</div> : children}
    </Component>
  );
}
