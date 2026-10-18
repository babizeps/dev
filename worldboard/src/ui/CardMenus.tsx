import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { CARD_TYPES } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { Card, CardType } from "../core/types";
import { CheckIcon, TypeIcon } from "./icons";
import { useMenu, type OpenMenu } from "./menuState";

const MENU_ITEMS = 'button:not(:disabled)[role^="menuitem"]';

/** Hält ein fest positioniertes Menü im Fenster und setzt den Fokus hinein. */
function useMenuPlacement(menu: OpenMenu) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ left: menu.x, top: menu.y });

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const margin = 8;
    setPos({
      left: Math.max(margin, Math.min(menu.x, window.innerWidth - width - margin)),
      top: Math.max(margin, Math.min(menu.y, window.innerHeight - height - margin)),
    });
    const items = Array.from(el.querySelectorAll<HTMLElement>(MENU_ITEMS));
    (items.find((i) => i.getAttribute("aria-checked") === "true") ?? items[0])?.focus();
  }, [menu]);

  return { ref, pos };
}

/** Pfeiltasten wandern durch die Einträge. */
function onMenuKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
  if (!["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
  const items = Array.from(e.currentTarget.querySelectorAll<HTMLElement>(MENU_ITEMS));
  const i = items.indexOf(document.activeElement as HTMLElement);
  const next =
    e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : e.key === "ArrowDown" || e.key === "ArrowRight" ? i + 1 : i - 1;
  items[(next + items.length) % items.length]?.focus();
  e.preventDefault();
}

function TypeMenu({ menu, card, pick }: { menu: OpenMenu; card: Card; pick: (t: CardType) => void }) {
  const { ref, pos } = useMenuPlacement(menu);
  return (
    <div ref={ref} className="card-menu" role="menu" aria-label="Kartentyp" style={pos} onKeyDown={onMenuKeyDown}>
      {CARD_TYPES.map((t, i) => (
        <button
          key={t.type}
          type="button"
          role="menuitemradio"
          aria-checked={t.type === card.type}
          className="card-menu-item"
          data-type={t.type}
          onClick={() => pick(t.type)}
        >
          <span className="type-chip">
            <TypeIcon type={t.type} size={13} />
          </span>
          <span className="card-menu-label">{t.label}</span>
          {t.type === card.type ? <CheckIcon size={16} className="card-menu-check" /> : <kbd>{i + 1}</kbd>}
        </button>
      ))}
    </div>
  );
}

/** Das gerade offene Typ-Menü an der Plakette einer Karte. */
export function CardMenus() {
  const menu = useMenu((s) => s.menu);
  const close = useMenu((s) => s.close);
  const card = useWorld((s) => (menu ? s.world.cards.find((c) => c.id === menu.cardId && c.deletedAt === null) : undefined));
  const updateCard = useWorld((s) => s.updateCard);

  useEffect(() => {
    if (!menu) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!(e.target as HTMLElement).closest(".card-menu, [data-menu-trigger]")) close();
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", close);
    };
  }, [menu, close]);

  if (!menu || !card) return null;
  const pick = (type: CardType) => {
    updateCard(card.id, { type });
    close();
  };
  return <TypeMenu menu={menu} card={card} pick={pick} />;
}
