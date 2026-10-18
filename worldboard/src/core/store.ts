import { create } from "zustand";
import { emptyWorld } from "./migrations";
import type { World } from "./types";
import {
  addCard,
  connect,
  duplicateCard,
  moveCards,
  removeCards,
  removeEdges,
  restore,
  updateCard,
  type CardPatch,
  type NewCard,
} from "./world";

export type SaveStatus = "saved" | "saving" | "error";

const HISTORY_LIMIT = 200;
/** Änderungen am selben Textfeld innerhalb dieser Zeit sind ein einziger Rückgängig-Schritt. */
const GROUP_MS = 1000;

interface WorldState {
  world: World;
  saveStatus: SaveStatus;
  /** Zuletzt angelegte Karte; die Oberfläche setzt dort den Fokus. Wird nicht gespeichert. */
  focusCardId: string | null;
  /** Frühere Stände für Rückgängig (ältester zuerst) und spätere für Wiederholen. */
  past: World[];
  future: World[];
  lastGroup: string | null;
  lastChangeAt: number;

  /** Lädt eine Welt und beginnt einen leeren Verlauf. */
  setWorld: (world: World) => void;
  setSaveStatus: (status: SaveStatus) => void;
  addCard: (input: NewCard) => string;
  updateCard: (id: string, patch: CardPatch) => void;
  moveCards: (positions: { id: string; x: number; y: number }[]) => void;
  connect: (from: string, to: string) => void;
  /** Kopiert eine Karte und gibt die neue ID zurück. */
  duplicate: (id: string) => string;
  remove: (cardIds: string[], edgeIds: string[]) => void;
  undo: () => void;
  redo: () => void;
  clearFocus: () => void;
}

export const useWorld = create<WorldState>()((set, get) => {
  /** Übernimmt eine Änderung und merkt sich den vorherigen Stand für Rückgängig. */
  const commit = (next: World, group: string | null = null, extra: Partial<WorldState> = {}) => {
    const { world, past, lastGroup, lastChangeAt } = get();
    if (next === world) return;
    const now = Date.now();
    const merge = group !== null && group === lastGroup && now - lastChangeAt < GROUP_MS;
    set({
      ...extra,
      world: next,
      past: merge ? past : [...past, world].slice(-HISTORY_LIMIT),
      future: [],
      lastGroup: group,
      lastChangeAt: now,
    });
  };

  return {
    world: emptyWorld(),
    saveStatus: "saved",
    focusCardId: null,
    past: [],
    future: [],
    lastGroup: null,
    lastChangeAt: 0,

    setWorld: (world) => set({ world, past: [], future: [], lastGroup: null }),
    setSaveStatus: (saveStatus) => set({ saveStatus }),
    addCard: (input) => {
      const id = crypto.randomUUID();
      commit(addCard(get().world, input, Date.now(), id), null, { focusCardId: id });
      return id;
    },
    updateCard: (id, patch) => {
      const keys = Object.keys(patch).sort();
      // Tippen in Titel oder Text wird gebündelt, alles andere ist ein eigener Schritt.
      const isTyping = keys.every((k) => k === "title" || k === "text");
      commit(updateCard(get().world, id, patch), isTyping ? `${id}:${keys.join(",")}` : null);
    },
    moveCards: (positions) => commit(moveCards(get().world, positions)),
    connect: (from, to) => commit(connect(get().world, from, to)),
    duplicate: (id) => {
      const newId = crypto.randomUUID();
      commit(duplicateCard(get().world, id, Date.now(), newId));
      return newId;
    },
    remove: (cardIds, edgeIds) => commit(removeEdges(removeCards(get().world, cardIds), edgeIds)),
    undo: () => {
      const { world, past, future } = get();
      const previous = past[past.length - 1];
      if (!previous) return;
      set({ world: restore(world, previous), past: past.slice(0, -1), future: [...future, world], lastGroup: null });
    },
    redo: () => {
      const { world, past, future } = get();
      const next = future[future.length - 1];
      if (!next) return;
      set({ world: restore(world, next), past: [...past, world], future: future.slice(0, -1), lastGroup: null });
    },
    clearFocus: () => set({ focusCardId: null }),
  };
});
