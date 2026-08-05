import { useState } from 'react'
import { StageDetailPanel } from '../components/pipeline/StageDetailPanel'
import { StageTimeline } from '../components/pipeline/StageTimeline'
import { EmailInputForm } from '../components/playground/EmailInputForm'
import { DurationBadge } from '../components/shared/DurationBadge'
import { EmptyState } from '../components/shared/EmptyState'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { StatTile } from '../components/shared/StatTile'
import { TicketBadge } from '../components/shared/TicketBadge'
import { useLastCompare } from '../hooks/useLastCompare'
import { useRunCompare } from '../hooks/useRunCompare'
import type { RunTraceResponse } from '../api/types'
import { formatMs } from '../lib/format'
import type { StageKey } from '../lib/stageAvailability'

function decisionLabel(trace: RunTraceResponse): string {
  if (trace.path === 'unknown_customer') return 'Unknown customer'
  if (trace.path === 'auto_attach') return 'Auto-attached (thread match)'
  if (!trace.decision) return '—'
  return trace.decision.should_attach ? 'Attach' : 'No match'
}

function PipelineColumn({
  title,
  trace,
  selectedStage,
  onSelectStage,
}: {
  title: string
  trace: RunTraceResponse
  selectedStage: StageKey
  onSelectStage: (stage: StageKey) => void
}) {
  const rerankTimeMs = trace.stage_timings_ms['reranking']

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-100">{title}</h2>
        <DurationBadge ms={trace.total_time_ms} />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2">
        <StatTile label="Cross-Encoder Time" value={rerankTimeMs !== undefined ? formatMs(rerankTimeMs) : 'N/A'} />
        <StatTile label="Total Time" value={formatMs(trace.total_time_ms)} />
        <StatTile label="Decision" value={decisionLabel(trace)} />
        <StatTile
          label="Confidence"
          value={trace.decision ? `${(trace.decision.confidence * 100).toFixed(0)}%` : '—'}
        />
      </div>

      {trace.decision?.ticket && (
        <div className="mb-4">
          <span className="mr-2 text-xs text-neutral-500">Recommended ticket:</span>
          <TicketBadge ticket={trace.decision.ticket} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-3">
        <StageTimeline trace={trace} selectedStage={selectedStage} onSelectStage={onSelectStage} />
        <div className="rounded border border-neutral-800 bg-neutral-900 p-4">
          <StageDetailPanel trace={trace} stage={selectedStage} />
        </div>
      </div>
    </div>
  )
}

export function PipelineComparison() {
  const lastCompare = useLastCompare()
  const compareMutation = useRunCompare()
  const [selectedStage, setSelectedStage] = useState<StageKey>('incoming_email')

  const compare = compareMutation.data ?? lastCompare

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-neutral-100">Pipeline Comparison</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Runs the same email through the production pipeline (with cross-encoder) and an
        experimental variant that skips it, taking the top candidates directly from grouping's
        final_score. Use this to isolate whether the cross-encoder is actually the bottleneck.
      </p>

      {compareMutation.isError && <ErrorBanner error={compareMutation.error} />}

      {!compare ? (
        <EmptyState
          message="No comparison run yet in this session -- run one below."
          action={
            <div className="w-full max-w-xl text-left">
              <EmailInputForm
                onSubmit={(req) => compareMutation.mutate(req)}
                isSubmitting={compareMutation.isPending}
                submitLabel="Run Comparison"
              />
            </div>
          }
        />
      ) : (
        <div>
          {compareMutation.isPending && (
            <p className="mb-3 text-xs text-neutral-500">
              Running both pipelines (two LLM decision calls) -- this can take a couple of
              minutes on local hardware…
            </p>
          )}
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <PipelineColumn
              title="Original Pipeline (With Cross-Encoder)"
              trace={compare.with_reranker}
              selectedStage={selectedStage}
              onSelectStage={setSelectedStage}
            />
            <PipelineColumn
              title="Experimental Pipeline (Without Cross-Encoder)"
              trace={compare.no_reranker}
              selectedStage={selectedStage}
              onSelectStage={setSelectedStage}
            />
          </div>

          <div className="mt-6 max-w-xl">
            <EmailInputForm
              onSubmit={(req) => compareMutation.mutate(req)}
              isSubmitting={compareMutation.isPending}
              submitLabel="Run Comparison Again"
            />
          </div>
        </div>
      )}
    </div>
  )
}
