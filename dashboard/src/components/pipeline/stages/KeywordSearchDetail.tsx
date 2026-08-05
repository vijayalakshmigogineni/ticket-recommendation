import type { KeywordSearchTrace } from '../../../api/types'
import { formatScore } from '../../../lib/format'
import { ScoredResultsTable } from '../../shared/ScoredResultsTable'
import { TicketBadge } from '../../shared/TicketBadge'

export function KeywordSearchDetail({ trace }: { trace: KeywordSearchTrace }) {
  return (
    <div>
      <p className="mb-2 text-xs text-neutral-500">
        {trace.hits.length} keyword matches (PostgreSQL full-text search, ts_rank). Exact
        identifier matches (claim/patient numbers etc.) aren't tracked as a separate signal --
        ts_rank scores all matched tokens, including alphanumeric identifiers, as part of the same
        score.
      </p>
      <ScoredResultsTable
        rows={trace.hits}
        keyField={(h) => h.interaction_id}
        columns={[
          { header: 'BM25-style Score', render: (h) => formatScore(h.score) },
          { header: 'Ticket', render: (h) => <TicketBadge ticket={h.ticket} /> },
          { header: 'Preview', render: (h) => <span className="text-neutral-400">{h.preview}</span> },
        ]}
      />
    </div>
  )
}
