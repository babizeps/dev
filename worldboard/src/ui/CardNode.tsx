import {
  Handle,
  NodeResizeControl,
  NodeToolbar,
  Position,
  useConnection,
  useStore,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { cardTypeLabel } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { Card } from "../core/types";
import { firstImageFile, useAssetUrl, useStorage } from "./assets";
import { ChevronIcon, MoreIcon, TypeIcon } from "./icons";
import { openContextMenu, useMenu } from "./menuState";
import { TypeDots } from "./TypeDots";

export type CardNodeType = Node<{ card: Card }, "card">;

export const CARD_WIDTH = 260;
const MIN_WIDTH = 180;
const MAX_WIDTH = 640;

const MISSING: Card | undefined = undefined;

/** Feste, leichte Schräglage pro Karte für den Skizzenbuch-Stil (-1 bis 1). */
function tilt(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  return ((Math.abs(h) % 21) - 10) / 10;
}

function AutoTextarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { value: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [props.value]);
  return <textarea ref={ref} rows={1} {...props} />;
}

export function CardNode({ id, data, selected }: NodeProps<CardNodeType>) {
  // Direkt aus dem Store lesen: Die Knotendaten kommen einen Render später an,
  // und beim schnellen Tippen würden sonst Buchstaben verloren gehen.
  const card = useWorld((s) => s.world.cards.find((c) => c.id === id) ?? MISSING) ?? data.card;
  const updateCard = useWorld((s) => s.updateCard);
  const focusCardId = useWorld((s) => s.focusCardId);
  const clearFocus = useWorld((s) => s.clearFocus);
  const storage = useStorage();
  const imageUrl = useAssetUrl(card.image);
  const titleRef = useRef<HTMLInputElement>(null);
  const [dropActive, setDropActive] = useState(false);
  const openMenu = useMenu((s) => s.open);
  const menuOpenHere = useMenu((s) => s.menu?.cardId === id);
  const onlySelected = useStore((s) => s.nodes.reduce((n, node) => n + (node.selected ? 1 : 0), 0) === 1);

  // Während eine Verbindung gezogen wird, wird die ganze Karte zum Ziel.
  const connection = useConnection();
  const isConnectTarget = connection.inProgress && connection.fromNode.id !== id;

  useEffect(() => {
    if (focusCardId !== id) return;
    // React Flow zeigt neue Knoten erst nach dem Messen an; bis dahin lässt sich nichts fokussieren.
    let tries = 0;
    let frame = 0;
    const tryFocus = () => {
      const el = titleRef.current;
      el?.focus();
      if (el && document.activeElement !== el && tries++ < 20) frame = requestAnimationFrame(tryFocus);
      else clearFocus();
    };
    tryFocus();
    return () => cancelAnimationFrame(frame);
  }, [focusCardId, id, clearFocus]);

  const set = (patch: Parameters<typeof updateCard>[1]) => updateCard(id, patch);

  const onDrop = async (e: React.DragEvent) => {
    const file = firstImageFile(e.dataTransfer);
    setDropActive(false);
    if (!file) return;
    e.preventDefault();
    e.stopPropagation();
    set({ image: await storage.saveAsset(file) });
  };

  return (
    <div
      className={["card", selected && "is-selected", dropActive && "is-drop", isConnectTarget && "is-connect-target"]
        .filter(Boolean)
        .join(" ")}
      data-type={card.type}
      data-testid="card"
      style={{ "--tilt": tilt(id) } as CSSProperties}
      onDragOver={(e) => {
        if (!e.dataTransfer.types.includes("Files")) return;
        e.preventDefault();
        e.stopPropagation();
        setDropActive(true);
      }}
      onDragLeave={() => setDropActive(false)}
      onDrop={onDrop}
    >
      <span className="card-tape" aria-hidden="true" />
      {imageUrl && (
        <div className="card-image">
          <img src={imageUrl} alt={card.title ? `Bild zu ${card.title}` : "Bild"} draggable={false} />
          <button
            type="button"
            className="card-image-remove nodrag"
            aria-label="Bild entfernen"
            onClick={() => set({ image: null })}
          >
            ×
          </button>
        </div>
      )}
      <div className="card-body">
        <button
          type="button"
          className="card-type nodrag"
          data-menu-trigger
          aria-haspopup="menu"
          aria-expanded={menuOpenHere}
          aria-label={`Kartentyp: ${cardTypeLabel(card.type)}`}
          onClick={(e) => {
            if (menuOpenHere) return useMenu.getState().close();
            const r = e.currentTarget.getBoundingClientRect();
            openMenu({ kind: "type", cardId: id, x: r.left - 4, y: r.bottom + 6 });
          }}
        >
          <TypeIcon type={card.type} size={13} />
          {cardTypeLabel(card.type)}
          <ChevronIcon size={12} />
        </button>
        <input
          ref={titleRef}
          className="card-title nodrag"
          value={card.title}
          placeholder="Titel"
          aria-label="Titel"
          onChange={(e) => set({ title: e.target.value })}
        />
        <AutoTextarea
          className="card-text nodrag nowheel"
          value={card.text}
          placeholder="Beschreibung …"
          aria-label="Beschreibung"
          onChange={(e) => set({ text: e.target.value })}
        />
      </div>
      <Handle
        type="target"
        position={Position.Left}
        isConnectableStart={false}
        className={`handle-target${isConnectTarget ? " is-active" : ""}`}
      />
      <Handle type="source" position={Position.Right} className="handle-source" title="Ziehen zum Verbinden" />
      <NodeToolbar isVisible={selected && onlySelected && !menuOpenHere} position={Position.Top} offset={14} align="start">
        <div className="card-toolbar">
          <TypeDots current={card.type} onPick={(type) => set({ type })} />
          <span className="card-toolbar-separator" aria-hidden="true" />
          <button
            type="button"
            className="type-dot is-more"
            data-menu-trigger
            aria-label="Weitere Aktionen"
            aria-haspopup="menu"
            data-tip="Weitere Aktionen"
            onClick={() => openContextMenu(id)}
          >
            <MoreIcon size={16} />
          </button>
        </div>
      </NodeToolbar>
      {selected && (
        <NodeResizeControl
          position="bottom-right"
          resizeDirection="horizontal"
          minWidth={MIN_WIDTH}
          maxWidth={MAX_WIDTH}
          className="card-resize"
          onResizeEnd={(_, p) => set({ width: Math.round(p.width) })}
        >
          <span aria-hidden="true" />
        </NodeResizeControl>
      )}
    </div>
  );
}
