import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReaderStore } from '../../store/reader.store'
import type { Theme, FontFamily } from '../../types/book'
import './ReaderToolbar.css'

interface Props {
  currentPage?: number
  totalPages?: number
  percentage?: number
}

export default function ReaderToolbar({ currentPage, totalPages, percentage }: Props) {
  const navigate = useNavigate()
  const { currentBook, settings, updateSettings, isToolbarVisible, setToolbarVisible } = useReaderStore()
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const scheduleHide = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current)
    hideTimer.current = setTimeout(() => setToolbarVisible(false), 3000)
  }

  useEffect(() => {
    const NAV_KEYS = new Set(['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' '])
    const showMouse = () => { setToolbarVisible(true); scheduleHide() }
    const showKey = (e: KeyboardEvent) => { if (!NAV_KEYS.has(e.key)) { setToolbarVisible(true); scheduleHide() } }
    window.addEventListener('mousemove', showMouse)
    window.addEventListener('keydown', showKey)
    scheduleHide()
    return () => {
      window.removeEventListener('mousemove', showMouse)
      window.removeEventListener('keydown', showKey)
      if (hideTimer.current) clearTimeout(hideTimer.current)
    }
  }, [])

  const themes: Theme[] = ['light', 'dark', 'sepia']
  const fonts: { value: FontFamily; label: string }[] = [
    { value: 'serif', label: 'Serif' },
    { value: 'sans-serif', label: 'Sans' },
    { value: 'monospace', label: 'Mono' },
  ]

  return (
    <div className={`reader-toolbar ${isToolbarVisible ? 'visible' : 'hidden'}`}>
      <div className="toolbar-left">
        <button className="toolbar-btn icon-btn" onClick={() => navigate('/')} title="Back to library">
          ← Library
        </button>
        <span className="book-title-display">{currentBook?.title}</span>
      </div>

      <div className="toolbar-center">
        {currentPage != null && (
          <span className="page-indicator">
            {currentPage}{totalPages ? ` / ${totalPages}` : ''}
            {percentage != null && ` · ${Math.round(percentage)}%`}
          </span>
        )}
      </div>

      <div className="toolbar-right">
        <div className="font-size-control">
          <button className="toolbar-btn" onClick={() => updateSettings({ fontSize: Math.max(12, settings.fontSize - 1) })}>A−</button>
          <span className="font-size-label">{settings.fontSize}px</span>
          <button className="toolbar-btn" onClick={() => updateSettings({ fontSize: Math.min(32, settings.fontSize + 1) })}>A+</button>
        </div>

        <div className="font-family-control">
          {fonts.map((f) => (
            <button
              key={f.value}
              className={`toolbar-btn ${settings.fontFamily === f.value ? 'active' : ''}`}
              onClick={() => updateSettings({ fontFamily: f.value })}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="theme-control">
          {themes.map((t) => (
            <button
              key={t}
              className={`theme-dot theme-${t} ${settings.theme === t ? 'active' : ''}`}
              onClick={() => updateSettings({ theme: t })}
              title={t}
              aria-label={`${t} theme`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
