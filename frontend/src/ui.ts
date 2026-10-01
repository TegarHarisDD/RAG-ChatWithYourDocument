// Squared, hairline-ruled controls — printed-page affordances, not app pills.
export const btn =
  "inline-flex items-center justify-center gap-2 px-3 py-2 font-mono text-xs font-medium tracking-wide transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-45";

export const btnPrimary = `${btn} bg-primary text-onPrimary hover:bg-primary/85`;

export const btnSecondary = `${btn} border border-line bg-transparent text-ink hover:border-accent hover:text-accent`;

// Compact control kept at a comfortable hit area (>= 24px target, 8px spacing).
export const btnGhost =
  "inline-flex min-h-[2rem] items-center justify-center gap-1 px-2 py-1.5 font-mono text-[11px] font-medium tracking-wide text-muted transition-colors duration-200 hover:text-accent disabled:cursor-not-allowed disabled:opacity-40";

export const btnDanger = `${btn} border border-danger/45 text-danger hover:bg-danger/10`;

export const inputClass =
  "w-full border border-line bg-bg px-3 py-2 font-mono text-sm text-ink outline-none transition-colors duration-200 placeholder:text-faint focus:border-accent";

export const card = "border border-line bg-panel";
