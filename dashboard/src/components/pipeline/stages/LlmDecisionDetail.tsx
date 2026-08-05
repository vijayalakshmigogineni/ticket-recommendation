import type { DecisionTrace } from '../../../api/types'
import { CodeBlock } from '../../shared/CodeBlock'
import { TicketBadge } from '../../shared/TicketBadge'

export function LlmDecisionDetail({ trace }: { trace: DecisionTrace }) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-neutral-500">Model: {trace.model}</p>
      <CodeBlock text={trace.system_prompt} label="System Prompt" />
      <CodeBlock text={trace.user_prompt ?? ''} label="User Prompt" />
      <div className="rounded border border-neutral-800 p-3">
        <div className="mb-2 flex items-center gap-3 text-xs">
          <span
            className={trace.should_attach ? 'text-emerald-400' : 'text-neutral-400'}
          >
            should_attach: {String(trace.should_attach)}
          </span>
          <span className="text-neutral-400">
            confidence: {(trace.confidence * 100).toFixed(0)}%
          </span>
          {trace.ticket && <TicketBadge ticket={trace.ticket} />}
        </div>
        <p className="text-xs text-neutral-300">{trace.explanation}</p>
      </div>
    </div>
  )
}
