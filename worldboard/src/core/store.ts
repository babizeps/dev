import { create } from "zustand";
import { emptyWorld } from "./migrations";
import type { World } from "./types";
import {
  addCard,
  connect,
  removeCards,
  removeEdges,
  updateCard,
  type CardPatch,
  type NewCard,
} from "./world";

export type SaveStatus = "saved" | "saving" | "error";

interface WorldState {
  world: World;
  saveStatus: SaveStatus;
  /** Zuletzt angelegte Karte; die Oberfläche setzt dort den Fokus. Wird nicht gespeichert. */
  focusCardId: string | null;

  setWorld: (world: World) => void;
  setSaveStatus: (status: SaveStatus) => void;
  addCard: (input: NewCard) => string;
  updateCard: (id: string, patch: CardPatch) => void;
  connect: (from: string, to: string) => void;
  removeCards: (ids: string[]) => void;
  removeEdges: (ids: string[]) => void;
  clearFocus: () => void;
}

export const useWorld = create<WorldState>()((set, get) => ({
  world: emptyWorld(),
  saveStatus: "saved",
  focusCardId: null,

  setWorld: (world) => set({ world }),
  setSaveStatus: (saveStatus) => set({ saveStatus }),
  addCard: (input) => {
    const id = crypto.randomUUID();
    set({ world: addCard(get().world, input, Date.now(), id), focusCardId: id });
    return id;
  },
  updateCard: (id, patch) => set({ world: updateCard(get().world, id, patch) }),
  connect: (from, to) => set({ world: connect(get().world, from, to) }),
  removeCards: (ids) => set({ world: removeCards(get().world, ids) }),
  removeEdges: (ids) => set({ world: removeEdges(get().world, ids) }),
  clearFocus: () => set({ focusCardId: null }),
}));
