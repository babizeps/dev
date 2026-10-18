import { CARD_TYPES } from "../core/cardTypes";
import type { CardType } from "../core/types";
import { TypeIcon } from "./icons";

/** Die sechs runden Typ-Knöpfe – dasselbe Bauteil in der Leiste über der Karte und im Rechtsklick-Menü. */
export function TypeDots({ current, onPick }: { current: CardType; onPick: (type: CardType) => void }) {
  return (
    <div className="type-dots" role="group" aria-label="Kartentyp">
      {CARD_TYPES.map((t, i) => (
        <button
          key={t.type}
          type="button"
          className="type-dot"
          data-type={t.type}
          aria-label={t.label}
          aria-pressed={t.type === current}
          data-tip={`${t.label} · ${i + 1}`}
          onClick={() => onPick(t.type)}
        >
          <TypeIcon type={t.type} size={15} />
        </button>
      ))}
    </div>
  );
}
