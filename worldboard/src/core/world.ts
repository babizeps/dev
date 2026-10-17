import { ROOT_BOARD_ID } from "./migrations";
import type { Card, CardType, Edge, World } from "./types";

/**
 * Alle Änderungen an einer Welt laufen über diese Funktionen.
 * Sie sind rein (geben eine neue Welt zurück) und setzen updatedAt immer selbst,
 * damit der spätere Sync jede Änderung erkennt.
 */

export const newId = (): string => crypto.randomUUID();

export function liveCards(world: World): Card[] {
  return world.cards.filter((c) => c.deletedAt === null);
}

export function liveEdges(world: World): Edge[] {
  const live = new Set(liveCards(world).map((c) => c.id));
  return world.edges.filter((e) => e.deletedAt === null && live.has(e.from) && live.has(e.to));
}

export interface NewCard {
  type: CardType;
  x: number;
  y: number;
  title?: string;
  image?: string | null;
}

export function addCard(world: World, input: NewCard, now = Date.now(), id: string = newId()): World {
  const card: Card = {
    id,
    boardId: ROOT_BOARD_ID,
    type: input.type,
    x: input.x,
    y: input.y,
    title: input.title ?? "",
    text: "",
    image: input.image ?? null,
    fields: {},
    updatedAt: now,
    deletedAt: null,
  };
  return { ...world, cards: [...world.cards, card] };
}

export type CardPatch = Partial<Pick<Card, "type" | "title" | "text" | "image" | "x" | "y">>;

export function updateCard(world: World, id: string, patch: CardPatch, now = Date.now()): World {
  let changed = false;
  const cards = world.cards.map((c) => {
    if (c.id !== id || c.deletedAt !== null) return c;
    const keys = Object.keys(patch) as (keyof CardPatch)[];
    if (keys.every((k) => c[k] === patch[k])) return c;
    changed = true;
    return { ...c, ...patch, updatedAt: now };
  });
  return changed ? { ...world, cards } : world;
}

export function connect(world: World, from: string, to: string, now = Date.now(), id: string = newId()): World {
  if (from === to) return world;
  const live = new Set(liveCards(world).map((c) => c.id));
  if (!live.has(from) || !live.has(to)) return world;
  const exists = liveEdges(world).some(
    (e) => (e.from === from && e.to === to) || (e.from === to && e.to === from),
  );
  if (exists) return world;
  const edge: Edge = { id, boardId: ROOT_BOARD_ID, from, to, label: "", updatedAt: now, deletedAt: null };
  return { ...world, edges: [...world.edges, edge] };
}

/** Markiert Karten als gelöscht, zusammen mit allen ihren Verbindungen. */
export function removeCards(world: World, ids: string[], now = Date.now()): World {
  const remove = new Set(ids);
  if (remove.size === 0) return world;
  return {
    ...world,
    cards: world.cards.map((c) =>
      remove.has(c.id) && c.deletedAt === null ? { ...c, deletedAt: now, updatedAt: now } : c,
    ),
    edges: world.edges.map((e) =>
      (remove.has(e.from) || remove.has(e.to)) && e.deletedAt === null
        ? { ...e, deletedAt: now, updatedAt: now }
        : e,
    ),
  };
}

export function removeEdges(world: World, ids: string[], now = Date.now()): World {
  const remove = new Set(ids);
  if (remove.size === 0) return world;
  return {
    ...world,
    edges: world.edges.map((e) =>
      remove.has(e.id) && e.deletedAt === null ? { ...e, deletedAt: now, updatedAt: now } : e,
    ),
  };
}
