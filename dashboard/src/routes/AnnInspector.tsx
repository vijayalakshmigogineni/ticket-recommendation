import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { listCustomers } from '../api/customers'
import { getInteraction, listInteractions } from '../api/interactions'
import { queryKeys } from '../api/queryKeys'
import { postVectorSearch } from '../api/search'
import type { InteractionDetailResponse, VectorSearchResponse } from '../api/types'
import { QuerySourceToggle, type QuerySource } from '../components/ann-inspector/QuerySourceToggle'
import { SideBySideComparisonPanel } from '../components/ann-inspector/SideBySideComparisonPanel'
import { DurationBadge } from '../components/shared/DurationBadge'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton'
import { ScoredResultsTable } from '../components/shared/ScoredResultsTable'
import { TicketBadge } from '../components/shared/TicketBadge'
import { VectorPreviewChips } from '../components/shared/VectorPreviewChips'
import { formatScore } from '../lib/format'

function ExistingInteractionMode() {
  const [interactionId, setInteractionId] = useState('')
  const [selectedNeighborIdx, setSelectedNeighborIdx] = useState<number | null>(null)

  const listQuery = useQuery({
    queryKey: queryKeys.interactions({ has_embedding: true, limit: 200 }),
    queryFn: ({ signal }) => listInteractions({ has_embedding: true, limit: 200 }, signal),
  })

  const detailQuery = useQuery({
    queryKey: queryKeys.interaction(interactionId, 20),
    queryFn: ({ signal }) => getInteraction(interactionId, 20, signal),
    enabled: !!interactionId,
  })

  const detail: InteractionDetailResponse | undefined = detailQuery.data
  const selectedNeighbor =
    selectedNeighborIdx !== null ? detail?.nearest_neighbors[selectedNeighborIdx] : undefined

  return (
    <div className="space-y-4">
      <select
        value={interactionId}
        onChange={(e) => {
          setInteractionId(e.target.value)
          setSelectedNeighborIdx(null)
        }}
        className="w-full max-w-xl rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-xs text-neutral-200"
      >
        <option value="">Select an interaction…</option>
        {listQuery.data?.items.map((i) => (
          <option key={i.id} value={i.id}>
            [{i.interaction_type}] {i.clean_content_preview.slice(0, 80)}
          </option>
        ))}
      </select>

      {detailQuery.isLoading && <LoadingSkeleton count={2} />}
      {detailQuery.isError && (
        <ErrorBanner error={detailQuery.error} onRetry={() => detailQuery.refetch()} />
      )}

      {detail && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="mb-1 text-xs font-medium text-neutral-400">Selected interaction</div>
              <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
                {detail.interaction.clean_content}
              </p>
              {detail.interaction.embedding_stats && (
                <div className="mt-2">
                  <div className="mb-1 text-xs text-neutral-500">
                    model: {detail.interaction.embedding_stats.model} · dim:{' '}
                    {detail.interaction.embedding_stats.dimension}
                  </div>
                  <VectorPreviewChips values={detail.interaction.embedding_stats.preview_first_20} />
                </div>
              )}
            </div>
            <div>
              <div className="mb-1 text-xs font-medium text-neutral-400">
                Nearest neighbors (click a row for side-by-side)
              </div>
              <ScoredResultsTable
                rows={detail.nearest_neighbors}
                keyField={(n) => n.interaction.id}
                columns={[
                  { header: 'Score', render: (n) => formatScore(n.score) },
                  { header: 'Ticket', render: (n) => <TicketBadge ticket={n.ticket} /> },
                  {
                    header: 'Preview',
                    render: (n) => (
                      <button
                        type="button"
                        className="text-left text-neutral-400 hover:underline"
                        onClick={() =>
                          setSelectedNeighborIdx(
                            detail.nearest_neighbors.findIndex(
                              (x) => x.interaction.id === n.interaction.id,
                            ),
                          )
                        }
                      >
                        {n.interaction.clean_content_preview}
                      </button>
                    ),
                  },
                ]}
              />
            </div>
          </div>

          {selectedNeighbor && (
            <SideBySideComparisonPanel
              queryText={detail.interaction.clean_content}
              neighborText={selectedNeighbor.interaction.clean_content_preview}
              score={selectedNeighbor.score}
              neighborTicket={selectedNeighbor.ticket}
            />
          )}
        </>
      )}
    </div>
  )
}

function TypedQueryMode() {
  const [text, setText] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [selectedHitIdx, setSelectedHitIdx] = useState<number | null>(null)

  const customersQuery = useQuery({
    queryKey: queryKeys.customers,
    queryFn: ({ signal }) => listCustomers(signal),
  })

  const mutation = useMutation({
    mutationFn: () =>
      postVectorSearch({ text, customer_id: customerId || undefined, top_n: 20 }),
    retry: false,
  })

  const result: VectorSearchResponse | undefined = mutation.data
  const selectedHit = selectedHitIdx !== null ? result?.hits[selectedHitIdx] : undefined

  return (
    <div className="space-y-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste or type an email body to search against the embedding space…"
        rows={4}
        className="w-full rounded border border-neutral-800 bg-neutral-900 p-2 text-xs text-neutral-200"
      />
      <div className="flex items-center gap-2">
        <select
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
        >
          <option value="">Global (all customers)</option>
          {customersQuery.data?.items.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} (scoped)
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={!text.trim() || mutation.isPending}
          onClick={() => {
            setSelectedHitIdx(null)
            mutation.mutate()
          }}
          className="rounded bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-900 disabled:opacity-40"
        >
          {mutation.isPending ? 'Searching…' : 'Run ANN Search'}
        </button>
      </div>

      {mutation.isError && <ErrorBanner error={mutation.error} />}

      {result && (
        <>
          <div className="flex flex-wrap gap-2 text-xs text-neutral-500">
            <span>model: {result.model}</span>
            <span>dim: {result.dimension}</span>
            <span>embed: <DurationBadge ms={result.embedding_time_ms} /></span>
            <span>search: <DurationBadge ms={result.search_time_ms} /></span>
            <span>total: <DurationBadge ms={result.total_time_ms} /></span>
          </div>

          <ScoredResultsTable
            rows={result.hits}
            keyField={(h) => h.interaction_id}
            columns={[
              { header: 'Score', render: (h) => formatScore(h.score) },
              { header: 'Ticket', render: (h) => <TicketBadge ticket={h.ticket} /> },
              {
                header: 'Preview',
                render: (h, idx) => (
                  <button
                    type="button"
                    className="text-left text-neutral-400 hover:underline"
                    onClick={() => setSelectedHitIdx(idx)}
                  >
                    {h.clean_content_preview}
                  </button>
                ),
              },
            ]}
          />

          {selectedHit && (
            <SideBySideComparisonPanel
              queryText={text}
              neighborText={selectedHit.clean_content_preview}
              score={selectedHit.score}
              neighborTicket={selectedHit.ticket}
            />
          )}
        </>
      )}
    </div>
  )
}

export function AnnInspector() {
  const [mode, setMode] = useState<QuerySource>('existing')

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-neutral-100">ANN Inspector</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Similarity scores, neighbors, and why an interaction would be retrieved.
      </p>
      <div className="mb-4">
        <QuerySourceToggle value={mode} onChange={setMode} />
      </div>
      {mode === 'existing' ? <ExistingInteractionMode /> : <TypedQueryMode />}
    </div>
  )
}
