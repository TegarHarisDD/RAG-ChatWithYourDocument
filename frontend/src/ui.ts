// Component recipes from the design tokens (see styles.css). Buttons are
// monochrome pills: primary is the filled ink pill, secondary is the same pill
// with a hairline. There is no chromatic variant — the edge glow is the only
// hue on the page.
export const btn =
  "inline-flex items-center justify-center gap-2 rounded-pill px-4 py-2 text-sm font-medium tracking-[-0.006em] transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40";

export const btnPrimary = `${btn} bg-ink text-onPrimary hover:bg-ink/85`;

export const btnSecondary = `${btn} border border-line bg-bg text-ink hover:bg-panel2`;

// The destructive action is the filled pill, matching "one primary action" per
// view; the system carries no danger hue.
export const btnDanger = `${btn} bg-ink text-onPrimary hover:bg-ink/85`;

export const btnGhost =
  "inline-flex min-h-[2.25rem] items-center justify-center gap-1 rounded-pill px-3 py-1.5 text-sm font-medium text-muted transition-colors duration-150 hover:bg-panel2 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40";

export const inputClass =
  "w-full rounded-control bg-panel px-3 py-2 text-base text-ink outline-none transition-colors placeholder:text-muted";

export const card = "rounded-panel bg-panel";
