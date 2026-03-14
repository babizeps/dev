import type { SlashCommandItem } from '../extensions/SlashCommand'

interface Props {
  items: SlashCommandItem[]
  onSelect: (item: SlashCommandItem) => void
  rect: DOMRect
}

export default function BlockTypeMenu({ items, onSelect, rect }: Props) {
  return (
    <div
      style={{
        position: 'fixed',
        top: rect.bottom + 4,
        left: rect.left,
        background: '#fff',
        border: '1px solid #e9e9e7',
        borderRadius: 8,
        boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
        zIndex: 1000,
        minWidth: 220,
        overflow: 'hidden',
      }}
    >
      {items.length === 0 && (
        <div style={{ padding: '8px 12px', color: '#999', fontSize: 13 }}>No results</div>
      )}
      {items.map((item) => (
        <button
          key={item.title}
          onClick={() => onSelect(item)}
          style={{
            display: 'block',
            width: '100%',
            padding: '8px 12px',
            border: 'none',
            background: 'none',
            textAlign: 'left',
            cursor: 'pointer',
            fontSize: 14,
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#f1f1ef' }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'none' }}
        >
          <div style={{ fontWeight: 500 }}>{item.title}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{item.description}</div>
        </button>
      ))}
    </div>
  )
}
