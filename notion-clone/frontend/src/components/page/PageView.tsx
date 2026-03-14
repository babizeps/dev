import type { Block } from '../../types/block'
import PageTitle from './PageTitle'
import BlockEditor from '../editor/BlockEditor'

interface Props {
  block: Block
  workspaceId: string
}

export default function PageView({ block, workspaceId }: Props) {
  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '60px 80px' }}>
      <PageTitle block={block} workspaceId={workspaceId} />
      <BlockEditor block={block} workspaceId={workspaceId} />
    </div>
  )
}
