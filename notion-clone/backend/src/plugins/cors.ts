import fp from 'fastify-plugin'
import cors from '@fastify/cors'
import { env } from '../config.js'

export default fp(async (app) => {
  app.register(cors, {
    origin: env.NODE_ENV === 'development' ? 'http://localhost:5173' : false,
    credentials: true,
  })
})
