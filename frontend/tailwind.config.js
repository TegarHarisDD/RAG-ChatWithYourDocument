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
        // Display: Fraunces. Reading: Newsreader. Apparatus + interface:
        // IBM Plex Mono. Prose is set in a serif; every machine fact (counts,
        // locators, statuses, timestamps) is set in mono.
        display: ["Fraunces", "Iowan Old Style", "Georgia", "serif"],
        reading: ["Newsreader", "Iowan Old Style", "Georgia", "serif"],
        mono: [
          "IBM Plex Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
        sans: [
          "IBM Plex Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      keyframes: {
        // A single orchestrated entrance, used once per surface.
        settle: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        caret: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
      animation: {
        settle: "settle 560ms cubic-bezier(0.2, 0.7, 0.2, 1) both",
        caret: "caret 1s step-end infinite",
      },
    },
  },
  plugins: [],
};
