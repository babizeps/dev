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
import { App } from "./ui/App";
import { StorageProvider } from "./ui/assets";
import { applyStoredTheme } from "./ui/theme";

const storage = createIndexedDbStorage();
const root = createRoot(document.getElementById("root")!);
applyStoredTheme();

async function start() {
  // Bittet den Browser, den Speicher nicht von selbst aufzuräumen.
  navigator.storage?.persist?.().catch(() => {});

  let world;
  try {
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

  root.render(
    <StrictMode>
      <StorageProvider storage={storage}>
        <App />
      </StorageProvider>
    </StrictMode>,
  );
}

void start();
