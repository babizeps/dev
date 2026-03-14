import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useReaderStore } from './store/reader.store'
import LibraryPage from './pages/LibraryPage'
import PdfReaderPage from './pages/PdfReaderPage'
import EpubReaderPage from './pages/EpubReaderPage'
import TxtReaderPage from './pages/TxtReaderPage'
import './styles/themes.css'
import './App.css'

function ReaderRouter() {
  const { currentBook } = useReaderStore()

  if (!currentBook) return <Navigate to="/" replace />

  switch (currentBook.format) {
    case 'pdf':  return <PdfReaderPage />
    case 'epub': return <EpubReaderPage />
    case 'txt':  return <TxtReaderPage />
    default:     return <Navigate to="/" replace />
  }
}

export default function App() {
  const { loadSettings, settings } = useReaderStore()

  useEffect(() => {
    loadSettings()
  }, [])

  // Apply theme to root so library page also gets themed
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.theme)
  }, [settings.theme])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/read/:bookId" element={<ReaderRouter />} />
      </Routes>
    </BrowserRouter>
  )
}
