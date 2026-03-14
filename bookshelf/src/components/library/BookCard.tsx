import type { Book } from '../../types/book'
import './BookCard.css'

interface Props {
  book: Book
  onClick: () => void
  onRemove: () => void
}

const FORMAT_COLORS: Record<string, string> = {
  pdf: '#e74c3c',
  epub: '#3498db',
  txt: '#27ae60',
}

function ProgressRing({ percentage }: { percentage: number }) {
  const r = 18
  const circ = 2 * Math.PI * r
  const offset = circ - (percentage / 100) * circ
  return (
    <svg className="progress-ring" width={44} height={44} viewBox="0 0 44 44">
      <circle cx={22} cy={22} r={r} fill="none" stroke="var(--border)" strokeWidth={3} />
      <circle
        cx={22} cy={22} r={r}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={3}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 22 22)"
      />
      <text x={22} y={26} textAnchor="middle" fontSize={9} fill="var(--text-secondary)">
        {Math.round(percentage)}%
      </text>
    </svg>
  )
}

export default function BookCard({ book, onClick, onRemove }: Props) {
  return (
    <div className="book-card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}>
      <div className="book-cover" style={{ backgroundColor: FORMAT_COLORS[book.format] ?? '#888' }}>
        <span className="format-badge">{book.format.toUpperCase()}</span>
      </div>
      <div className="book-info">
        <p className="book-title" title={book.title}>{book.title}</p>
        <p className="book-author" title={book.author}>{book.author}</p>
        <ProgressRing percentage={0} />
      </div>
      <button
        className="remove-btn"
        onClick={(e) => { e.stopPropagation(); onRemove() }}
        title="Remove from library"
        aria-label="Remove book"
      >
        ×
      </button>
    </div>
  )
}
