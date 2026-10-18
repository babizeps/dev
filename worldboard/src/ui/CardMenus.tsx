import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { CARD_TYPES } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { Card, CardType } from "../core/types";
import { useStorage } from "./assets";
import { CheckIcon, TypeIcon } from "./icons";
import { useMenu, type OpenMenu } from "./menuState";
import { TypeDots } from "./TypeDots";

const MENU_ITEMS = 'button:not(:disabled)[role^="menuitem"], .type-dot';

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

function ContextMenu({ menu, card, pick }: { menu: OpenMenu; card: Card; pick: (t: CardType) => void }) {
  const { ref, pos } = useMenuPlacement(menu);
  const { updateCard, duplicate, remove } = useWorld.getState();
  const close = useMenu((s) => s.close);
  const storage = useStorage();
  const fileInput = useRef<HTMLInputElement>(null);
  const run = (action: () => void) => () => {
    action();
    close();
  };

  return (
    <div ref={ref} className="card-menu" role="menu" aria-label="Karte" style={pos} onKeyDown={onMenuKeyDown}>
      <div className="card-menu-heading">Typ</div>
      <TypeDots current={card.type} onPick={pick} />
      <div className="card-menu-separator" role="separator" />
      <button type="button" role="menuitem" className="card-menu-item" onClick={() => fileInput.current?.click()}>
        <span className="card-menu-label">Bild hinzufügen …</span>
        <kbd>Strg V</kbd>
      </button>
      <input
        ref={fileInput}
        type="file"
        accept="image/*"
        hidden
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (file) updateCard(card.id, { image: await storage.saveAsset(file) });
          close();
        }}
      />
      <button type="button" role="menuitem" className="card-menu-item" onClick={run(() => duplicate(card.id))}>
        <span className="card-menu-label">Duplizieren</span>
        <kbd>Strg D</kbd>
      </button>
      <button
        type="button"
        role="menuitem"
        className="card-menu-item"
        disabled={card.width === null}
        onClick={run(() => updateCard(card.id, { width: null }))}
      >
        <span className="card-menu-label">Breite zurücksetzen</span>
      </button>
      <div className="card-menu-separator" role="separator" />
      <button type="button" role="menuitem" className="card-menu-item is-danger" onClick={run(() => remove([card.id], []))}>
        <span className="card-menu-label">Löschen</span>
        <kbd>Entf</kbd>
      </button>
    </div>
  );
}

/** Das gerade offene Kartenmenü (Typ-Menü an der Plakette oder Rechtsklick-Menü). */
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
  return menu.kind === "type" ? (
    <TypeMenu menu={menu} card={card} pick={pick} />
  ) : (
    <ContextMenu menu={menu} card={card} pick={pick} />
  );
}
