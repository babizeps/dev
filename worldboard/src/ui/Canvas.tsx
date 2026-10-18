import {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  BackgroundVariant,
  ReactFlow,
  useReactFlow,
  type Edge as FlowEdge,
  type EdgeChange,
  type NodeChange,
  type OnDelete,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CARD_TYPES } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { Card, Edge } from "../core/types";
import { liveCards, liveEdges } from "../core/world";
import { firstImageFile, useStorage } from "./assets";
import { CARD_WIDTH, CardNode, type CardNodeType } from "./CardNode";
import { FloatingEdge } from "./FloatingEdge";
import { useMenu } from "./menuState";
import type { ThemeMode } from "./theme";

const nodeTypes = { card: CardNode };
const edgeTypes = { floating: FloatingEdge };
// Feste Referenz: React Flow meldet seine Tasten-Listener bei jeder neuen Liste neu an.
const DELETE_KEYS = ["Delete", "Backspace"];

/** Knoten aus den Karten ableiten und dabei den Ansichtszustand der alten Knoten behalten. */
function toNodes(cards: Card[], prev: CardNodeType[]): CardNodeType[] {
  const byId = new Map(prev.map((n) => [n.id, n]));
  return cards.map((card) => {
    const old = byId.get(card.id);
    return {
      ...old,
      id: card.id,
      type: "card",
      // Während des Ziehens zeigt React Flow die Live-Position; gespeichert wird beim Loslassen.
      position: old?.dragging ? old.position : { x: card.x, y: card.y },
      // Die Breite kommt aus der Karte, die Höhe immer aus dem Inhalt.
      width: old?.resizing ? old.width : (card.width ?? CARD_WIDTH),
      height: undefined,
      data: { card },
    };
  });
}

function toEdges(links: Edge[], prev: FlowEdge[]): FlowEdge[] {
  const selected = new Set(prev.filter((e) => e.selected).map((e) => e.id));
  return links.map((l) => ({ id: l.id, source: l.from, target: l.to, type: "floating", selected: selected.has(l.id) }));
}

/**
 * Die Leinwand. Der Store ist die Wahrheit: Knoten und Linien werden aus der Welt abgeleitet.
 * React Flow hält nur Zustand der Ansicht (Auswahl, Position während des Ziehens, gemessene Größe).
 */
export function Canvas({ mode }: { mode: ThemeMode }) {
  const world = useWorld((s) => s.world);
  const { addCard, updateCard, moveCards, connect, remove, duplicate } = useWorld.getState();
  const openMenu = useMenu((s) => s.open);
  const closeMenu = useMenu((s) => s.close);
  const storage = useStorage();
  const { screenToFlowPosition, getNodes } = useReactFlow<CardNodeType>();

  const cards = useMemo(() => liveCards(world), [world]);
  const links = useMemo(() => liveEdges(world), [world]);

  const [nodes, setNodes] = useState<CardNodeType[]>(() => toNodes(cards, []));
  const [edges, setEdges] = useState<FlowEdge[]>(() => toEdges(links, []));
  // Nur beim Öffnen einer bestehenden Welt einpassen, nicht wenn die erste Karte entsteht.
  const [fitOnStart] = useState(() => cards.length > 0);

  useEffect(() => setNodes((prev) => toNodes(cards, prev)), [cards]);
  useEffect(() => setEdges((prev) => toEdges(links, prev)), [links]);

  const onNodesChange = useCallback((changes: NodeChange<CardNodeType>[]) => {
    // Entfernen läuft über onDelete und den Store, nicht über den Ansichtszustand.
    setNodes((nds) => applyNodeChanges(changes.filter((c) => c.type !== "remove"), nds));
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes.filter((c) => c.type !== "remove"), eds));
  }, []);

  const onDelete: OnDelete<CardNodeType> = useCallback(
    ({ nodes: deletedNodes, edges: deletedEdges }) =>
      remove(
        deletedNodes.map((n) => n.id),
        deletedEdges.map((e) => e.id),
      ),
    [remove],
  );

  const createAt = useCallback(
    (clientX: number, clientY: number, image: string | null = null) => {
      const p = screenToFlowPosition({ x: clientX, y: clientY });
      addCard({ type: "notiz", x: p.x - CARD_WIDTH / 2, y: p.y - 40, image });
    },
    [addCard, screenToFlowPosition],
  );

  // Bild aus der Zwischenablage: an die Karte, in der man gerade schreibt oder die ausgewählt ist,
  // sonst als neue Karte in der Mitte der Ansicht.
  useEffect(() => {
    const onPaste = async (e: ClipboardEvent) => {
      const file = Array.from(e.clipboardData?.files ?? []).find((f) => f.type.startsWith("image/"));
      if (!file) return;
      e.preventDefault();
      const focused = (document.activeElement as HTMLElement | null)?.closest<HTMLElement>(".react-flow__node")?.dataset.id;
      const selected = getNodes().filter((n) => n.selected);
      const target = focused ?? (selected.length === 1 ? selected[0].id : null);
      const name = await storage.saveAsset(file);
      if (target) {
        updateCard(target, { image: name });
      } else {
        const rect = document.querySelector(".canvas")!.getBoundingClientRect();
        createAt(rect.left + rect.width / 2, rect.top + rect.height / 2, name);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [createAt, getNodes, storage, updateCard]);

  // Tasten 1–6 setzen den Typ, Strg/Cmd+D dupliziert – für die eine ausgewählte Karte (oder die mit offenem Menü).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.closest("input, textarea, select, [contenteditable]")) return;
      const selected = getNodes().filter((n) => n.selected);
      const target = useMenu.getState().menu?.cardId ?? (selected.length === 1 ? selected[0].id : null);
      if (!target) return;
      if ((e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        duplicate(target);
        closeMenu();
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const type = CARD_TYPES[Number(e.key) - 1]?.type;
      if (!type) return;
      e.preventDefault();
      updateCard(target, { type });
      closeMenu();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeMenu, duplicate, getNodes, updateCard]);

  const isPane = (target: EventTarget) => (target as HTMLElement).classList?.contains("react-flow__pane");

  return (
    <div
      className="canvas"
      onDoubleClick={(e) => isPane(e.target) && createAt(e.clientX, e.clientY)}
      onDragOver={(e) => e.dataTransfer.types.includes("Files") && e.preventDefault()}
      onDrop={async (e) => {
        const file = firstImageFile(e.dataTransfer);
        if (!file) return;
        e.preventDefault();
        const { clientX, clientY } = e;
        createAt(clientX, clientY, await storage.saveAsset(file));
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={(_, __, dragged) => moveCards(dragged.map((n) => ({ id: n.id, ...n.position })))}
        onConnect={(c) => connect(c.source, c.target)}
        onDelete={onDelete}
        onNodeContextMenu={(e, node) => {
          e.preventDefault();
          openMenu({ kind: "context", cardId: node.id, x: e.clientX, y: e.clientY });
        }}
        onMoveStart={closeMenu}
        deleteKeyCode={DELETE_KEYS}
        zoomOnDoubleClick={false}
        connectionRadius={40}
        minZoom={0.2}
        maxZoom={2.5}
        colorMode={mode}
        proOptions={{ hideAttribution: true }}
        fitView={fitOnStart}
        fitViewOptions={{ maxZoom: 1, padding: 0.2 }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.3} />
      </ReactFlow>
      {cards.length === 0 && (
        <p className="empty-hint">
          Doppelklick auf die Leinwand für eine neue Karte
          <br />
          oder ein Bild hierher ziehen
        </p>
      )}
    </div>
  );
}
