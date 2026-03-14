import { create } from 'zustand'
import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'
import type { Book } from '../types/book'

interface LibraryState {
  books: Book[]
  isLoading: boolean
  error: string | null
  fetchBooks: () => Promise<void>
  importBook: () => Promise<void>
  importBookByPath: (path: string) => Promise<void>
  removeBook: (bookId: string) => Promise<void>
  markOpened: (bookId: string) => void
}

export const useLibraryStore = create<LibraryState>((set, get) => ({
  books: [],
  isLoading: false,
  error: null,

  fetchBooks: async () => {
    set({ isLoading: true, error: null })
    try {
      const books = await invoke<Book[]>('list_books')
      set({ books, isLoading: false })
    } catch (e) {
      set({ error: String(e), isLoading: false })
    }
  },

  importBook: async () => {
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Books', extensions: ['pdf', 'epub', 'txt'] }],
    })
    if (!selected) return
    await get().importBookByPath(selected as string)
  },

  importBookByPath: async (path: string) => {
    set({ error: null })
    try {
      const book = await invoke<Book>('add_book', { filePath: path })
      set((s) => ({ books: [book, ...s.books] }))
    } catch (e) {
      set({ error: String(e) })
    }
  },

  removeBook: async (bookId: string) => {
    await invoke('remove_book', { bookId })
    set((s) => ({ books: s.books.filter((b) => b.id !== bookId) }))
  },

  markOpened: (bookId: string) => {
    invoke('update_last_opened', { bookId }).catch(() => {})
    set((s) => ({
      books: s.books.map((b) =>
        b.id === bookId ? { ...b, lastOpenedAt: new Date().toISOString() } : b
      ),
    }))
  },
}))
