import { useEffect, useRef, useCallback, useState } from 'react'
import { useEditor, EditorContent, BubbleMenu } from '@tiptap/react'
import type { JSONContent } from '@tiptap/react'
import { defaultExtensions } from './extensions/index'
import { createSlashExtension, type SlashCommandItem } from './extensions/SlashCommand'
import BlockTypeMenu from './toolbar/BlockTypeMenu'
import { useBlocksStore } from '../../store/blocks.store'
import type { Block } from '../../types/block'

interface Props {
  block: Block
  workspaceId: string
}

const DEBOUNCE_MS = 600

export default function BlockEditor({ block, workspaceId }: Props) {
  const { updateBlock } = useBlocksStore()
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [slashMenu, setSlashMenu] = useState<{
    items: SlashCommandItem[]
    command: (item: SlashCommandItem) => void
    rect: DOMRect
  } | null>(null)

  const initialContent = (block.content as { tiptapDoc?: JSONContent }).tiptapDoc ?? {
    type: 'doc',
    content: [{ type: 'paragraph' }],
  }

  const save = useCallback(
    (doc: JSONContent) => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        updateBlock(workspaceId, block.id, { ...block.content, tiptapDoc: doc })
      }, DEBOUNCE_MS)
    },
    [workspaceId, block.id, block.content, updateBlock]
  )

  const slashExtension = createSlashExtension(
    (props) => setSlashMenu(props),
    () => setSlashMenu(null)
  )

  const editor = useEditor({
    extensions: [...defaultExtensions, slashExtension],
    content: initialContent,
    onUpdate: ({ editor }) => save(editor.getJSON()),
  })

  useEffect(() => {
    if (!editor) return
    const doc = (block.content as { tiptapDoc?: JSONContent }).tiptapDoc
    if (doc) editor.commands.setContent(doc, false)
  }, [block.id])

  useEffect(() => {
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current) }
  }, [])

  const btnStyle = (active: boolean): React.CSSProperties => ({
    padding: '4px 8px',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    background: active ? '#37352f' : 'transparent',
    color: active ? '#fff' : '#37352f',
    fontSize: 13,
    fontWeight: 600,
  })

  return (
    <div>
      {editor && (
        <BubbleMenu editor={editor} tippyOptions={{ duration: 100 }}>
          <div style={{ background: '#fff', border: '1px solid #e9e9e7', borderRadius: 6, padding: 4, display: 'flex', gap: 2, boxShadow: '0 4px 16px rgba(0,0,0,0.12)' }}>
            <button style={btnStyle(editor.isActive('bold'))} onClick={() => editor.chain().focus().toggleBold().run()}>B</button>
            <button style={{ ...btnStyle(editor.isActive('italic')), fontStyle: 'italic' }} onClick={() => editor.chain().focus().toggleItalic().run()}>I</button>
            <button style={{ ...btnStyle(editor.isActive('code')), fontFamily: 'monospace' }} onClick={() => editor.chain().focus().toggleCode().run()}>{'<>'}</button>
            <button style={btnStyle(editor.isActive('strike'))} onClick={() => editor.chain().focus().toggleStrike().run()}>S̶</button>
          </div>
        </BubbleMenu>
      )}

      <EditorContent editor={editor} style={{ minHeight: 200 }} />

      {slashMenu && (
        <BlockTypeMenu
          items={slashMenu.items}
          rect={slashMenu.rect}
          onSelect={(item) => {
            slashMenu.command(item)
            setSlashMenu(null)
          }}
        />
      )}

      <style>{`
        .tiptap { outline: none; font-size: 16px; line-height: 1.6; }
        .tiptap p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          color: #aaa;
          pointer-events: none;
          float: left;
          height: 0;
        }
        .tiptap h1 { font-size: 2em; font-weight: 700; margin: 0.5em 0 0.2em; }
        .tiptap h2 { font-size: 1.5em; font-weight: 600; margin: 0.5em 0 0.2em; }
        .tiptap h3 { font-size: 1.25em; font-weight: 600; margin: 0.5em 0 0.2em; }
        .tiptap ul, .tiptap ol { padding-left: 1.5em; }
        .tiptap code { background: #f1f1ef; border-radius: 3px; padding: 2px 4px; font-family: monospace; font-size: 0.9em; }
        .tiptap pre { background: #f1f1ef; border-radius: 6px; padding: 12px; margin: 8px 0; overflow-x: auto; }
        .tiptap pre code { background: none; padding: 0; }
        .tiptap hr { border: none; border-top: 1px solid #e9e9e7; margin: 16px 0; }
        .tiptap li[data-type="taskItem"] { display: flex; align-items: flex-start; gap: 8px; }
        .tiptap li[data-type="taskItem"] > label { margin-top: 3px; }
      `}</style>
    </div>
  )
}
