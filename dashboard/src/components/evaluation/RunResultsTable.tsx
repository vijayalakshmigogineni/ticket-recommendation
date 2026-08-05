import type { EvalQueryResult } from '../../api/types'
import { DurationBadge } from '../shared/DurationBadge'

export function ResultPill({ correct }: { correct: boolean }) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-xs ${
        correct
          ? 'border-emerald-800 bg-emerald-950 text-emerald-400'
          : 'border-red-800 bg-red-950 text-red-400'
      }`}
    >
      {correct ? 'PASS' : 'FAIL'}
    </span>
  )
}

export function RunResultsTable({ results }: { results: EvalQueryResult[] }) {
  return (
    <div className="overflow-x-auto rounded border border-neutral-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-neutral-900 text-neutral-500">
          <tr>
            <th className="px-2 py-1 font-medium">Key</th>
            <th className="px-2 py-1 font-medium">Category</th>
            <th className="px-2 py-1 font-medium">Difficulty</th>
            <th className="px-2 py-1 font-medium">Result</th>
            <th className="px-2 py-1 font-medium">Expected</th>
            <th className="px-2 py-1 font-medium">Actual</th>
            <th className="px-2 py-1 font-medium">Confidence</th>
            <th className="px-2 py-1 font-medium">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800">
          {results.map((r) => (
            <tr key={r.key} className="align-top">
              <td className="px-2 py-1 text-neutral-300">
                {r.explanation ? (
                  <details>
                    <summary className="cursor-pointer text-neutral-300 hover:underline">
                      {r.key}
                    </summary>
                    <p className="mt-1 max-w-md text-neutral-500">{r.explanation}</p>
                  </details>
                ) : (
                  r.key
                )}
              </td>
              <td className="px-2 py-1 text-neutral-400">{r.category}</td>
              <td className="px-2 py-1 text-neutral-400">{r.difficulty}</td>
              <td className="px-2 py-1">
                <ResultPill correct={r.correct} />
              </td>
              <td className="px-2 py-1 text-neutral-400">
                {r.expected_ticket_keys ? r.expected_ticket_keys.join(' / ') : 'no match'}
              </td>
              <td className="px-2 py-1 text-neutral-400">{r.actual_ticket_key ?? 'no match'}</td>
              <td className="px-2 py-1 text-neutral-400">
                {r.confidence !== null ? r.confidence.toFixed(2) : '—'}
              </td>
              <td className="px-2 py-1">
                <DurationBadge ms={r.elapsed_s * 1000} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
