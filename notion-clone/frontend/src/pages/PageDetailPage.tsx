import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useBlocksStore } from '../store/blocks.store'
import { useUiStore } from '../store/ui.store'
import type { Block } from '../types/block'
import PageView from '../components/page/PageView'

export default function PageDetailPage() {
  const { pageId } = useParams<{ pageId: string }>()
  const { blocksByParent } = useBlocksStore()
  const { activeWorkspaceId } = useUiStore()
  const [page, setPage] = useState<Block | null>(null)

  useEffect(() => {
    if (!pageId) return
    // Search all loaded blocks for this page
    for (const blocks of blocksByParent.values()) {
      const found = blocks.find((b) => b.id === pageId)
      if (found) { setPage(found); return }
    }
  }, [pageId, blocksByParent])

  if (!page || !activeWorkspaceId) {
    return <div style={{ padding: 32, color: '#999' }}>Loading page…</div>
  }

  return <PageView block={page} workspaceId={activeWorkspaceId} />
}
