import { useRef, useEffect } from 'react'
import { useBlocksStore } from '../../store/blocks.store'
import type { Block } from '../../types/block'

interface Props {
  block: Block
  workspaceId: string
}

export default function PageTitle({ block, workspaceId }: Props) {
  const { updateBlock } = useBlocksStore()
  const ref = useRef<HTMLDivElement>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const title = (block.content as { title?: string }).title ?? ''

  useEffect(() => {
    if (ref.current && ref.current.textContent !== title) {
      ref.current.textContent = title
    }
  }, [block.id])

  const handleInput = () => {
    const newTitle = ref.current?.textContent ?? ''
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      updateBlock(workspaceId, block.id, { ...block.content, title: newTitle })
    }, 400)
  }

  return (
    <div
      ref={ref}
      contentEditable
      suppressContentEditableWarning
      onInput={handleInput}
      style={{
        fontSize: 40,
        fontWeight: 700,
        outline: 'none',
        marginBottom: 24,
        lineHeight: 1.2,
        color: '#37352f',
        minHeight: 52,
        wordBreak: 'break-word',
      }}
      data-placeholder="Untitled"
      onFocus={(e) => {
        if (!e.currentTarget.textContent) {
          e.currentTarget.style.cssText += '; color: #aaa'
        }
      }}
      onBlur={(e) => {
        e.currentTarget.style.color = '#37352f'
      }}
    />
  )
}
