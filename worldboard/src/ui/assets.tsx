import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { StorageAdapter } from "../storage/StorageAdapter";

const StorageContext = createContext<StorageAdapter | null>(null);

export function StorageProvider({ storage, children }: { storage: StorageAdapter; children: ReactNode }) {
  return <StorageContext.Provider value={storage}>{children}</StorageContext.Provider>;
}

export function useStorage(): StorageAdapter {
  const storage = useContext(StorageContext);
  if (!storage) throw new Error("useStorage braucht einen StorageProvider");
  return storage;
}

// Bilder ändern sich nie (Name = Inhalts-Hash), daher reicht eine URL pro Bild für die ganze Sitzung.
const urlCache = new Map<string, Promise<string | null>>();

export function useAssetUrl(name: string | null): string | null {
  const storage = useStorage();
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!name) {
      setUrl(null);
      return;
    }
    let cancelled = false;
    let promise = urlCache.get(name);
    if (!promise) {
      promise = storage.loadAsset(name).then((blob) => (blob ? URL.createObjectURL(blob) : null));
      urlCache.set(name, promise);
    }
    promise.then((u) => !cancelled && setUrl(u));
    return () => {
      cancelled = true;
    };
  }, [name, storage]);

  return url;
}

export function firstImageFile(data: DataTransfer | null): File | null {
  if (!data) return null;
  return Array.from(data.files).find((f) => f.type.startsWith("image/")) ?? null;
}
