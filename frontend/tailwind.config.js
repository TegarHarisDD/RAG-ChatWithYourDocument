/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Semantic tokens resolved from CSS variables (see styles.css). The
        // whole palette swaps between light and dark by toggling `.dark` on
        // <html>, so every surface follows without per-element dark: variants.
        // The system is monochrome: accent and primary both resolve to ink, so
        // no component carries chroma (the aura glow is the only hue).
        bg: "rgb(var(--c-bg) / <alpha-value>)",
        panel: "rgb(var(--c-panel) / <alpha-value>)",
        panel2: "rgb(var(--c-panel2) / <alpha-value>)",
        raised: "rgb(var(--c-raised) / <alpha-value>)",
        line: "rgb(var(--c-line) / <alpha-value>)",
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        faint: "rgb(var(--c-faint) / <alpha-value>)",
        accent: "rgb(var(--c-accent) / <alpha-value>)",
        accentDeep: "rgb(var(--c-accent-deep) / <alpha-value>)",
        primary: "rgb(var(--c-primary) / <alpha-value>)",
        onPrimary: "rgb(var(--c-on-primary) / <alpha-value>)",
        danger: "rgb(var(--c-danger) / <alpha-value>)",
        success: "rgb(var(--c-success) / <alpha-value>)",
        warning: "rgb(var(--c-warning) / <alpha-value>)",
      },
      fontFamily: {
        // One family, no exceptions. Display, reading, and mono all resolve to
        // the same grotesque so hierarchy comes from size and weight alone.
        sans: [
          "Inter",
          "Geist",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        display: ["Inter", "Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        reading: ["Inter", "Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["Inter", "Geist", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        control: "var(--radius-control)",
        panel: "var(--radius-panel)",
        prompt: "var(--radius-prompt)",
        pill: "var(--radius-pill)",
      },
      keyframes: {
        caret: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
      animation: {
        caret: "caret 1s step-end infinite",
      },
    },
  },
  plugins: [],
};
