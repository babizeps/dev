import "fake-indexeddb/auto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { emptyWorld, migrate } from "../core/migrations";
import { addCard } from "../core/world";
import { createAutosave } from "./autosave";
import { createIndexedDbStorage } from "./indexedDb";

let dbCounter = 0;
const freshStorage = () => createIndexedDbStorage(`test-${dbCounter++}`);

describe("IndexedDB-Speicher", () => {
  it("gibt null zurück, solange nichts gespeichert ist", async () => {
    expect(await freshStorage().loadWorld()).toBeNull();
  });

  it("lädt eine gespeicherte Welt identisch wieder", async () => {
    const storage = freshStorage();
    const world = addCard(emptyWorld(1), { type: "figur", x: 1, y: 2, title: "Mira" }, 3, "a");
    await storage.saveWorld(world);
    expect(migrate(await storage.loadWorld())).toEqual(world);
  });

  it("speichert gleiche Bilder nur einmal unter ihrem Hash", async () => {
    const storage = freshStorage();
    const a = await storage.saveAsset(new Blob(["pixel"], { type: "image/png" }));
    const b = await storage.saveAsset(new Blob(["pixel"], { type: "image/png" }));
    const c = await storage.saveAsset(new Blob(["anders"], { type: "image/png" }));
    expect(a).toMatch(/^[0-9a-f]{64}\.png$/);
    expect(b).toBe(a);
    expect(c).not.toBe(a);
    const loaded = await storage.loadAsset(a);
    expect(await loaded?.text()).toBe("pixel");
    expect(await storage.loadAsset("fehlt.png")).toBeNull();
  });
});

describe("Auto-Speichern", () => {
  afterEach(() => vi.useRealTimers());

  it("fasst schnelle Änderungen zu einem Speichern zusammen", async () => {
    vi.useFakeTimers();
    const save = vi.fn().mockResolvedValue(undefined);
    const status = vi.fn();
    const autosave = createAutosave(save, status, 500);
    const w1 = emptyWorld(1);
    const w2 = emptyWorld(2);
    autosave.schedule(w1);
    autosave.schedule(w2);
    expect(status).toHaveBeenLastCalledWith("saving");
    await vi.advanceTimersByTimeAsync(499);
    expect(save).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(save).toHaveBeenCalledExactlyOnceWith(w2);
    expect(status).toHaveBeenLastCalledWith("saved");
  });

  it("speichert bei flush sofort und meldet Fehler", async () => {
    const save = vi.fn().mockRejectedValue(new Error("voll"));
    const status = vi.fn();
    vi.spyOn(console, "error").mockImplementation(() => {});
    const autosave = createAutosave(save, status, 10_000);
    autosave.schedule(emptyWorld(1));
    await autosave.flush();
    expect(save).toHaveBeenCalledOnce();
    expect(status).toHaveBeenLastCalledWith("error");
  });
});
