import type { ContextBuildingTrace } from '../../../api/types'
import { CodeBlock } from '../../shared/CodeBlock'
import { TicketBadge } from '../../shared/TicketBadge'

export function ContextBuilderDetail({ trace }: { trace: ContextBuildingTrace }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-neutral-500">
        Matched interaction(s) + neighboring interactions + ticket metadata, merged in
        chronological order. No summarization -- this is exactly what gets sent to the cross
        encoder.
      </p>
      {trace.contexts.map((ctx) => (
        <div key={ctx.ticket.id}>
          <div className="mb-1 flex items-center justify-between">
            <TicketBadge ticket={ctx.ticket} />
            <span className="text-xs text-neutral-600">{ctx.char_count} chars</span>
          </div>
          <CodeBlock text={ctx.text} label="Final context sent to cross-encoder" />
        </div>
      ))}
    </div>
  )
}
