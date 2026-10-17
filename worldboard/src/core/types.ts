export type CardType = "notiz" | "figur" | "ort" | "fraktion" | "ereignis" | "gegenstand";

/** Felder, die jeder gespeicherte Datensatz hat. Grundlage für den späteren Sync. */
interface BaseRecord {
  id: string;
  updatedAt: number;
  /** Gelöscht-Vermerk statt echtem Löschen, damit Löschungen später synchronisiert werden können. */
  deletedAt: number | null;
}

export interface Board extends BaseRecord {
  name: string;
  parentId: string | null;
}

export interface Card extends BaseRecord {
  boardId: string;
  type: CardType;
  x: number;
  y: number;
  /** Breite in Pixeln; null = Standardbreite. Die Höhe ergibt sich aus dem Inhalt. */
  width: number | null;
  title: string;
  text: string;
  /** Dateiname des Bildes im Asset-Speicher (Inhalts-Hash + Endung). */
  image: string | null;
  /** Reserviert für eigene Felder pro Typ (Roadmap Stufe 3). */
  fields: { [key: string]: string };
}

export interface Edge extends BaseRecord {
  boardId: string;
  from: string;
  to: string;
  /** Reserviert für beschriftete Verbindungen (Roadmap Stufe 2). */
  label: string;
}

export interface World {
  schemaVersion: 1;
  boards: Board[];
  cards: Card[];
  edges: Edge[];
}
