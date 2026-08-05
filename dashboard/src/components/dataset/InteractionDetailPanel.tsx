import { useQuery } from '@tanstack/react-query'
import { getInteraction } from '../../api/interactions'
import { queryKeys } from '../../api/queryKeys'
import { formatDateTime, formatScore } from '../../lib/format'
import { ErrorBanner } from '../shared/ErrorBanner'
import { LoadingSkeleton } from '../shared/LoadingSkeleton'
import { ScoredResultsTable } from '../shared/ScoredResultsTable'
import { TicketBadge } from '../shared/TicketBadge'
import { VectorPreviewChips } from '../shared/VectorPreviewChips'

export function InteractionDetailPanel({ interactionId }: { interactionId: string }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: queryKeys.interaction(interactionId, 10),
    queryFn: ({ signal }) => getInteraction(interactionId, 10, signal),
  })

  if (isLoading) return <LoadingSkeleton count={3} />
  if (isError) return <ErrorBanner error={error} onRetry={() => refetch()} />
  if (!data) return null

  const { interaction, nearest_neighbors } = data

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-500">
        <span>{interaction.interaction_type}</span>
        <span>·</span>
        <span>{interaction.sender_email}</span>
        <span>·</span>
        <span>{formatDateTime(interaction.created_at)}</span>
        {interaction.ticket && (
          <>
            <span>·</span>
            <TicketBadge ticket={interaction.ticket} />
          </>
        )}
      </div>

      <div>
        <div className="mb-1 text-xs font-medium text-neutral-400">Content</div>
        <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
          {interaction.clean_content}
        </p>
      </div>

      {interaction.embedding_stats ? (
        <div>
          <div className="mb-1 text-xs font-medium text-neutral-400">Embedding</div>
          <div className="mb-2 grid grid-cols-4 gap-2 text-xs text-neutral-400">
            <div>
              model <div className="text-neutral-200">{interaction.embedding_stats.model}</div>
            </div>
            <div>
              dimension <div className="text-neutral-200">{interaction.embedding_stats.dimension}</div>
            </div>
            <div>
              norm <div className="text-neutral-200">{formatScore(interaction.embedding_stats.norm)}</div>
            </div>
            <div>
              min / max{' '}
              <div className="text-neutral-200">
                {formatScore(interaction.embedding_stats.min)} / {formatScore(interaction.embedding_stats.max)}
              </div>
            </div>
          </div>
          <VectorPreviewChips
            values={interaction.embedding_stats.preview_first_20}
            dimension={interaction.embedding_stats.dimension}
          />
        </div>
      ) : (
        <p className="text-xs text-neutral-600">Not embedded (internal note / system event).</p>
      )}

      <div>
        <div className="mb-1 text-xs font-medium text-neutral-400">
          Nearest neighbors (why this would be retrieved)
        </div>
        <ScoredResultsTable
          rows={nearest_neighbors}
          keyField={(n) => n.interaction.id}
          columns={[
            { header: 'Score', render: (n) => formatScore(n.score) },
            { header: 'Ticket', render: (n) => <TicketBadge ticket={n.ticket} /> },
            {
              header: 'Preview',
              render: (n) => (
                <span className="text-neutral-400">{n.interaction.clean_content_preview}</span>
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}
