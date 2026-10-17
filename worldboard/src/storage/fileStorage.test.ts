import { describe, expect, it } from "vitest";
import { emptyWorld, migrate } from "../core/migrations";
import { addCard } from "../core/world";
import { createFileStorage, type FileSystem } from "./fileStorage";

/** Ein Dateisystem im Speicher, das wie das echte fehlschlägt, wenn Ordner fehlen. */
function memoryFs() {
  const files = new Map<string, Uint8Array | string>();
  const dirs = new Set<string>();
  const parent = (p: string) => p.slice(0, p.lastIndexOf("/"));
  const needDir = (p: string) => {
    if (!dirs.has(parent(p))) throw new Error(`Ordner fehlt: ${parent(p)}`);
  };
  const fs: FileSystem = {
    exists: async (p) => files.has(p) || dirs.has(p),
    mkdir: async (p) => void dirs.add(p),
    readText: async (p) => {
      const v = files.get(p);
      if (typeof v !== "string") throw new Error(`nicht gefunden: ${p}`);
      return v;
    },
    writeText: async (p, d) => {
      needDir(p);
      files.set(p, d);
    },
    readBinary: async (p) => {
      const v = files.get(p);
      if (!(v instanceof Uint8Array)) throw new Error(`nicht gefunden: ${p}`);
      return v;
    },
    writeBinary: async (p, d) => {
      needDir(p);
      files.set(p, d);
    },
    rename: async (from, to) => {
      const v = files.get(from);
      if (v === undefined) throw new Error(`nicht gefunden: ${from}`);
      files.delete(from);
      files.set(to, v);
    },
    remove: async (p) => void files.delete(p),
    list: async (d) => [...files.keys()].filter((p) => parent(p) === d).map((p) => p.slice(d.length + 1)),
  };
  return { fs, files };
}

const DIR = "/home/u/Documents/Worldboard";
const day = (d: string) => () => new Date(`${d}T12:00:00`);

describe("Datei-Speicher", () => {
  it("legt die Ordner an und meldet eine neue Welt als leer", async () => {
    const { fs } = memoryFs();
    const storage = createFileStorage(fs, DIR);
    expect(await storage.loadWorld()).toBeNull();
    expect(await fs.exists(`${DIR}/assets`)).toBe(true);
    expect(await fs.exists(`${DIR}/backups`)).toBe(true);
    expect(storage.location).toBe(DIR);
  });

  it("speichert lesbares JSON über eine Zwischendatei und lädt es identisch", async () => {
    const { fs, files } = memoryFs();
    const storage = createFileStorage(fs, DIR);
    const world = addCard(emptyWorld(1), { type: "figur", x: 1, y: 2, title: "Mira" }, 3, "a");
    await storage.saveWorld(world);
    expect(files.has(`${DIR}/world.json.tmp`)).toBe(false);
    expect(files.get(`${DIR}/world.json`)).toContain('"title": "Mira"');
    expect(migrate(await createFileStorage(fs, DIR).loadWorld())).toEqual(world);
  });

  it("meldet eine beschädigte Datei, statt sie zu überschreiben", async () => {
    const { fs, files } = memoryFs();
    await fs.mkdir(DIR);
    files.set(`${DIR}/world.json`, "{ kaputt");
    await expect(createFileStorage(fs, DIR).loadWorld()).rejects.toThrow(/beschädigt.*backups/);
    expect(files.get(`${DIR}/world.json`)).toBe("{ kaputt");
  });

  it("legt einmal pro Tag eine Sicherung an und behält nur die neuesten", async () => {
    const { fs, files } = memoryFs();
    await createFileStorage(fs, DIR).saveWorld(emptyWorld(1));
    for (const d of ["2026-10-01", "2026-10-02", "2026-10-02", "2026-10-03", "2026-10-04"]) {
      await createFileStorage(fs, DIR, { today: day(d), keepBackups: 3 }).loadWorld();
    }
    const backups = [...files.keys()].filter((p) => p.includes("/backups/")).sort();
    expect(backups).toEqual([
      `${DIR}/backups/world-2026-10-02.json`,
      `${DIR}/backups/world-2026-10-03.json`,
      `${DIR}/backups/world-2026-10-04.json`,
    ]);
  });

  it("speichert Bilder unter ihrem Hash und liest sie mit Dateityp zurück", async () => {
    const { fs, files } = memoryFs();
    const storage = createFileStorage(fs, DIR);
    const name = await storage.saveAsset(new Blob(["pixel"], { type: "image/png" }));
    expect(await storage.saveAsset(new Blob(["pixel"], { type: "image/png" }))).toBe(name);
    expect([...files.keys()].filter((p) => p.includes("/assets/"))).toHaveLength(1);
    const blob = await storage.loadAsset(name);
    expect(blob?.type).toBe("image/png");
    expect(await blob?.text()).toBe("pixel");
    expect(await storage.loadAsset("fehlt.png")).toBeNull();
  });
});
