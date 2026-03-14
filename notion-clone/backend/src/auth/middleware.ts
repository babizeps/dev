import type { FastifyRequest, FastifyReply } from 'fastify'
import { lucia } from './lucia.js'

export async function verifySession(req: FastifyRequest, reply: FastifyReply) {
  const sessionId = req.cookies[lucia.sessionCookieName]

  if (!sessionId) {
    return reply.status(401).send({ error: 'Unauthorized' })
  }

  const { session, user } = await lucia.validateSession(sessionId)

  if (!session) {
    const blank = lucia.createBlankSessionCookie()
    reply.setCookie(blank.name, blank.value, blank.attributes)
    return reply.status(401).send({ error: 'Unauthorized' })
  }

  if (session.fresh) {
    const fresh = lucia.createSessionCookie(session.id)
    reply.setCookie(fresh.name, fresh.value, fresh.attributes)
  }

  req.user = user
  req.session = session
}

declare module 'fastify' {
  interface FastifyRequest {
    user: import('lucia').User
    session: import('lucia').Session
  }
}
