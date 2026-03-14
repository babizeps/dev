import { create } from 'zustand'
import { invoke } from '@tauri-apps/api/core'
import type { Book, ReadingProgress, ReaderSettings } from '../types/book'
import { DEFAULT_SETTINGS } from '../types/book'

interface ReaderState {
  currentBook: Book | null
  progress: ReadingProgress | null
  settings: ReaderSettings
  isTocOpen: boolean
  isToolbarVisible: boolean
  setCurrentBook: (book: Book) => void
  loadProgress: (bookId: string) => Promise<void>
  saveProgress: (position: string, percentage: number) => Promise<void>
  updateSettings: (patch: Partial<ReaderSettings>) => Promise<void>
  loadSettings: () => Promise<void>
  setTocOpen: (open: boolean) => void
  setToolbarVisible: (visible: boolean) => void
}

export const useReaderStore = create<ReaderState>((set, get) => ({
  currentBook: null,
  progress: null,
  settings: DEFAULT_SETTINGS,
  isTocOpen: false,
  isToolbarVisible: true,

  setCurrentBook: (book) => set({ currentBook: book, progress: null }),

  loadProgress: async (bookId) => {
    try {
      const progress = await invoke<ReadingProgress | null>('get_progress', { bookId })
      set({ progress })
    } catch (_) {}
  },

  saveProgress: async (position, percentage) => {
    const book = get().currentBook
    if (!book) return
    try {
      await invoke('save_progress', { bookId: book.id, position, percentage })
      set(() => ({
        progress: {
          bookId: book.id,
          position,
          percentage,
          updatedAt: new Date().toISOString(),
        },
      }))
    } catch (_) {}
  },

  loadSettings: async () => {
    try {
      const settings = await invoke<ReaderSettings>('get_settings')
      set({ settings })
    } catch (_) {}
  },

  updateSettings: async (patch) => {
    const next = { ...get().settings, ...patch }
    set({ settings: next })
    try {
      await invoke('save_settings', { settings: next })
    } catch (_) {}
  },

  setTocOpen: (isTocOpen) => set({ isTocOpen }),
  setToolbarVisible: (isToolbarVisible) => set({ isToolbarVisible }),
}))
