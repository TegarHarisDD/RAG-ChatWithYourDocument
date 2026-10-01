import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "cwd:theme";
const THEME_EVENT = "cwd:theme";

const THEME_COLORS: Record<Theme, string> = {
  light: "#fcfcfc",
  dark: "#0a0a0a",
};

export function getTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.setAttribute("data-theme", theme);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", THEME_COLORS[theme]);
  window.dispatchEvent(new Event(THEME_EVENT));
}

export function setTheme(theme: Theme) {
  applyTheme(theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage can be unavailable (private mode); the DOM class still applies.
  }
}

// The initial class is set by the inline script in index.html to avoid a
// flash, so the hook can read it directly as its starting state. A window event
// keeps every consumer (sidebar toggle, command palette) in sync.
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getTheme);

  useEffect(() => {
    function sync() {
      setThemeState(getTheme());
    }
    window.addEventListener(THEME_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(THEME_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const toggle = useCallback(() => {
    const next: Theme = getTheme() === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }, []);

  return { theme, toggle };
}

