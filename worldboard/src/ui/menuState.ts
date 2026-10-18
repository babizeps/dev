import { create } from "zustand";

/**
 * Das gerade offene Typ-Menü einer Karte. Es liegt fest über der Leinwand (nicht in der Karte),
 * damit es beim Zoomen lesbar bleibt; x/y sind Bildschirmkoordinaten.
 */
export type OpenMenu = { kind: "type"; cardId: string; x: number; y: number };

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
