export const BLOCK_TYPES = [
  'page', 'paragraph', 'heading1', 'heading2', 'heading3',
  'bulleted_list', 'numbered_list', 'todo', 'code', 'divider', 'image',
] as const

export type BlockType = typeof BLOCK_TYPES[number]

export interface Block {
  id: string
  type: BlockType
  workspaceId: string
  parentId: string | null
  content: Record<string, unknown>
  order: number
  createdAt: string
  updatedAt: string
}
