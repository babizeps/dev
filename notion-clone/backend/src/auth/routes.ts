import type { FastifyInstance } from 'fastify'
import { z } from 'zod'
import bcrypt from 'bcryptjs'
import { prisma } from '../db.js'
import { lucia } from './lucia.js'
import { verifySession } from './middleware.js'

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export default async function authRoutes(app: FastifyInstance) {
  app.post('/register', async (req, reply) => {
    const result = credentialsSchema.safeParse(req.body)
    if (!result.success) {
      return reply.status(400).send({ error: result.error.flatten() })
    }

    const { email, password } = result.data
    const existing = await prisma.user.findUnique({ where: { email } })
    if (existing) {
      return reply.status(409).send({ error: 'Email already in use' })
    }

    const passwordHash = await bcrypt.hash(password, 12)
    const user = await prisma.user.create({ data: { email, passwordHash } })

    // Auto-create a default workspace
    await prisma.workspace.create({
      data: { name: `${email.split('@')[0]}'s Workspace`, ownerId: user.id },
    })

    const session = await lucia.createSession(user.id, {})
    const cookie = lucia.createSessionCookie(session.id)
    reply.setCookie(cookie.name, cookie.value, cookie.attributes)

    return reply.status(201).send({ user: { id: user.id, email: user.email } })
  })

  app.post('/login', async (req, reply) => {
    const result = credentialsSchema.safeParse(req.body)
    if (!result.success) {
      return reply.status(400).send({ error: result.error.flatten() })
    }

    const { email, password } = result.data
    const user = await prisma.user.findUnique({ where: { email } })
    if (!user) {
      return reply.status(401).send({ error: 'Invalid credentials' })
    }

    const valid = await bcrypt.compare(password, user.passwordHash)
    if (!valid) {
      return reply.status(401).send({ error: 'Invalid credentials' })
    }

    const session = await lucia.createSession(user.id, {})
    const cookie = lucia.createSessionCookie(session.id)
    reply.setCookie(cookie.name, cookie.value, cookie.attributes)

    return reply.send({ user: { id: user.id, email: user.email } })
  })

  app.post('/logout', { preHandler: verifySession }, async (req, reply) => {
    await lucia.invalidateSession(req.session.id)
    const blank = lucia.createBlankSessionCookie()
    reply.setCookie(blank.name, blank.value, blank.attributes)
    return reply.status(204).send()
  })

  app.get('/me', { preHandler: verifySession }, async (req, reply) => {
    return reply.send({ user: req.user })
  })
}
