import { documentDir, join } from "@tauri-apps/api/path";
import { exists, mkdir, readDir, readFile, readTextFile, remove, rename, writeFile, writeTextFile } from "@tauri-apps/plugin-fs";
import { createFileStorage, type FileSystem } from "./fileStorage";
import type { StorageAdapter } from "./StorageAdapter";

const tauriFs: FileSystem = {
  exists: (path) => exists(path),
  mkdir: (path) => mkdir(path, { recursive: true }),
  readText: (path) => readTextFile(path),
  writeText: (path, data) => writeTextFile(path, data),
  readBinary: (path) => readFile(path),
  writeBinary: (path, data) => writeFile(path, data),
  rename: (from, to) => rename(from, to),
  remove: (path) => remove(path),
  list: async (dir) => (await readDir(dir)).filter((e) => e.isFile).map((e) => e.name),
};

/** Die Welt liegt in Dokumente/Worldboard (diesen Ordner erlaubt src-tauri/capabilities/default.json). */
export async function createTauriStorage(): Promise<StorageAdapter> {
  return createFileStorage(tauriFs, await join(await documentDir(), "Worldboard"));
}
