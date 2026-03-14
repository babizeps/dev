import fp from 'fastify-plugin'
import cookie from '@fastify/cookie'
import { env } from '../config.js'

export default fp(async (app) => {
  app.register(cookie, {
    secret: env.COOKIE_SECRET,
  })
})
