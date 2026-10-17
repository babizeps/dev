import { BaseEdge, getBezierPath, Position, useInternalNode, type EdgeProps, type InternalNode } from "@xyflow/react";

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

export function FloatingEdge({ id, source, target, style, interactionWidth }: EdgeProps) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  if (!sourceNode?.measured.width || !targetNode?.measured.width) return null;

  const s = borderPoint(sourceNode, targetNode);
  const t = borderPoint(targetNode, sourceNode);
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
