import { z } from 'zod'

export const BLOCK_TYPES = [
  'page', 'paragraph', 'heading1', 'heading2', 'heading3',
  'bulleted_list', 'numbered_list', 'todo', 'code', 'divider', 'image',
] as const

export const createBlockSchema = z.object({
  type: z.enum(BLOCK_TYPES),
  parentId: z.string().uuid().nullable().optional(),
  content: z.record(z.unknown()).default({}),
  afterId: z.string().uuid().optional(), // insert after this block
})

export const updateBlockSchema = z.object({
  type: z.enum(BLOCK_TYPES).optional(),
  parentId: z.string().uuid().nullable().optional(),
  content: z.record(z.unknown()).optional(),
})

export const reorderBlockSchema = z.object({
  blockId: z.string().uuid(),
  beforeId: z.string().uuid().optional(),
  afterId: z.string().uuid().optional(),
})
