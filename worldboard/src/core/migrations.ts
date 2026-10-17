import { isCardType } from "./cardTypes";
import type { Board, Card, Edge, World } from "./types";

export const CURRENT_SCHEMA_VERSION = 1;
export const ROOT_BOARD_ID = "root";

export function emptyWorld(now = Date.now()): World {
  return {
    schemaVersion: 1,
    boards: [{ id: ROOT_BOARD_ID, name: "Meine Welt", parentId: null, updatedAt: now, deletedAt: null }],
    cards: [],
    edges: [],
  };
}

export class UnsupportedSchemaError extends Error {
  constructor(version: unknown) {
    super(`Die gespeicherte Welt hat Format-Version ${String(version)}, diese App kennt nur bis ${CURRENT_SCHEMA_VERSION}.`);
  }
}

type Loose = { [key: string]: unknown };

const str = (v: unknown, fallback = "") => (typeof v === "string" ? v : fallback);
const num = (v: unknown, fallback = 0) => (typeof v === "number" && Number.isFinite(v) ? v : fallback);
const numOrNull = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const list = (v: unknown): Loose[] =>
  Array.isArray(v) ? v.filter((x): x is Loose => typeof x === "object" && x !== null) : [];

/**
 * Bringt gespeicherte Daten auf das aktuelle Format.
 * Fehlende Felder bekommen Standardwerte; eine neuere, unbekannte Version wird abgelehnt,
 * damit die App sie nicht beim nächsten Speichern überschreibt.
 */
export function migrate(raw: unknown): World {
  if (raw === null || raw === undefined) return emptyWorld();
  if (typeof raw !== "object") throw new Error("Gespeicherte Welt ist kein Objekt.");
  const data = raw as Loose;
  const version = data.schemaVersion ?? 1;
  if (version !== 1) throw new UnsupportedSchemaError(version);

  const boards: Board[] = list(data.boards).map((b) => ({
    id: str(b.id),
    name: str(b.name, "Meine Welt"),
    parentId: typeof b.parentId === "string" ? b.parentId : null,
    updatedAt: num(b.updatedAt),
    deletedAt: numOrNull(b.deletedAt),
  }));
  if (!boards.some((b) => b.id === ROOT_BOARD_ID)) boards.unshift(emptyWorld(0).boards[0]);

  const cards: Card[] = list(data.cards).map((c) => ({
    id: str(c.id),
    boardId: str(c.boardId, ROOT_BOARD_ID),
    type: isCardType(c.type) ? c.type : "notiz",
    x: num(c.x),
    y: num(c.y),
    title: str(c.title),
    text: str(c.text),
    image: typeof c.image === "string" ? c.image : null,
    fields: typeof c.fields === "object" && c.fields !== null ? (c.fields as Card["fields"]) : {},
    updatedAt: num(c.updatedAt),
    deletedAt: numOrNull(c.deletedAt),
  }));

  const edges: Edge[] = list(data.edges).map((e) => ({
    id: str(e.id),
    boardId: str(e.boardId, ROOT_BOARD_ID),
    from: str(e.from),
    to: str(e.to),
    label: str(e.label),
    updatedAt: num(e.updatedAt),
    deletedAt: numOrNull(e.deletedAt),
  }));

  return {
    schemaVersion: 1,
    boards: boards.filter((b) => b.id),
    cards: cards.filter((c) => c.id),
    edges: edges.filter((e) => e.id && e.from && e.to),
  };
}
