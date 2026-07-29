/**
 * Bloque de carga — reusa el lenguaje visual de LoadingScreen (degradado
 * naranja en movimiento, no un shimmer gris genérico). `go-skeleton-shimmer`
 * vive en index.css junto a las demás animaciones de carga.
 */
export default function SkeletonShimmer({ className = "", rounded = "rounded-go" }) {
  return <div className={`go-skeleton-shimmer ${rounded} ${className}`.trim()} aria-hidden="true" />;
}
