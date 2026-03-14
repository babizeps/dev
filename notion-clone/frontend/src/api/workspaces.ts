import { api } from './client'
import type { Workspace } from '../types/workspace'

export const workspacesApi = {
  list: () => api.get<Workspace[]>('/workspaces'),
  create: (name: string) => api.post<Workspace>('/workspaces', { name }),
}
