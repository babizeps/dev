import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

export type ThemeStyle = "studio" | "sketch";
/** Der Modus, in dem gerade gezeichnet wird. */
export type ThemeMode = "light" | "dark";
/** Die Wahl im Ansicht-Menü; „auto“ folgt der Systemeinstellung. */
export type ModeSetting = ThemeMode | "auto";

const STYLE_KEY = "worldboard.style";
const MODE_KEY = "worldboard.mode";
const DARK_QUERY = "(prefers-color-scheme: dark)";

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

function initialModeSetting(): ModeSetting {
  const stored = read(MODE_KEY);
  return stored === "light" || stored === "dark" ? stored : "auto";
}

function systemMode(): ThemeMode {
  return window.matchMedia?.(DARK_QUERY).matches ? "dark" : "light";
}

function resolve(setting: ModeSetting): ThemeMode {
  return setting === "auto" ? systemMode() : setting;
}

function apply(style: ThemeStyle, mode: ThemeMode) {
  document.documentElement.dataset.style = style;
  document.documentElement.dataset.mode = mode;
}

/** Vor dem ersten Rendern aufrufen, damit nichts im falschen Theme aufblitzt. */
export function applyStoredTheme() {
  apply(initialStyle(), resolve(initialModeSetting()));
}

export function useTheme() {
  const [style, setStyleState] = useState(initialStyle);
  const [modeSetting, setModeSettingState] = useState(initialModeSetting);
  const [system, setSystem] = useState(systemMode);
  const mode: ThemeMode = modeSetting === "auto" ? system : modeSetting;

  // Wechselt das System zwischen Tag und Nacht (z. B. macOS „Automatisch“), zieht die App mit.
  useEffect(() => {
    const query = window.matchMedia?.(DARK_QUERY);
    if (!query) return;
    const onChange = () => setSystem(query.matches ? "dark" : "light");
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  useEffect(() => apply(style, mode), [style, mode]);

  const setStyle = useCallback((next: ThemeStyle) => {
    setStyleState(next);
    write(STYLE_KEY, next);
  }, []);

  const setModeSetting = useCallback((next: ModeSetting) => {
    setModeSettingState(next);
    write(MODE_KEY, next);
  }, []);

  return { style, mode, modeSetting, setStyle, setModeSetting };
}

function subscribeStyle(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-style"] });
  return () => observer.disconnect();
}

/** Der gerade aktive Stil, für Teile, die nicht unter `useTheme` hängen (z. B. Verbindungen). */
export function useActiveStyle(): ThemeStyle {
  return useSyncExternalStore(subscribeStyle, () => (document.documentElement.dataset.style === "sketch" ? "sketch" : "studio"));
}
