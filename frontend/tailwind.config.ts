import type { Config } from "tailwindcss";

// Design tokens from the Stitch project "FLARE AI Research Portal"
// (design system: Orbital Flame Telemetry).
const grotesk = ["var(--font-grotesk)", "Space Grotesk", "system-ui", "sans-serif"];
const inter = ["var(--font-inter)", "Inter", "system-ui", "sans-serif"];

const config: Config = {
  darkMode: "class",
  content: ["./src/components/**/*.{ts,tsx}", "./src/app/**/*.{ts,tsx}", "./src/lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#ffb59d",
        "on-primary": "#5d1900",
        "primary-container": "#ff6b35",
        "on-primary-container": "#5f1900",
        secondary: "#7bd0ff",
        "on-secondary": "#00354a",
        "secondary-container": "#00a6e0",
        "secondary-fixed": "#c4e7ff",
        tertiary: "#ffb95f",
        "on-tertiary": "#472a00",
        "tertiary-container": "#d68900",
        "tertiary-fixed": "#ffddb8",
        error: "#ffb4ab",
        "error-container": "#93000a",
        "on-error-container": "#ffdad6",
        background: "#0f131d",
        surface: "#0f131d",
        "surface-bright": "#353944",
        "surface-container-lowest": "#0a0e18",
        "surface-container-low": "#171b26",
        "surface-container": "#1c1f2a",
        "surface-container-high": "#262a35",
        "surface-container-highest": "#313540",
        "on-surface": "#dfe2f1",
        "on-surface-variant": "#e1bfb5",
        outline: "#a98a80",
        "outline-variant": "#594139",
        amber: { glow: "#fbbf24", deep: "#f59e0b", light: "#fde047", ink: "#09132e" },
      },
      borderRadius: { DEFAULT: "0.25rem", lg: "0.5rem", xl: "0.75rem", "2xl": "1rem", full: "9999px" },
      spacing: {
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "1rem",
        "space-lg": "1.5rem",
        "space-xl": "2rem",
        "space-2xl": "3rem",
      },
      fontFamily: { display: grotesk, body: inter },
      fontSize: {
        "headline-lg": ["32px", { lineHeight: "40px", letterSpacing: "-0.01em", fontWeight: "700" }],
        "headline-lg-mobile": ["24px", { lineHeight: "32px", letterSpacing: "0em", fontWeight: "700" }],
        "headline-md": ["24px", { lineHeight: "32px", letterSpacing: "0em", fontWeight: "600" }],
        "title-md": ["16px", { lineHeight: "24px", letterSpacing: "0.05em", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "26px", letterSpacing: "0em", fontWeight: "400" }],
        "body-md": ["14px", { lineHeight: "22px", letterSpacing: "0em", fontWeight: "400" }],
        "label-md": ["12px", { lineHeight: "16px", letterSpacing: "0.08em", fontWeight: "600" }],
        "label-sm": ["10px", { lineHeight: "14px", letterSpacing: "0.12em", fontWeight: "600" }],
        "code-sm": ["12px", { lineHeight: "18px", letterSpacing: "0.02em", fontWeight: "500" }],
      },
    },
  },
  plugins: [],
};

export default config;
