/**
 * Variantes y duraciones compartidas para `motion` (sucesor de framer-motion).
 * Espejo en JS de --go-ease / --go-duration-* de tokens.css, para animaciones
 * manejadas por JS (las de CSS puro siguen usando las variables directamente).
 */

export const EASE_OUT = [0.16, 1, 0.3, 1];

export const DURATION = {
  fast: 0.15,
  base: 0.25,
  slow: 0.4,
};

export const springSnappy = { type: "spring", stiffness: 500, damping: 40 };
export const springSoft = { type: "spring", stiffness: 260, damping: 30 };

export const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const fadeInUp = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

/** Entrada escalonada de KPIs/cards (DESIGN_SYSTEM.md §Animacion). */
export function staggerContainer(staggerChildren = 0.06, delayChildren = 0) {
  return {
    hidden: {},
    visible: { transition: { staggerChildren, delayChildren } },
  };
}

export const modalOverlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const modalPanelVariants = {
  hidden: { opacity: 0, scale: 0.96, y: 8 },
  visible: { opacity: 1, scale: 1, y: 0 },
};
