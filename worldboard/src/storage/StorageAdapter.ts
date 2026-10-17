import type { World } from "../core/types";

/**
 * Wo eine Welt liegt. Der Rest der App kennt nur diese Schnittstelle,
 * damit Browser-Speicher, Tauri-Dateien und später Sync austauschbar sind.
 */
export interface StorageAdapter {
  /** Für Menschen lesbarer Speicherort, z. B. ein Ordnerpfad. */
  location: string;
  /** Rohdaten oder null, wenn noch nichts gespeichert ist. Die Migration passiert im Core. */
  loadWorld(): Promise<unknown>;
  saveWorld(world: World): Promise<void>;
  /** Speichert ein Bild unter seinem Inhalts-Hash und gibt den Dateinamen zurück. */
  saveAsset(blob: Blob): Promise<string>;
  loadAsset(name: string): Promise<Blob | null>;
}
