import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { invoke } from '@tauri-apps/api/core'
import { useReaderStore } from '../store/reader.store'
import { useLibraryStore } from '../store/library.store'
import ReaderToolbar from '../components/reader/ReaderToolbar'
import './ReaderPage.css'

function parseParagraphs(raw: string): string[] {
  return raw
    .split(/\n{2,}/)
    .map((block) => block.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
    .filter(Boolean)
}

function buildSpreads(paragraphs: string[], charBudget: number): string[][] {
  const spreads: string[][] = []
  let left: string[] = [], right: string[] = []
  let leftLen = 0, rightLen = 0
  const half = charBudget / 2
  for (const para of paragraphs) {
    if (leftLen < half)       { left.push(para);  leftLen  += para.length }
    else if (rightLen < half) { right.push(para); rightLen += para.length }
    else {
      spreads.push([left.join('\n\n'), right.join('\n\n')])
      left = [para]; right = []; leftLen = para.length; rightLen = 0
    }
  }
  if (left.length || right.length) spreads.push([left.join('\n\n'), right.join('\n\n')])
  return spreads
}

const CHARS_PER_SPREAD = 3000
const ARROW_HIDE_MS = 2500
const FLIP_DURATION_MS = 500

const FONT_FAMILY: Record<string, string> = {
  serif: 'Georgia, "Times New Roman", serif',
  'sans-serif': '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  monospace: '"SF Mono", Menlo, monospace',
}

function PageText({ text, style }: { text: string; style: React.CSSProperties }) {
  return (
    <div className="txt-column" style={style}>
      {text.split('\n\n').map((p, i) => (
        <p key={i} className="txt-paragraph">{p}</p>
      ))}
    </div>
  )
}

type AnimState = { fromIdx: number; toIdx: number; direction: 'forward' | 'backward' } | null

export default function TxtReaderPage() {
  const { bookId } = useParams<{ bookId: string }>()
  const navigate = useNavigate()

  const [spreads, setSpreads] = useState<string[][]>([])
  const [spreadIndex, setSpreadIndex] = useState(0)
  const [anim, setAnim] = useState<AnimState>(null)
  const [arrowsVisible, setArrowsVisible] = useState(false)
  const arrowTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const animTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { currentBook, progress, settings, loadProgress, saveProgress, setCurrentBook } = useReaderStore()
  const { books } = useLibraryStore()

  const [cursorHidden, setCursorHidden] = useState(false)
  const cursorTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Arrow auto-hide + cursor auto-hide (shared mousemove handler)
  const showArrows = useCallback(() => {
    setArrowsVisible(true)
    setCursorHidden(false)
    if (arrowTimer.current) clearTimeout(arrowTimer.current)
    arrowTimer.current = setTimeout(() => setArrowsVisible(false), ARROW_HIDE_MS)
    if (cursorTimer.current) clearTimeout(cursorTimer.current)
    cursorTimer.current = setTimeout(() => setCursorHidden(true), 2000)
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', showArrows)
    cursorTimer.current = setTimeout(() => setCursorHidden(true), 2000)
    return () => {
      window.removeEventListener('mousemove', showArrows)
      if (arrowTimer.current) clearTimeout(arrowTimer.current)
      if (cursorTimer.current) clearTimeout(cursorTimer.current)
    }
  }, [showArrows])

  useEffect(() => {
    if (!currentBook && bookId) {
      const book = books.find((b) => b.id === bookId)
      if (book) setCurrentBook(book)
      else navigate('/')
    }
  }, [bookId, currentBook, books])

  useEffect(() => {
    const book = currentBook ?? books.find((b) => b.id === bookId)
    if (!book) return
    loadProgress(book.id)
    invoke<string>('read_file_text', { path: book.filePath })
      .then((text) => setSpreads(buildSpreads(parseParagraphs(text), CHARS_PER_SPREAD)))
      .catch(() => navigate('/'))
  }, [currentBook?.id])

  useEffect(() => {
    if (spreads.length > 0 && progress) {
      const idx = parseInt(progress.position, 10)
      if (!isNaN(idx) && idx >= 0 && idx < spreads.length) setSpreadIndex(idx)
    }
  }, [spreads, progress])

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveCurrentProgress = useCallback(() => {
    if (!spreads.length || !currentBook) return
    saveProgress(String(spreadIndex), ((spreadIndex + 1) / spreads.length) * 100)
  }, [spreadIndex, spreads, currentBook])

  useEffect(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(saveCurrentProgress, 500)
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current) }
  }, [spreadIndex])

  const goTo = useCallback((nextIdx: number, dir: 'forward' | 'backward') => {
    if (anim) return
    setAnim({ fromIdx: spreadIndex, toIdx: nextIdx, direction: dir })
    if (animTimer.current) clearTimeout(animTimer.current)
    animTimer.current = setTimeout(() => {
      setSpreadIndex(nextIdx)
      setAnim(null)
    }, FLIP_DURATION_MS)
  }, [spreadIndex, anim])

  const goBack    = useCallback(() => { if (spreadIndex > 0) goTo(spreadIndex - 1, 'backward') }, [spreadIndex, goTo])
  const goForward = useCallback(() => { if (spreadIndex < spreads.length - 1) goTo(spreadIndex + 1, 'forward') }, [spreadIndex, spreads.length, goTo])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') { e.preventDefault(); goForward() }
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); goBack() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [goBack, goForward])

  const percentage = spreads.length > 0 ? ((spreadIndex + 1) / spreads.length) * 100 : 0
  const isFirst = spreadIndex === 0 && !anim
  const isLast  = spreadIndex === spreads.length - 1 && !anim

  const textStyle: React.CSSProperties = {
    fontSize: `${settings.fontSize}px`,
    lineHeight: settings.lineHeight,
    fontFamily: FONT_FAMILY[settings.fontFamily] ?? FONT_FAMILY.serif,
  }

  // During animation, compute what to show on the static background and on the flipping element
  // Forward: right page flips (pivot: left edge = spine). Front=old right, back=new left. Behind it: old left + new right.
  // Backward: left page flips (pivot: right edge = spine). Front=old left, back=new right. Behind it: new left + old right.
  const bgLeft    = anim ? (anim.direction === 'forward'  ? spreads[anim.fromIdx][0] : spreads[anim.toIdx][0])   : (spreads[spreadIndex]?.[0] ?? '')
  const bgRight   = anim ? (anim.direction === 'forward'  ? spreads[anim.toIdx][1]   : spreads[anim.fromIdx][1]) : (spreads[spreadIndex]?.[1] ?? '')
  const flipFront = anim ? (anim.direction === 'forward'  ? spreads[anim.fromIdx][1] : spreads[anim.fromIdx][0]) : ''
  const flipBack  = anim ? (anim.direction === 'forward'  ? spreads[anim.toIdx][0]   : spreads[anim.toIdx][1])   : ''
  const flipSide  = anim?.direction === 'backward' ? 'left' : 'right'

  const displayPage = anim ? anim.toIdx : spreadIndex

  return (
    <div className="reader-page" data-theme={settings.theme} style={{ cursor: cursorHidden ? 'none' : undefined }}>
      <ReaderToolbar
        currentPage={displayPage * 2 + 1}
        totalPages={spreads.length * 2}
        percentage={percentage}
      />

      <div className="txt-spread-wrapper">
        <button
          className={`spread-nav spread-nav-left ${arrowsVisible && !isFirst ? 'nav-visible' : ''}`}
          onClick={goBack} aria-label="Previous page" tabIndex={isFirst ? -1 : 0}
        >‹</button>

        {/* Static background spread */}
        <div className="txt-spread">
          <div className="txt-book-page txt-book-page-left">
            <PageText text={bgLeft} style={textStyle} />
            <span className="page-num">{displayPage * 2 + 1}</span>
          </div>
          <div className="txt-book-spine" />
          <div className="txt-book-page txt-book-page-right">
            <PageText text={bgRight} style={textStyle} />
            <span className="page-num">{displayPage * 2 + 2}</span>
          </div>
        </div>

        {/* 3D flipping page — only rendered during animation */}
        {anim && (
          <div className={`flip-container flip-${flipSide}`}>
            <div className="flip-face flip-front">
              <PageText text={flipFront} style={textStyle} />
            </div>
            <div className="flip-face flip-back">
              <PageText text={flipBack} style={textStyle} />
            </div>
          </div>
        )}

        <button
          className={`spread-nav spread-nav-right ${arrowsVisible && !isLast ? 'nav-visible' : ''}`}
          onClick={goForward} aria-label="Next page" tabIndex={isLast ? -1 : 0}
        >›</button>
      </div>
    </div>
  )
}
