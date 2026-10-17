import type { World } from "../core/types";

export interface Autosave {
  /** Merkt die Welt zum Speichern vor; gespeichert wird erst nach einer kurzen Pause. */
  schedule(world: World): void;
  /** Speichert sofort, falls etwas vorgemerkt ist. */
  flush(): Promise<void>;
}

export function createAutosave(
  save: (world: World) => Promise<void>,
  onStatus: (status: "saving" | "saved" | "error") => void,
  delayMs = 500,
): Autosave {
  let pending: World | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let running: Promise<void> = Promise.resolve();

  const flush = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    const world = pending;
    pending = null;
    if (!world) return running;
    running = running
      .then(() => save(world))
      .then(
        () => onStatus(pending ? "saving" : "saved"),
        (err) => {
          console.error("Speichern fehlgeschlagen", err);
          onStatus("error");
        },
      );
    return running;
  };

  return {
    schedule(world) {
      pending = world;
      onStatus("saving");
      if (timer) clearTimeout(timer);
      timer = setTimeout(flush, delayMs);
    },
    flush,
  };
}
