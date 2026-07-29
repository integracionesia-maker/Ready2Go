/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        go: {
          orange: "#FB670B",
          "orange-hover": "#FF7A22",
          "orange-pressed": "#D95C00",
          "orange-tint": "rgba(251,103,11,0.10)",
          black: "#262626",
          gray: {
            1: "#535353",
            2: "#C5C5C5",
            3: "#ECEBE0",
          },
          white: "#FFFFFF",
          dark: {
            900: "#09090B",
            800: "#111113",
            700: "#18181B",
            600: "#27272A",
          },
          error: "#E53E3E",
        },
        chart: {
          1: "#FB670B",
          2: "#14B8A6",
          3: "#38BDF8",
          4: "#A78BFA",
          5: "#00A36E",
          6: "#F59E0B",
        },
      },
      fontFamily: {
        // Lee las pilas de src/design/fonts.css — meter los woff2 de marca
        // cuando lleguen es cambiar ese único archivo, no este.
        display: ["var(--go-font-display)", "sans-serif"],
        body: ["var(--go-font-body)", "sans-serif"],
        mono: ["var(--go-font-mono)", "monospace"],
      },
      borderRadius: {
        go: "8px",
        "go-lg": "12px",
        "go-xl": "16px",
      },
    },
  },
  plugins: [],
};
