import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { invoke } from '@tauri-apps/api/core'
import * as pdfjs from 'pdfjs-dist'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import { useReaderStore } from '../store/reader.store'
import { useLibraryStore } from '../store/library.store'
import ReaderToolbar from '../components/reader/ReaderToolbar'
import './ReaderPage.css'

// Point PDF.js worker to the bundled file
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString()

export default function PdfReaderPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const navigate = useNavigate()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const renderTaskRef = useRef<pdfjs.RenderTask | null>(null)

  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)

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

  // Load PDF from file bytes
  useEffect(() => {
    const book = currentBook ?? books.find((b) => b.id === bookId)
    if (!book) return

    loadProgress(book.id)

    invoke<number[]>('read_file_bytes', { path: book.filePath })
      .then((bytes) => {
        const data = new Uint8Array(bytes)
        return pdfjs.getDocument({ data }).promise
      })
      .then((doc) => {
        setPdfDoc(doc)
        setTotalPages(doc.numPages)
      })
      .catch(() => navigate('/'))
  }, [currentBook?.id])

  // Restore page from progress once PDF is loaded
  useEffect(() => {
    if (pdfDoc && progress) {
      const page = parseInt(progress.position, 10)
      if (!isNaN(page) && page >= 1 && page <= pdfDoc.numPages) {
        setCurrentPage(page)
      }
    }
  }, [pdfDoc, progress])

  // Render current page
  const renderPage = useCallback(
    async (pageNum: number) => {
      if (!pdfDoc || !canvasRef.current) return

      if (renderTaskRef.current) {
        renderTaskRef.current.cancel()
      }

      const page = await pdfDoc.getPage(pageNum)
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')!
      const container = canvas.parentElement!
      const containerWidth = container.clientWidth - 80

      const viewport = page.getViewport({ scale: 1 })
      const scale = Math.min(containerWidth / viewport.width, 1.5)
      const scaled = page.getViewport({ scale })

      canvas.width = scaled.width
      canvas.height = scaled.height

      // Apply sepia tint for sepia theme
      if (settings.theme === 'sepia') {
        ctx.fillStyle = '#f4ecd8'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
      }

      const task = page.render({ canvasContext: ctx, viewport: scaled })
      renderTaskRef.current = task
      await task.promise
    },
    [pdfDoc, settings.theme]
  )

  useEffect(() => {
    if (pdfDoc) renderPage(currentPage)
  }, [currentPage, pdfDoc, renderPage])

  // Save progress with debounce
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!pdfDoc || !currentBook) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      const percentage = totalPages > 0 ? (currentPage / totalPages) * 100 : 0
      saveProgress(String(currentPage), percentage)
    }, 500)
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current) }
  }, [currentPage, pdfDoc])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {
        e.preventDefault()
        setCurrentPage((p) => Math.min(p + 1, totalPages))
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault()
        setCurrentPage((p) => Math.max(p - 1, 1))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [totalPages])

  const percentage = totalPages > 0 ? (currentPage / totalPages) * 100 : 0

  return (
    <div className="reader-page" data-theme={settings.theme}>
      <ReaderToolbar currentPage={currentPage} totalPages={totalPages} percentage={percentage} />

      <div className="reader-content pdf-content" onClick={(e) => {
        const x = e.clientX / window.innerWidth
        if (x < 0.35) setCurrentPage((p) => Math.max(p - 1, 1))
        else if (x > 0.65) setCurrentPage((p) => Math.min(p + 1, totalPages))
      }}>
        <canvas ref={canvasRef} className="pdf-canvas" />
      </div>

      <div className="page-nav-hint">
        <span>← Previous</span>
        <span>Click sides or use ← → keys</span>
        <span>Next →</span>
      </div>
    </div>
  )
}
