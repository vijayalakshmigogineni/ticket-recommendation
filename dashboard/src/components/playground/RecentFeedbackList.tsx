import { useQuery } from '@tanstack/react-query'
import { listFeedback } from '../../api/feedback'
import { queryKeys } from '../../api/queryKeys'
import { formatDateTime, truncate } from '../../lib/format'
import { ErrorBanner } from '../shared/ErrorBanner'
import { LoadingSkeleton } from '../shared/LoadingSkeleton'
import { ScoredResultsTable } from '../shared/ScoredResultsTable'
import { TicketBadge } from '../shared/TicketBadge'

export function RecentFeedbackList() {
  const feedbackQuery = useQuery({
    queryKey: queryKeys.feedback({ limit: 10 }),
    queryFn: ({ signal }) => listFeedback({ limit: 10 }, signal),
  })

  return (
    <div>
      <h2 className="mb-2 text-sm font-medium text-neutral-300">Recent Feedback</h2>
      {feedbackQuery.isLoading && <LoadingSkeleton count={3} />}
      {feedbackQuery.isError && (
        <ErrorBanner error={feedbackQuery.error} onRetry={() => feedbackQuery.refetch()} />
      )}
      {feedbackQuery.data && (
        <ScoredResultsTable
          rows={feedbackQuery.data.items}
          keyField={(f) => f.id}
          emptyMessage="No feedback recorded yet -- accept or reject a recommendation in the Playground."
          columns={[
            { header: 'When', render: (f) => formatDateTime(f.created_at) },
            { header: 'Customer', render: (f) => f.customer.name },
            { header: 'Subject', render: (f) => truncate(f.subject, 60) },
            {
              header: 'Verdict',
              render: (f) => (
                <span className={f.manager_decision === 'accepted' ? 'text-emerald-400' : 'text-red-400'}>
                  {f.manager_decision}
                </span>
              ),
            },
            {
              header: 'Ticket',
              render: (f) =>
                f.manager_decision === 'rejected' && f.corrected_ticket ? (
                  <span>
                    <span className="text-neutral-600 line-through">
                      {f.recommended_ticket?.subject ?? 'no match'}
                    </span>{' '}
                    → <TicketBadge ticket={f.corrected_ticket} />
                  </span>
                ) : f.recommended_ticket ? (
                  <TicketBadge ticket={f.recommended_ticket} />
                ) : (
                  <span className="text-neutral-600">no match</span>
                ),
            },
          ]}
        />
      )}
    </div>
  )
}
