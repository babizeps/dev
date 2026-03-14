export type BookFormat = 'pdf' | 'epub' | 'txt'

export interface Book {
  id: string
  title: string
  author: string
  filePath: string
  format: BookFormat
  coverPath: string | null
  totalPages: number | null
  fileSize: number
  addedAt: string
  lastOpenedAt: string | null
}

export interface ReadingProgress {
  bookId: string
  position: string
  percentage: number
  updatedAt: string
}

export type Theme = 'light' | 'dark' | 'sepia'
export type FontFamily = 'serif' | 'sans-serif' | 'monospace'

export interface ReaderSettings {
  theme: Theme
  fontSize: number
  lineHeight: number
  fontFamily: FontFamily
}

export const DEFAULT_SETTINGS: ReaderSettings = {
  theme: 'light',
  fontSize: 18,
  lineHeight: 1.6,
  fontFamily: 'serif',
}
