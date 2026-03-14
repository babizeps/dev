import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import { prisma } from '../db.js'
import { verifySession } from '../auth/middleware.js'

const createWorkspaceSchema = z.object({ name: z.string().min(1) })

export default async function workspaceRoutes(app: FastifyInstance) {
  app.addHook('preHandler', verifySession)

  app.get('/', async (req) => {
    const workspaces = await prisma.workspace.findMany({
      where: { ownerId: req.user.id },
      orderBy: { createdAt: 'asc' },
    })
    return workspaces
  })

  app.post('/', async (req, reply) => {
    const result = createWorkspaceSchema.safeParse(req.body)
    if (!result.success) return reply.status(400).send({ error: result.error.flatten() })

    const workspace = await prisma.workspace.create({
      data: { name: result.data.name, ownerId: req.user.id },
    })
    return reply.status(201).send(workspace)
  })
}
