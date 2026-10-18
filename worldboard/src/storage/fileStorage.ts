import type { World } from "../core/types";
import { assetName } from "./hash";
import type { StorageAdapter } from "./StorageAdapter";

/** Die Dateifunktionen, die der Speicher braucht. In der App kommen sie von Tauri, in Tests aus dem Speicher. */
export interface FileSystem {
  exists(path: string): Promise<boolean>;
  mkdir(path: string): Promise<void>;
  readText(path: string): Promise<string>;
  writeText(path: string, data: string): Promise<void>;
  readBinary(path: string): Promise<Uint8Array>;
  writeBinary(path: string, data: Uint8Array): Promise<void>;
  rename(from: string, to: string): Promise<void>;
  remove(path: string): Promise<void>;
  /** Dateinamen (ohne Pfad) in einem Ordner. */
  list(dir: string): Promise<string[]>;
}

export interface FileStorageOptions {
  /** Wie viele tägliche Sicherungen behalten werden. */
  keepBackups?: number;
  today?: () => Date;
}

const MIME: { [ext: string]: string } = {
  png: "image/png",
  jpg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  svg: "image/svg+xml",
  avif: "image/avif",
};

const BACKUP_PATTERN = /^world-\d{4}-\d{2}-\d{2}\.json$/;

function dateStamp(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * Speichert eine Welt als Ordner:
 *   world.json   die Welt (lesbares JSON)
 *   assets/      Bilder, benannt nach ihrem Inhalts-Hash
 *   backups/     eine Kopie von world.json pro Tag
 */
export function createFileStorage(fs: FileSystem, dir: string, options: FileStorageOptions = {}): StorageAdapter {
  const keep = options.keepBackups ?? 14;
  const today = options.today ?? (() => new Date());
  const worldPath = `${dir}/world.json`;
  const assetsDir = `${dir}/assets`;
  const backupsDir = `${dir}/backups`;

  let ready: Promise<void> | null = null;
  const ensureDirs = () =>
    (ready ??= (async () => {
      for (const d of [dir, assetsDir, backupsDir]) if (!(await fs.exists(d))) await fs.mkdir(d);
    })());

  async function backup(text: string) {
    const name = `world-${dateStamp(today())}.json`;
    if (await fs.exists(`${backupsDir}/${name}`)) return;
    await fs.writeText(`${backupsDir}/${name}`, text);
    const old = (await fs.list(backupsDir)).filter((n) => BACKUP_PATTERN.test(n)).sort().slice(0, -keep);
    for (const n of old) await fs.remove(`${backupsDir}/${n}`);
  }

  return {
    location: dir,

    async loadWorld() {
      await ensureDirs();
      if (!(await fs.exists(worldPath))) return null;
      const text = await fs.readText(worldPath);
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(`${worldPath} ist beschädigt. Ältere Stände liegen in ${backupsDir}.`);
      }
      // Die Sicherung entsteht beim Laden, also vom letzten gut gespeicherten Stand.
      await backup(text);
      return data;
    },

    async saveWorld(world: World) {
      await ensureDirs();
      // Erst in eine Zwischendatei schreiben, dann umbenennen:
      // Ein Absturz mitten im Schreiben kann world.json so nicht zerstören.
      const tmp = `${worldPath}.tmp`;
      await fs.writeText(tmp, JSON.stringify(world, null, 2));
      await fs.rename(tmp, worldPath);
    },

    async saveAsset(blob: Blob) {
      await ensureDirs();
      const name = await assetName(blob);
      const path = `${assetsDir}/${name}`;
      if (!(await fs.exists(path))) await fs.writeBinary(path, new Uint8Array(await blob.arrayBuffer()));
      return name;
    },

    async loadAsset(name: string) {
      const path = `${assetsDir}/${name}`;
      if (!(await fs.exists(path))) return null;
      const bytes = await fs.readBinary(path);
      const ext = name.split(".").pop() ?? "";
      return new Blob([bytes as BlobPart], { type: MIME[ext] ?? "application/octet-stream" });
    },
  };
}
