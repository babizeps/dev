import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ePub from 'epubjs'
import type { Book as EpubBook, Rendition } from 'epubjs'
import { invoke } from '@tauri-apps/api/core'
import { useReaderStore } from '../store/reader.store'
import { useLibraryStore } from '../store/library.store'
import ReaderToolbar from '../components/reader/ReaderToolbar'
import './ReaderPage.css'

const THEME_STYLES = {
  light: { body: { background: '#ffffff', color: '#1a1a1a' } },
  dark:  { body: { background: '#1c1c1e', color: '#e5e5e7' } },
  sepia: { body: { background: '#f4ecd8', color: '#3b2a1a' } },
}

export default function EpubReaderPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const epubRef = useRef<EpubBook | null>(null)
  const renditionRef = useRef<Rendition | null>(null)

  const [percentage, setPercentage] = useState(0)

  const { currentBook, progress, settings, loadProgress, saveProgress, setCurrentBook } = useReaderStore()
  const { books } = useLibraryStore()

  // Restore book from store if navigated directly
  useEffect(() => {
    if (!currentBook && bookId) {
      const book = books.find((b) => b.id === bookId)
      if (book) setCurrentBook(book)
      else navigate('/')
    }
  }, [bookId, currentBook, books])

  // Load EPUB
  useEffect(() => {
    const book = currentBook ?? books.find((b) => b.id === bookId)
    if (!book || !containerRef.current) return

    loadProgress(book.id)

    invoke<number[]>('read_file_bytes', { path: book.filePath })
      .then((bytes) => {
        const arrayBuffer = new Uint8Array(bytes).buffer

        // Clean up previous instance
        if (epubRef.current) epubRef.current.destroy()

        const epubBook = ePub(arrayBuffer)
        epubRef.current = epubBook

        const rendition = epubBook.renderTo(containerRef.current!, {
          width: '100%',
          height: '100%',
          flow: 'paginated',
          spread: 'none',
        })
        renditionRef.current = rendition

        // Register themes
        Object.entries(THEME_STYLES).forEach(([name, style]) => {
          rendition.themes.register(name, { ...style })
        })
        rendition.themes.select(settings.theme)
        rendition.themes.fontSize(`${settings.fontSize}px`)

        rendition.on('relocated', (location: any) => {
          const pct = (location.start.percentage ?? 0) * 100
          setPercentage(pct)
          saveProgress(location.start.cfi, pct)
        })

        epubBook.ready.then(() => {
          if (progress?.position) {
            rendition.display(progress.position)
          } else {
            rendition.display()
          }
        })
      })
      .catch(() => navigate('/'))

    return () => {
      if (epubRef.current) epubRef.current.destroy()
    }
  }, [currentBook?.id])

  // Apply theme and font changes to running rendition
  useEffect(() => {
    if (!renditionRef.current) return
    renditionRef.current.themes.select(settings.theme)
    renditionRef.current.themes.fontSize(`${settings.fontSize}px`)
  }, [settings.theme, settings.fontSize])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!renditionRef.current) return
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {
        e.preventDefault()
        renditionRef.current.next()
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault()
        renditionRef.current.prev()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="reader-page" data-theme={settings.theme}>
      <ReaderToolbar percentage={percentage} />

      <div className="reader-content epub-content">
        <div ref={containerRef} className="epub-container" />
      </div>

      <div className="epub-nav-btns">
        <button className="epub-nav-btn" onClick={() => renditionRef.current?.prev()}>‹</button>
        <button className="epub-nav-btn" onClick={() => renditionRef.current?.next()}>›</button>
      </div>
    </div>
  )
}
