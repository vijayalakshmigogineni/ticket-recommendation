import { formatScore } from '../../lib/format'
import { TicketBadge } from '../shared/TicketBadge'
import type { TicketRef } from '../../api/types'

interface SideBySideComparisonPanelProps {
  queryText: string
  neighborText: string
  score: number
  neighborTicket?: TicketRef | null
}

export function SideBySideComparisonPanel({
  queryText,
  neighborText,
  score,
  neighborTicket,
}: SideBySideComparisonPanelProps) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-xs text-neutral-400">
        <span>Why retrieved -- similarity score:</span>
        <span className="font-mono text-neutral-200">{formatScore(score)}</span>
        {neighborTicket && <TicketBadge ticket={neighborTicket} />}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="mb-1 text-xs font-medium text-neutral-500">Query</div>
          <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
            {queryText}
          </p>
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-neutral-500">Neighbor</div>
          <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
            {neighborText}
          </p>
        </div>
      </div>
    </div>
  )
}
