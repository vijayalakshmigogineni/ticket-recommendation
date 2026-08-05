import { Link } from 'react-router-dom'
import { DurationBadge } from '../components/shared/DurationBadge'
import { EmptyState } from '../components/shared/EmptyState'
import { STAGE_LABELS, type StageKey } from '../lib/stageAvailability'
import { useLastRun } from '../hooks/useLastRun'

const TIMING_STAGE_ORDER: StageKey[] = [
  'preprocessing',
  'customer_identification',
  'thread_detection',
  'embedding',
  'keyword_search',
  'ann_search',
  'fusion',
  'grouping',
  'context_building',
  'reranking',
  'decision',
]

// recommender/pipeline_trace.py's raw timing dict keys don't all match the
// StageKey display names used elsewhere in the dashboard -- these two are the
// exceptions (fusion -> hybrid_retrieval, decision -> llm_decision).
const RAW_TIMING_KEY: Partial<Record<StageKey, string>> = {
  fusion: 'hybrid_retrieval',
  decision: 'llm_decision',
}

export function MetricsPage() {
  const lastRun = useLastRun()

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-neutral-100">Metrics</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Latest-run performance breakdown. Historical trend aggregation across many runs is
        deferred (would need a persisted run log) -- this shows the most recent run only.
      </p>

      {!lastRun ? (
        <EmptyState
          message="No run yet in this session."
          action={
            <Link
              to="/playground"
              className="rounded bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-900"
            >
              Go to Playground
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
            <div className="text-xs uppercase tracking-wide text-neutral-500">
              Total Pipeline Time
            </div>
            <div className="mt-1 text-2xl font-semibold text-neutral-100">
              <DurationBadge ms={lastRun.total_time_ms} />
            </div>
          </div>

          <div className="overflow-x-auto rounded border border-neutral-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-neutral-900 text-neutral-500">
                <tr>
                  <th className="px-2 py-1 font-medium">Stage</th>
                  <th className="px-2 py-1 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {TIMING_STAGE_ORDER.map((key) => {
                  const ms = lastRun.stage_timings_ms[RAW_TIMING_KEY[key] ?? key]
                  return (
                    <tr key={key}>
                      <td className="px-2 py-1 text-neutral-300">{STAGE_LABELS[key]}</td>
                      <td className="px-2 py-1">
                        {ms !== undefined ? (
                          <DurationBadge ms={ms} />
                        ) : (
                          <span className="text-neutral-600">skipped</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <Link to="/pipeline" className="text-xs text-neutral-500 hover:underline">
            View full pipeline trace →
          </Link>
        </div>
      )}
    </div>
  )
}
