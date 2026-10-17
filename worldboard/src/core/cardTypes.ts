import type { CardType } from "./types";

export interface CardTypeInfo {
  type: CardType;
  label: string;
}

/** Reihenfolge = Reihenfolge in der Werkzeugleiste. Farben kommen aus dem Theme (styles.css). */
export const CARD_TYPES: CardTypeInfo[] = [
  { type: "notiz", label: "Notiz" },
  { type: "figur", label: "Figur" },
  { type: "ort", label: "Ort" },
  { type: "fraktion", label: "Fraktion" },
  { type: "ereignis", label: "Ereignis" },
  { type: "gegenstand", label: "Gegenstand" },
];

export function cardTypeLabel(type: CardType): string {
  return CARD_TYPES.find((t) => t.type === type)?.label ?? type;
}

export function isCardType(value: unknown): value is CardType {
  return CARD_TYPES.some((t) => t.type === value);
}
