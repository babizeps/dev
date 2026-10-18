import { isTauri } from "@tauri-apps/api/core";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/700.css";
import "@fontsource/karla/400.css";
import "@fontsource/karla/500.css";
import "@fontsource/caveat/600.css";
import "@fontsource/caveat/700.css";
import "@xyflow/react/dist/style.css";
import "./ui/styles.css";
import { migrate } from "./core/migrations";
import { useWorld } from "./core/store";
import { createAutosave } from "./storage/autosave";
import { createIndexedDbStorage } from "./storage/indexedDb";
import type { StorageAdapter } from "./storage/StorageAdapter";
import { App } from "./ui/App";
import { StorageProvider } from "./ui/assets";
import { applyStoredTheme } from "./ui/theme";

const root = createRoot(document.getElementById("root")!);
applyStoredTheme();

async function openStorage(): Promise<StorageAdapter> {
  if (isTauri()) return (await import("./storage/tauriFs")).createTauriStorage();
  // Bittet den Browser, den Speicher nicht von selbst aufzuräumen.
  navigator.storage?.persist?.().catch(() => {});
  return createIndexedDbStorage();
}

async function start() {
  let storage: StorageAdapter;
  let world;
  try {
    storage = await openStorage();
    world = migrate(await storage.loadWorld());
  } catch (err) {
    // Nicht weiterarbeiten: sonst würde das Auto-Speichern die unlesbare Welt überschreiben.
    root.render(
      <div className="fatal" role="alert">
        <h1>Die Welt konnte nicht geladen werden</h1>
        <p>{err instanceof Error ? err.message : String(err)}</p>
      </div>,
    );
    return;
  }

  const { setWorld, setSaveStatus } = useWorld.getState();
  setWorld(world);

  const autosave = createAutosave((w) => storage.saveWorld(w), setSaveStatus);
  useWorld.subscribe((state, prev) => {
    if (state.world !== prev.world) autosave.schedule(state.world);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void autosave.flush();
  });
  window.addEventListener("pagehide", () => void autosave.flush());
  if (isTauri()) {
    // Vor dem Schließen des Fensters alles Vorgemerkte schreiben.
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().onCloseRequested(() => autosave.flush());
  }

  root.render(
    <StrictMode>
      <StorageProvider storage={storage}>
        <App />
      </StorageProvider>
    </StrictMode>,
  );
}

void start();
