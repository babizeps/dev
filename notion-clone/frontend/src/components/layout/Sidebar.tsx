import { useEffect, useState } from 'react'
import { useAuthStore } from '../../store/auth.store'
import { useUiStore } from '../../store/ui.store'
import { useBlocksStore } from '../../store/blocks.store'
import { workspacesApi } from '../../api/workspaces'
import { authApi } from '../../api/auth'
import type { Workspace } from '../../types/workspace'
import SidebarItem from './SidebarItem'

export default function Sidebar() {
  const { user, setUser } = useAuthStore()
  const { activeWorkspaceId, setActiveWorkspace } = useUiStore()
  const { blocksByParent, fetchBlocks, addBlock } = useBlocksStore()
  const [workspace, setWorkspace] = useState<Workspace | null>(null)

  useEffect(() => {
    workspacesApi.list().then((ws) => {
      if (ws[0]) {
        setWorkspace(ws[0])
        setActiveWorkspace(ws[0].id)
        fetchBlocks(ws[0].id, null)
      }
    })
  }, [])

  const rootPages = (blocksByParent.get('root') ?? []).filter((b) => b.type === 'page')

  const handleNewPage = async () => {
    if (!activeWorkspaceId) return
    await addBlock(activeWorkspaceId, 'page', null)
    // Re-fetch to get correct order
    fetchBlocks(activeWorkspaceId, null)
  }

  const handleLogout = async () => {
    await authApi.logout()
    setUser(null)
  }

  return (
    <aside style={{ width: 240, minHeight: '100vh', background: '#f7f7f5', borderRight: '1px solid #e9e9e7', display: 'flex', flexDirection: 'column', padding: '8px 4px' }}>
      <div style={{ padding: '8px 12px', marginBottom: 4 }}>
        <div style={{ fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {workspace?.name ?? 'Workspace'}
        </div>
        <div style={{ fontSize: 12, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.email}</div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {rootPages.map((page) => (
          <SidebarItem key={page.id} block={page} workspaceId={activeWorkspaceId ?? ''} />
        ))}
      </div>

      <button
        onClick={handleNewPage}
        style={{ margin: '4px 8px', padding: '6px 12px', background: 'none', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13, color: '#999', textAlign: 'left' }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#ebebea' }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'none' }}
      >
        + New page
      </button>

      <button
        onClick={handleLogout}
        style={{ margin: '4px 8px 8px', padding: '6px 12px', background: 'none', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, color: '#999', textAlign: 'left' }}
      >
        Log out
      </button>
    </aside>
  )
}
