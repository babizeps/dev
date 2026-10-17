import { useCallback, useState } from "react";

export type ThemeStyle = "studio" | "sketch";
export type ThemeMode = "light" | "dark";

const STYLE_KEY = "worldboard.style";
const MODE_KEY = "worldboard.mode";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Ohne Browser-Speicher gilt die Wahl nur bis zum Neuladen.
  }
}

function initialStyle(): ThemeStyle {
  return read(STYLE_KEY) === "sketch" ? "sketch" : "studio";
}

function initialMode(): ThemeMode {
  const stored = read(MODE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function apply(style: ThemeStyle, mode: ThemeMode) {
  document.documentElement.dataset.style = style;
  document.documentElement.dataset.mode = mode;
}

/** Vor dem ersten Rendern aufrufen, damit nichts im falschen Theme aufblitzt. */
export function applyStoredTheme() {
  apply(initialStyle(), initialMode());
}

export function useTheme() {
  const [style, setStyleState] = useState(initialStyle);
  const [mode, setModeState] = useState(initialMode);

  const setStyle = useCallback(
    (next: ThemeStyle) => {
      setStyleState(next);
      write(STYLE_KEY, next);
      apply(next, mode);
    },
    [mode],
  );

  const setMode = useCallback(
    (next: ThemeMode) => {
      setModeState(next);
      write(MODE_KEY, next);
      apply(style, next);
    },
    [style],
  );

  return { style, mode, setStyle, setMode };
}
