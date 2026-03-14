import { create } from 'zustand'
import type { Block, BlockType } from '../types/block'
import { blocksApi } from '../api/blocks'

interface BlocksState {
  // parentId (or "root") → Block[]
  blocksByParent: Map<string, Block[]>
  fetchBlocks: (workspaceId: string, parentId: string | null) => Promise<void>
  addBlock: (workspaceId: string, type: BlockType, parentId: string | null, afterId?: string) => Promise<Block>
  updateBlock: (workspaceId: string, blockId: string, content: Record<string, unknown>) => Promise<void>
  deleteBlock: (workspaceId: string, blockId: string, parentId: string | null) => Promise<void>
}

const parentKey = (id: string | null) => id ?? 'root'

export const useBlocksStore = create<BlocksState>((set, get) => ({
  blocksByParent: new Map(),

  fetchBlocks: async (workspaceId, parentId) => {
    const blocks = await blocksApi.list(workspaceId, parentId)
    set((s) => {
      const next = new Map(s.blocksByParent)
      next.set(parentKey(parentId), blocks)
      return { blocksByParent: next }
    })
  },

  addBlock: async (workspaceId, type, parentId, afterId) => {
    const block = await blocksApi.create(workspaceId, { type, parentId, afterId })
    set((s) => {
      const key = parentKey(parentId)
      const existing = s.blocksByParent.get(key) ?? []
      const next = new Map(s.blocksByParent)
      next.set(key, [...existing, block])
      return { blocksByParent: next }
    })
    return block
  },

  updateBlock: async (workspaceId, blockId, content) => {
    const updated = await blocksApi.update(workspaceId, blockId, { content })
    set((s) => {
      const next = new Map(s.blocksByParent)
      for (const [key, blocks] of next) {
        const idx = blocks.findIndex((b) => b.id === blockId)
        if (idx !== -1) {
          const updated2 = [...blocks]
          updated2[idx] = updated
          next.set(key, updated2)
        }
      }
      return { blocksByParent: next }
    })
  },

  deleteBlock: async (workspaceId, blockId, parentId) => {
    await blocksApi.delete(workspaceId, blockId)
    set((s) => {
      const key = parentKey(parentId)
      const next = new Map(s.blocksByParent)
      next.set(key, (next.get(key) ?? []).filter((b) => b.id !== blockId))
      return { blocksByParent: next }
    })
  },
}))
