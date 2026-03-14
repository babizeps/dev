import { prisma } from '../db.js'

const REBALANCE_THRESHOLD = 0.0001

export async function getNewOrder(
  workspaceId: string,
  parentId: string | null | undefined,
  afterId?: string
): Promise<number> {
  const siblings = await prisma.block.findMany({
    where: { workspaceId, parentId: parentId ?? null },
    orderBy: { order: 'asc' },
    select: { id: true, order: true },
  })

  if (siblings.length === 0) return 1000

  if (!afterId) {
    // Insert at start
    return siblings[0].order / 2
  }

  const afterIdx = siblings.findIndex((b) => b.id === afterId)
  if (afterIdx === -1 || afterIdx === siblings.length - 1) {
    // Insert at end
    return siblings[siblings.length - 1].order + 1000
  }

  const before = siblings[afterIdx]
  const after = siblings[afterIdx + 1]
  const newOrder = (before.order + after.order) / 2

  if (Math.abs(after.order - before.order) < REBALANCE_THRESHOLD) {
    await rebalanceSiblings(workspaceId, parentId ?? null)
    return getNewOrder(workspaceId, parentId, afterId)
  }

  return newOrder
}

async function rebalanceSiblings(workspaceId: string, parentId: string | null) {
  const siblings = await prisma.block.findMany({
    where: { workspaceId, parentId },
    orderBy: { order: 'asc' },
    select: { id: true },
  })

  await Promise.all(
    siblings.map((b, i) =>
      prisma.block.update({ where: { id: b.id }, data: { order: (i + 1) * 1000 } })
    )
  )
}
