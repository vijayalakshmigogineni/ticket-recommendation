import type { RerankingTrace } from '../../../api/types'
import { formatScore } from '../../../lib/format'
import { ScoredResultsTable } from '../../shared/ScoredResultsTable'
import { TicketBadge } from '../../shared/TicketBadge'

export function CrossEncoderDetail({ trace }: { trace: RerankingTrace }) {
  return (
    <div>
      <p className="mb-2 text-xs text-neutral-500">Model: {trace.model_name}</p>
      <ScoredResultsTable
        rows={trace.scores}
        keyField={(r) => r.ticket.id}
        columns={[
          { header: 'Cross-Encoder Score', render: (r) => formatScore(r.rerank_score) },
          { header: 'Ticket', render: (r) => <TicketBadge ticket={r.ticket} /> },
        ]}
      />
    </div>
  )
}
