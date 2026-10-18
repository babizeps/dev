import {
  BaseEdge,
  getBezierPath,
  Position,
  useInternalNode,
  type ConnectionLineComponentProps,
  type EdgeProps,
  type InternalNode,
} from "@xyflow/react";
import { useActiveStyle } from "./theme";

/*
 * Verbindungen ohne feste Andockpunkte: Die Linie startet und endet dort,
 * wo sie den Kartenrand schneidet. So muss eine Verbindung keine Seiten speichern.
 */

function center(node: InternalNode) {
  const { x, y } = node.internals.positionAbsolute;
  return { x: x + (node.measured.width ?? 0) / 2, y: y + (node.measured.height ?? 0) / 2 };
}

/** Schnittpunkt der Linie von der Mitte von `node` zur Mitte von `other` mit dem Rand von `node`. */
function borderPoint(node: InternalNode, other: InternalNode) {
  const w = (node.measured.width ?? 0) / 2;
  const h = (node.measured.height ?? 0) / 2;
  const c = center(node);
  const o = center(other);
  const dx = o.x - c.x;
  const dy = o.y - c.y;
  if (dx === 0 && dy === 0) return c;
  const scale = 1 / Math.max(Math.abs(dx) / w, Math.abs(dy) / h);
  return { x: c.x + dx * scale, y: c.y + dy * scale };
}

function side(node: InternalNode, p: { x: number; y: number }): Position {
  const { x, y } = node.internals.positionAbsolute;
  const w = node.measured.width ?? 0;
  const h = node.measured.height ?? 0;
  if (p.x <= x + 1) return Position.Left;
  if (p.x >= x + w - 1) return Position.Right;
  if (p.y <= y + 1) return Position.Top;
  if (p.y >= y + h - 1) return Position.Bottom;
  return Position.Top;
}

type Point = { x: number; y: number };

const DIRECTION: Record<Position, Point> = {
  [Position.Left]: { x: -1, y: 0 },
  [Position.Right]: { x: 1, y: 0 },
  [Position.Top]: { x: 0, y: -1 },
  [Position.Bottom]: { x: 0, y: 1 },
};

/** Kleiner, fester Zufallsgenerator: Jede Verbindung zittert immer gleich und springt beim Neuzeichnen nicht. */
function seeded(text: string) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

/**
 * Wie mit dem Stift gezogen: eine weiche Kurve, die leicht hin und her wandert.
 * Die Enden bleiben genau am Kartenrand, das Zittern nimmt zur Mitte hin zu.
 */
function sketchPath(id: string, s: Point, sp: Position, t: Point, tp: Position): string {
  const length = Math.hypot(t.x - s.x, t.y - s.y);
  const reach = Math.min(Math.max(length * 0.4, 24), 180);
  const c1 = { x: s.x + DIRECTION[sp].x * reach, y: s.y + DIRECTION[sp].y * reach };
  const c2 = { x: t.x + DIRECTION[tp].x * reach, y: t.y + DIRECTION[tp].y * reach };
  const at = (u: number): Point => {
    const v = 1 - u;
    return {
      x: v * v * v * s.x + 3 * v * v * u * c1.x + 3 * v * u * u * c2.x + u * u * u * t.x,
      y: v * v * v * s.y + 3 * v * v * u * c1.y + 3 * v * u * u * c2.y + u * u * u * t.y,
    };
  };
  const random = seeded(id);
  const waves = [
    { amp: 1.6 + random(), freq: Math.max(1, length / 140), phase: random() * Math.PI * 2 },
    { amp: 0.6 + random() * 0.6, freq: Math.max(2, length / 45), phase: random() * Math.PI * 2 },
  ];
  const steps = Math.max(8, Math.round(length / 8));
  const points: Point[] = [];
  for (let i = 0; i <= steps; i++) {
    const u = i / steps;
    const p = at(u);
    const q = at(Math.min(1, u + 0.001));
    const r = at(Math.max(0, u - 0.001));
    const dx = q.x - r.x;
    const dy = q.y - r.y;
    const norm = Math.hypot(dx, dy) || 1;
    const wobble = Math.sin(Math.PI * u) * waves.reduce((sum, w) => sum + w.amp * Math.sin(2 * Math.PI * w.freq * u + w.phase), 0);
    points.push({ x: p.x - (dy / norm) * wobble, y: p.y + (dx / norm) * wobble });
  }
  // Durch die Mittelpunkte glätten, damit keine Knicke entstehen.
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const mid = { x: (points[i].x + points[i + 1].x) / 2, y: (points[i].y + points[i + 1].y) / 2 };
    d += ` Q${points[i].x},${points[i].y} ${mid.x},${mid.y}`;
  }
  const last = points[points.length - 1];
  return `${d} L${last.x},${last.y}`;
}

export function FloatingEdge({ id, source, target, style, interactionWidth }: EdgeProps) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  const themeStyle = useActiveStyle();
  if (!sourceNode?.measured.width || !targetNode?.measured.width) return null;

  const s = borderPoint(sourceNode, targetNode);
  const t = borderPoint(targetNode, sourceNode);
  if (themeStyle === "sketch") {
    const path = sketchPath(id, s, side(sourceNode, s), t, side(targetNode, t));
    return <BaseEdge id={id} path={path} style={style} interactionWidth={interactionWidth} />;
  }
  const [path] = getBezierPath({
    sourceX: s.x,
    sourceY: s.y,
    sourcePosition: side(sourceNode, s),
    targetX: t.x,
    targetY: t.y,
    targetPosition: side(targetNode, t),
  });

  return <BaseEdge id={id} path={path} style={style} interactionWidth={interactionWidth} />;
}

/** Die Linie, während eine Verbindung gezogen wird – im Skizzenbuch ebenfalls von Hand gezogen. */
export function ConnectionLine({ fromX, fromY, toX, toY, fromPosition, toPosition, connectionLineStyle }: ConnectionLineComponentProps) {
  const themeStyle = useActiveStyle();
  const path =
    themeStyle === "sketch"
      ? sketchPath("verbinden", { x: fromX, y: fromY }, fromPosition, { x: toX, y: toY }, toPosition)
      : getBezierPath({ sourceX: fromX, sourceY: fromY, sourcePosition: fromPosition, targetX: toX, targetY: toY, targetPosition: toPosition })[0];
  return <path className="react-flow__connection-path" d={path} fill="none" style={connectionLineStyle} />;
}
