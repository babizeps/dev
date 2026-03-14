import { Extension } from '@tiptap/core'
import Suggestion, { type SuggestionOptions } from '@tiptap/suggestion'
import type { Editor } from '@tiptap/react'

export interface SlashCommandItem {
  title: string
  description: string
  command: (editor: Editor) => void
}

export const SLASH_ITEMS: SlashCommandItem[] = [
  {
    title: 'Text',
    description: 'Plain paragraph',
    command: (editor) => editor.chain().focus().setParagraph().run(),
  },
  {
    title: 'Heading 1',
    description: 'Large heading',
    command: (editor) => editor.chain().focus().setHeading({ level: 1 }).run(),
  },
  {
    title: 'Heading 2',
    description: 'Medium heading',
    command: (editor) => editor.chain().focus().setHeading({ level: 2 }).run(),
  },
  {
    title: 'Heading 3',
    description: 'Small heading',
    command: (editor) => editor.chain().focus().setHeading({ level: 3 }).run(),
  },
  {
    title: 'Bullet List',
    description: 'Unordered list',
    command: (editor) => editor.chain().focus().toggleBulletList().run(),
  },
  {
    title: 'Numbered List',
    description: 'Ordered list',
    command: (editor) => editor.chain().focus().toggleOrderedList().run(),
  },
  {
    title: 'To-do',
    description: 'Checkbox list',
    command: (editor) => editor.chain().focus().toggleTaskList().run(),
  },
  {
    title: 'Code',
    description: 'Code block',
    command: (editor) => editor.chain().focus().toggleCodeBlock().run(),
  },
  {
    title: 'Divider',
    description: 'Horizontal rule',
    command: (editor) => editor.chain().focus().setHorizontalRule().run(),
  },
]

function filterItems(query: string) {
  return SLASH_ITEMS.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase())
  )
}

export function createSlashExtension(
  onOpen: (props: { items: SlashCommandItem[]; command: (item: SlashCommandItem) => void; rect: DOMRect }) => void,
  onClose: () => void
) {
  return Extension.create({
    name: 'slashCommand',
    addOptions() {
      return { suggestion: {} as SuggestionOptions }
    },
    addProseMirrorPlugins() {
      return [
        Suggestion({
          editor: this.editor,
          char: '/',
          command: ({ editor, range, props }) => {
            props.command(editor)
            editor.chain().focus().deleteRange(range).run()
          },
          items: ({ query }) => filterItems(query),
          render: () => {
            let currentProps: { items: SlashCommandItem[]; command: (item: SlashCommandItem) => void }
            return {
              onStart: (props) => {
                currentProps = props as typeof currentProps
                const rect = props.clientRect?.() ?? new DOMRect()
                onOpen({ items: props.items as SlashCommandItem[], command: props.command as (item: SlashCommandItem) => void, rect })
              },
              onUpdate: (props) => {
                currentProps = props as typeof currentProps
                const rect = props.clientRect?.() ?? new DOMRect()
                onOpen({ items: props.items as SlashCommandItem[], command: props.command as (item: SlashCommandItem) => void, rect })
              },
              onKeyDown: () => false,
              onExit: () => { onClose() },
            }
          },
        }),
      ]
    },
  })
}
