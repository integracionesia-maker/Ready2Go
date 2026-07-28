/**
 * Filtro SVG de refracción (feTurbulence + feDisplacementMap + feSpecularLighting)
 * montado UNA sola vez en el shell, detrás de @supports (ver glass.css). Se monta
 * oculto (0x0, fuera de flujo) — solo existe para que `.glass--refract` pueda
 * referenciarlo por id vía `backdrop-filter: url(#id)`.
 *
 * Solo Chromium interpreta backdrop-filter con un filtro SVG por id; Safari y
 * Firefox lo ignoran en silencio (por eso glass.css lo envuelve en @supports).
 */
export default function GlassFilterDefs({ id = "go-glass-refract" }) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}
    >
      <defs>
        <filter id={id} x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.008 0.008" numOctaves="2" seed="7" result="noise" />
          <feGaussianBlur in="noise" stdDeviation="6" result="softNoise" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="softNoise"
            scale="18"
            xChannelSelector="R"
            yChannelSelector="G"
            result="displaced"
          />
          <feSpecularLighting
            in="softNoise"
            surfaceScale="6"
            specularConstant="0.9"
            specularExponent="18"
            lightingColor="#ffffff"
            result="specular"
          >
            <fePointLight x="-60" y="-80" z="140" />
          </feSpecularLighting>
          <feComposite in="specular" in2="displaced" operator="in" result="specularClipped" />
          <feMerge>
            <feMergeNode in="displaced" />
            <feMergeNode in="specularClipped" />
          </feMerge>
        </filter>
      </defs>
    </svg>
  );
}
