import { useQuery } from '@tanstack/react-query'
import { getEvaluationStatus } from '../api/evaluation'
import { queryKeys } from '../api/queryKeys'
import type { EvalRunSummary } from '../api/types'
import { ResultPill, RunResultsTable } from '../components/evaluation/RunResultsTable'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton'
import { StatTile } from '../components/shared/StatTile'

function pct(correct: number, total: number): string {
  return total > 0 ? `${Math.round((100 * correct) / total)}%` : '—'
}

function ratioStatus(correct: number, total: number): 'ok' | 'warn' | 'neutral' {
  if (total === 0) return 'neutral'
  return correct === total ? 'ok' : 'warn'
}

function HistoryTable({ history }: { history: EvalRunSummary[] }) {
  return (
    <div className="overflow-x-auto rounded border border-neutral-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-neutral-900 text-neutral-500">
          <tr>
            <th className="px-2 py-1 font-medium">Date</th>
            <th className="px-2 py-1 font-medium">Source</th>
            <th className="px-2 py-1 font-medium">Queries</th>
            <th className="px-2 py-1 font-medium">Clear-case accuracy</th>
            <th className="px-2 py-1 font-medium">Recall@20</th>
            <th className="px-2 py-1 font-medium">Recall@3</th>
            <th className="px-2 py-1 font-medium">Hard passed</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800">
          {history.map((run) => (
            <tr key={run.source_file}>
              <td className="px-2 py-1 text-neutral-300">{run.generated_at ?? '—'}</td>
              <td className="px-2 py-1 text-neutral-500">{run.source_file}</td>
              <td className="px-2 py-1 text-neutral-400">{run.total_queries}</td>
              <td className="px-2 py-1 text-neutral-300">
                {run.clear_correct}/{run.clear_total} ({pct(run.clear_correct, run.clear_total)})
              </td>
              <td className="px-2 py-1 text-neutral-400">
                {run.recall20_correct}/{run.recall20_total}
              </td>
              <td className="px-2 py-1 text-neutral-400">
                {run.recall3_correct}/{run.recall3_total}
              </td>
              <td className="px-2 py-1 text-neutral-400">
                {run.hard_correct}/{run.hard_total}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function EvaluationPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: queryKeys.evaluationStatus,
    queryFn: ({ signal }) => getEvaluationStatus(signal),
  })

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-neutral-100">Evaluation</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Regression benchmark results from{' '}
        <code className="text-neutral-400">data/sample_dataset/eval_queries.py</code>, scored by{' '}
        <code className="text-neutral-400">scripts/run_eval.py</code>. Clear-case accuracy is the
        headline reliability number; hard/ambiguous cases are tracked separately and don't count
        against it.
      </p>

      {isLoading && <LoadingSkeleton shape="tile" count={4} />}
      {isError && <ErrorBanner error={error} onRetry={() => refetch()} />}

      {data && !data.latest && (
        <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-sm text-neutral-500">
          {data.message}
        </div>
      )}

      {data?.latest && (
        <div className="space-y-6">
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold text-neutral-300">Latest run</h2>
              <span className="text-xs text-neutral-500">
                {data.latest.generated_at ?? data.latest.source_file} &middot;{' '}
                {data.latest.source_file}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile
                label="Clear-case accuracy"
                value={pct(data.latest.clear_correct, data.latest.clear_total)}
                sublabel={`${data.latest.clear_correct}/${data.latest.clear_total}`}
                status={ratioStatus(data.latest.clear_correct, data.latest.clear_total)}
              />
              <StatTile
                label="Recall@20"
                value={pct(data.latest.recall20_correct, data.latest.recall20_total)}
                sublabel={`${data.latest.recall20_correct}/${data.latest.recall20_total}`}
                status={ratioStatus(data.latest.recall20_correct, data.latest.recall20_total)}
              />
              <StatTile
                label="Recall@3"
                value={pct(data.latest.recall3_correct, data.latest.recall3_total)}
                sublabel={`${data.latest.recall3_correct}/${data.latest.recall3_total}`}
                status={ratioStatus(data.latest.recall3_correct, data.latest.recall3_total)}
              />
              <StatTile
                label="Hard cases passed"
                value={`${data.latest.hard_correct}/${data.latest.hard_total}`}
                sublabel="informational, not in headline accuracy"
                status="neutral"
              />
            </div>
          </div>

          {data.latest.categories.length > 1 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold text-neutral-300">
                Category breakdown (clear-difficulty cases)
              </h2>
              <div className="overflow-x-auto rounded border border-neutral-800">
                <table className="w-full text-left text-xs">
                  <thead className="bg-neutral-900 text-neutral-500">
                    <tr>
                      <th className="px-2 py-1 font-medium">Category</th>
                      <th className="px-2 py-1 font-medium">Accuracy</th>
                      <th className="px-2 py-1 font-medium">Recall@20</th>
                      <th className="px-2 py-1 font-medium">Recall@3</th>
                      <th className="px-2 py-1 font-medium">Avg. confidence (correct)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800">
                    {data.latest.categories.map((c) => (
                      <tr key={c.category}>
                        <td className="px-2 py-1 text-neutral-300">{c.category}</td>
                        <td className="px-2 py-1 text-neutral-400">
                          {c.clear_correct}/{c.clear_total} ({pct(c.clear_correct, c.clear_total)})
                        </td>
                        <td className="px-2 py-1 text-neutral-400">
                          {c.recall20_correct}/{c.recall20_total}
                        </td>
                        <td className="px-2 py-1 text-neutral-400">
                          {c.recall3_correct}/{c.recall3_total}
                        </td>
                        <td className="px-2 py-1 text-neutral-400">
                          {c.avg_confidence_correct !== null
                            ? c.avg_confidence_correct.toFixed(2)
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.latest.hard_cases.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold text-neutral-300">
                Hard / deliberately-ambiguous cases
              </h2>
              <div className="overflow-x-auto rounded border border-neutral-800">
                <table className="w-full text-left text-xs">
                  <thead className="bg-neutral-900 text-neutral-500">
                    <tr>
                      <th className="px-2 py-1 font-medium">Key</th>
                      <th className="px-2 py-1 font-medium">Result</th>
                      <th className="px-2 py-1 font-medium">Got</th>
                      <th className="px-2 py-1 font-medium">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800">
                    {data.latest.hard_cases.map((hc) => (
                      <tr key={hc.key}>
                        <td className="px-2 py-1 text-neutral-300">{hc.key}</td>
                        <td className="px-2 py-1">
                          <ResultPill correct={hc.correct} />
                        </td>
                        <td className="px-2 py-1 text-neutral-400">
                          {hc.actual_ticket_key ?? 'no match'}
                        </td>
                        <td className="px-2 py-1 text-neutral-400">
                          {hc.confidence !== null ? hc.confidence.toFixed(2) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div>
            <h2 className="mb-2 text-sm font-semibold text-neutral-300">
              All queries ({data.latest.results.length})
            </h2>
            <RunResultsTable results={data.latest.results} />
          </div>

          {data.history.length > 1 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold text-neutral-300">
                Run history ({data.history.length} runs)
              </h2>
              <HistoryTable history={data.history} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
