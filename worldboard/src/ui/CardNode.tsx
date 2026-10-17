import { Handle, NodeResizeControl, Position, useConnection, type Node, type NodeProps } from "@xyflow/react";
import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { CARD_TYPES } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { Card, CardType } from "../core/types";
import { firstImageFile, useAssetUrl, useStorage } from "./assets";
import { ChevronIcon, TypeIcon } from "./icons";

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
        <label className="card-type nodrag">
          <TypeIcon type={card.type} size={13} />
          <select
            value={card.type}
            aria-label="Kartentyp"
            onChange={(e) => set({ type: e.target.value as CardType })}
          >
            {CARD_TYPES.map((t) => (
              <option key={t.type} value={t.type}>
                {t.label}
              </option>
            ))}
          </select>
          <ChevronIcon size={12} />
        </label>
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
