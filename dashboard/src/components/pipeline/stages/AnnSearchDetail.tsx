import type { AnnSearchTrace } from '../../../api/types'
import { formatScore } from '../../../lib/format'
import { ScoredResultsTable } from '../../shared/ScoredResultsTable'
import { TicketBadge } from '../../shared/TicketBadge'

export function AnnSearchDetail({ trace }: { trace: AnnSearchTrace }) {
  return (
    <div>
      <p className="mb-2 text-xs text-neutral-500">
        Top {trace.hits.length} semantic matches via pgvector HNSW (cosine similarity).
      </p>
      <ScoredResultsTable
        rows={trace.hits}
        keyField={(h) => h.interaction_id}
        columns={[
          { header: 'Similarity', render: (h) => formatScore(h.score) },
          {
            header: 'Interaction ID',
            render: (h) => <span className="font-mono text-neutral-500">{h.interaction_id.slice(0, 8)}</span>,
          },
          { header: 'Ticket', render: (h) => <TicketBadge ticket={h.ticket} /> },
          { header: 'Preview', render: (h) => <span className="text-neutral-400">{h.preview}</span> },
        ]}
      />
    </div>
  )
}
