import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { Block } from '../../types/block'
import { useBlocksStore } from '../../store/blocks.store'
import { useUiStore } from '../../store/ui.store'

interface Props {
  block: Block
  workspaceId: string
}

export default function SidebarItem({ block, workspaceId }: Props) {
  const navigate = useNavigate()
  const { pageId } = useParams()
  const { expandedPageIds, toggleExpanded } = useUiStore()
  const { blocksByParent, fetchBlocks } = useBlocksStore()

  const isExpanded = expandedPageIds.has(block.id)
  const isActive = pageId === block.id
  const children = blocksByParent.get(block.id) ?? []
  const title = (block.content as { title?: string }).title || 'Untitled'

  const [loaded, setLoaded] = useState(false)

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!loaded) {
      await fetchBlocks(workspaceId, block.id)
      setLoaded(true)
    }
    toggleExpanded(block.id)
  }

  return (
    <div>
      <div
        onClick={() => navigate(`/${block.id}`)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '3px 8px',
          borderRadius: 4,
          cursor: 'pointer',
          background: isActive ? '#e9e9e7' : 'transparent',
          userSelect: 'none',
        }}
        onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#f1f1ef' }}
        onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent' }}
      >
        <button
          onClick={handleToggle}
          style={{ width: 20, height: 20, border: 'none', background: 'none', cursor: 'pointer', padding: 0, color: '#999', fontSize: 10, flexShrink: 0 }}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
        <span style={{ fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          📄 {title}
        </span>
      </div>

      {isExpanded && children.filter((c) => c.type === 'page').length > 0 && (
        <div style={{ paddingLeft: 16 }}>
          {children.filter((c) => c.type === 'page').map((child) => (
            <SidebarItem key={child.id} block={child} workspaceId={workspaceId} />
          ))}
        </div>
      )}
    </div>
  )
}
