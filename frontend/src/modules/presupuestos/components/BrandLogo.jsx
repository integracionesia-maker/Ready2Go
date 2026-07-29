import { useTheme } from "@/context/ThemeContext";
import imagotipoBlanco from "@/assets/logos/imagotipo-go-blanco.png";
import imagotipoNaranja from "@/assets/logos/imagotipo-go-naranja.png";
import isotipoBlanco from "@/assets/logos/isotipo-go-blanco.png";
import isotipoNaranja from "@/assets/logos/isotipo-go-naranja.png";

const SOURCES = {
  imagotipo: { dark: imagotipoBlanco, light: imagotipoNaranja },
  isotipo: { dark: isotipoBlanco, light: isotipoNaranja },
};

/**
 * Logo oficial Grupo Ortiz, consciente del tema: variante blanca en modo
 * oscuro y naranja en modo claro.
 *
 * variant: "imagotipo" (logo completo, cuadrado) | "isotipo" (símbolo, apaisado)
 */
export default function BrandLogo({ variant = "isotipo", className = "", alt = "Grupo Ortiz" }) {
  const { theme } = useTheme();
  return (
    <img
      src={SOURCES[variant][theme === "light" ? "light" : "dark"]}
      alt={alt}
      className={className}
      draggable={false}
    />
  );
}
