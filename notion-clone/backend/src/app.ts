import Fastify from 'fastify'
import corsPlugin from './plugins/cors.js'
import cookiePlugin from './plugins/cookie.js'
import sensiblePlugin from './plugins/sensible.js'
import authRoutes from './auth/routes.js'
import blockRoutes from './blocks/routes.js'
import workspaceRoutes from './workspaces/routes.js'

export function buildApp() {
  const app = Fastify({ logger: true })

  app.register(corsPlugin)
  app.register(cookiePlugin)
  app.register(sensiblePlugin)

  app.get('/healthz', async () => ({ status: 'ok' }))

  app.register(authRoutes, { prefix: '/auth' })
  app.register(workspaceRoutes, { prefix: '/workspaces' })
  app.register(blockRoutes, { prefix: '/workspaces' })

  return app
}
