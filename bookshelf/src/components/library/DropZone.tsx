import { useState } from 'react'
import { useLibraryStore } from '../../store/library.store'
import './DropZone.css'

export default function DropZone() {
  const { importBook } = useLibraryStore()
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    const { importBookByPath } = useLibraryStore.getState()
    for (const file of files) {
      if (/\.(pdf|epub|txt)$/i.test(file.name)) {
        await importBookByPath((file as any).path)
      }
    }
  }

  return (
    <div
      className={`dropzone ${isDragging ? 'dragging' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={importBook}
    >
      <div className="dropzone-icon">📚</div>
      <p className="dropzone-title">Drop books here</p>
      <p className="dropzone-sub">or click to browse for PDF, EPUB, or TXT files</p>
    </div>
  )
}
