import { create } from 'zustand'

interface UiState {
  sidebarOpen: boolean
  expandedPageIds: Set<string>
  activeWorkspaceId: string | null
  setSidebarOpen: (open: boolean) => void
  toggleExpanded: (id: string) => void
  setActiveWorkspace: (id: string) => void
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  expandedPageIds: new Set(),
  activeWorkspaceId: null,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  toggleExpanded: (id) =>
    set((s) => {
      const next = new Set(s.expandedPageIds)
      next.has(id) ? next.delete(id) : next.add(id)
      return { expandedPageIds: next }
    }),
  setActiveWorkspace: (id) => set({ activeWorkspaceId: id }),
}))
