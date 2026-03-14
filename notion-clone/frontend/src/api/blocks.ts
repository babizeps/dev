import { api } from './client'
import type { Block, BlockType } from '../types/block'

export const blocksApi = {
  list: (workspaceId: string, parentId: string | null) =>
    api.get<Block[]>(
      `/workspaces/${workspaceId}/blocks?parentId=${parentId ?? 'null'}`
    ),
  create: (
    workspaceId: string,
    data: { type: BlockType; parentId?: string | null; content?: Record<string, unknown>; afterId?: string }
  ) => api.post<Block>(`/workspaces/${workspaceId}/blocks`, data),
  update: (workspaceId: string, blockId: string, data: Partial<Pick<Block, 'type' | 'content' | 'parentId'>>) =>
    api.patch<Block>(`/workspaces/${workspaceId}/blocks/${blockId}`, data),
  delete: (workspaceId: string, blockId: string) =>
    api.delete(`/workspaces/${workspaceId}/blocks/${blockId}`),
}
