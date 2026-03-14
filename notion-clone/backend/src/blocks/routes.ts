import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import { prisma } from '../db.js'
import { verifySession } from '../auth/middleware.js'
import { createBlockSchema, updateBlockSchema, reorderBlockSchema } from './schema.js'
import { getNewOrder } from './service.js'

async function assertWorkspaceOwner(workspaceId: string, userId: string) {
  const ws = await prisma.workspace.findUnique({ where: { id: workspaceId } })
  if (!ws || ws.ownerId !== userId) throw { statusCode: 403, message: 'Forbidden' }
  return ws
}

export default async function blockRoutes(app: FastifyInstance) {
  app.addHook('preHandler', verifySession)

  // GET /workspaces/:wid/blocks?parentId=
  app.get('/:wid/blocks', async (req, reply) => {
    const { wid } = req.params as { wid: string }
    const { parentId } = req.query as { parentId?: string }

    await assertWorkspaceOwner(wid, req.user.id)

    const blocks = await prisma.block.findMany({
      where: {
        workspaceId: wid,
        parentId: parentId === 'null' || parentId === undefined ? null : parentId,
      },
      orderBy: { order: 'asc' },
    })
    return blocks
  })

  // POST /workspaces/:wid/blocks
  app.post('/:wid/blocks', async (req, reply) => {
    const { wid } = req.params as { wid: string }
    await assertWorkspaceOwner(wid, req.user.id)

    const result = createBlockSchema.safeParse(req.body)
    if (!result.success) return reply.status(400).send({ error: result.error.flatten() })

    const { type, parentId, content, afterId } = result.data
    const order = await getNewOrder(wid, parentId, afterId)

    const block = await prisma.block.create({
      data: { type, workspaceId: wid, parentId: parentId ?? null, content, order },
    })
    return reply.status(201).send(block)
  })

  // PATCH /workspaces/:wid/blocks/:id
  app.patch('/:wid/blocks/:id', async (req, reply) => {
    const { wid, id } = req.params as { wid: string; id: string }
    await assertWorkspaceOwner(wid, req.user.id)

    const result = updateBlockSchema.safeParse(req.body)
    if (!result.success) return reply.status(400).send({ error: result.error.flatten() })

    const block = await prisma.block.update({
      where: { id, workspaceId: wid },
      data: result.data,
    })
    return block
  })

  // DELETE /workspaces/:wid/blocks/:id
  app.delete('/:wid/blocks/:id', async (req, reply) => {
    const { wid, id } = req.params as { wid: string; id: string }
    await assertWorkspaceOwner(wid, req.user.id)

    await prisma.block.delete({ where: { id, workspaceId: wid } })
    return reply.status(204).send()
  })

  // POST /workspaces/:wid/blocks/reorder
  app.post('/:wid/blocks/reorder', async (req, reply) => {
    const { wid } = req.params as { wid: string }
    await assertWorkspaceOwner(wid, req.user.id)

    const result = reorderBlockSchema.safeParse(req.body)
    if (!result.success) return reply.status(400).send({ error: result.error.flatten() })

    const { blockId, afterId } = result.data
    const block = await prisma.block.findUniqueOrThrow({ where: { id: blockId } })
    const order = await getNewOrder(wid, block.parentId, afterId)

    const updated = await prisma.block.update({ where: { id: blockId }, data: { order } })
    return updated
  })
}
