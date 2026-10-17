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
import { useWorld } from "../core/store";
import type { Card, Edge } from "../core/types";
import { liveCards, liveEdges } from "../core/world";
import { firstImageFile, useStorage } from "./assets";
import { CardNode, type CardNodeType } from "./CardNode";
import { FloatingEdge } from "./FloatingEdge";
import type { ThemeMode } from "./theme";

const nodeTypes = { card: CardNode };
const edgeTypes = { floating: FloatingEdge };
const CARD_WIDTH = 260;

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
  const { addCard, updateCard, connect, removeCards, removeEdges } = useWorld.getState();
  const storage = useStorage();
  const { screenToFlowPosition } = useReactFlow();

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
    ({ nodes: deletedNodes, edges: deletedEdges }) => {
      removeCards(deletedNodes.map((n) => n.id));
      removeEdges(deletedEdges.map((e) => e.id));
    },
    [removeCards, removeEdges],
  );

  const createAt = (clientX: number, clientY: number, image: string | null = null) => {
    const p = screenToFlowPosition({ x: clientX, y: clientY });
    addCard({ type: "notiz", x: p.x - CARD_WIDTH / 2, y: p.y - 40, image });
  };

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
        onNodeDragStop={(_, __, dragged) => dragged.forEach((n) => updateCard(n.id, n.position))}
        onConnect={(c) => connect(c.source, c.target)}
        onDelete={onDelete}
        deleteKeyCode={["Delete", "Backspace"]}
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
