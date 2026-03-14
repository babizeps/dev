import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLibraryStore } from '../store/library.store'
import { useReaderStore } from '../store/reader.store'
import BookCard from '../components/library/BookCard'
import DropZone from '../components/library/DropZone'
import type { Book } from '../types/book'
import './LibraryPage.css'

export default function LibraryPage() {
  const navigate = useNavigate()
  const { books, isLoading, error, fetchBooks, importBook, removeBook, markOpened } = useLibraryStore()
  const { setCurrentBook } = useReaderStore()

  useEffect(() => {
    fetchBooks()
  }, [])

  const openBook = (book: Book) => {
    setCurrentBook(book)
    markOpened(book.id)
    navigate(`/read/${book.id}`)
  }

  return (
    <div className="library-page">
      <header className="library-header">
        <h1 className="library-title">bookshelf</h1>
        <button className="import-btn" onClick={importBook}>+ Add Book</button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {isLoading ? (
        <div className="loading">Loading library…</div>
      ) : books.length === 0 ? (
        <DropZone />
      ) : (
        <div className="book-grid">
          {books.map((book) => (
            <BookCard
              key={book.id}
              book={book}
              onClick={() => openBook(book)}
              onRemove={() => removeBook(book.id)}
            />
          ))}
          <div
            className="add-card"
            onClick={importBook}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && importBook()}
          >
            <span className="add-icon">+</span>
            <span>Add Book</span>
          </div>
        </div>
      )}
    </div>
  )
}
