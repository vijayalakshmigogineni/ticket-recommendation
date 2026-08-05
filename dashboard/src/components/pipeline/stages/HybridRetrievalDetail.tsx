import type { FusionTrace } from '../../../api/types'
import { formatScore } from '../../../lib/format'
import { ScoredResultsTable } from '../../shared/ScoredResultsTable'
import { TicketBadge } from '../../shared/TicketBadge'

export function HybridRetrievalDetail({ trace }: { trace: FusionTrace }) {
  return (
    <div>
      <p className="mb-2 text-xs text-neutral-500">
        Keyword + ANN results merged via Reciprocal Rank Fusion (k={trace.rrf_k}) into the top{' '}
        {trace.hits.length} matching interactions.
      </p>
      <ScoredResultsTable
        rows={trace.hits}
        keyField={(h) => h.interaction_id}
        columns={[
          { header: 'RRF Score', render: (h) => formatScore(h.fused_score, 5) },
          {
            header: 'Keyword Score',
            render: (h) => (h.keyword_score !== null ? formatScore(h.keyword_score) : '—'),
          },
          {
            header: 'ANN Score',
            render: (h) => (h.ann_score !== null ? formatScore(h.ann_score) : '—'),
          },
          { header: 'Ticket', render: (h) => <TicketBadge ticket={h.ticket} /> },
          { header: 'Preview', render: (h) => <span className="text-neutral-400">{h.preview}</span> },
        ]}
      />
    </div>
  )
}
