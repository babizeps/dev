import type { World } from "../core/types";
import { assetName } from "./hash";
import type { StorageAdapter } from "./StorageAdapter";

const WORLD_STORE = "world";
const ASSET_STORE = "assets";
const WORLD_KEY = "current";

function open(dbName: string): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(dbName, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(WORLD_STORE);
      req.result.createObjectStore(ASSET_STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function run<T>(db: IDBDatabase, store: string, mode: IDBTransactionMode, op: (s: IDBObjectStore) => IDBRequest<T>) {
  return new Promise<T>((resolve, reject) => {
    const tx = db.transaction(store, mode);
    const req = op(tx.objectStore(store));
    tx.oncomplete = () => resolve(req.result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

/** Speicher im Browser (MVP). Für echte Welten kommt in Stufe 1 der Tauri-Dateispeicher. */
export function createIndexedDbStorage(dbName = "worldboard"): StorageAdapter {
  const db = open(dbName);
  return {
    async loadWorld() {
      return (await run(await db, WORLD_STORE, "readonly", (s) => s.get(WORLD_KEY))) ?? null;
    },
    async saveWorld(world: World) {
      await run(await db, WORLD_STORE, "readwrite", (s) => s.put(world, WORLD_KEY));
    },
    async saveAsset(blob: Blob) {
      const name = await assetName(blob);
      const conn = await db;
      const existing = await run(conn, ASSET_STORE, "readonly", (s) => s.getKey(name));
      if (existing === undefined) await run(conn, ASSET_STORE, "readwrite", (s) => s.put(blob, name));
      return name;
    },
    async loadAsset(name: string) {
      return ((await run(await db, ASSET_STORE, "readonly", (s) => s.get(name))) as Blob | undefined) ?? null;
    },
  };
}
