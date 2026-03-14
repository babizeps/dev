import { api } from './client'
import type { User } from '../types/user'

export const authApi = {
  register: (email: string, password: string) =>
    api.post<{ user: User }>('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    api.post<{ user: User }>('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get<{ user: User }>('/auth/me'),
}
