import { create } from "zustand";

/**
 * Welches Kartenmenü gerade offen ist. Die Menüs liegen fest über der Leinwand (nicht in der Karte),
 * damit sie beim Zoomen lesbar bleiben; x/y sind Bildschirmkoordinaten.
 */
export type OpenMenu =
  | { kind: "type"; cardId: string; x: number; y: number }
  | { kind: "context"; cardId: string; x: number; y: number };

interface MenuState {
  menu: OpenMenu | null;
  open: (menu: OpenMenu) => void;
  close: () => void;
}

export const useMenu = create<MenuState>()((set) => ({
  menu: null,
  open: (menu) => set({ menu }),
  close: () => set({ menu: null }),
}));
