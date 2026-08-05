import type { GroupingTrace } from '../../../api/types'
import { formatScore } from '../../../lib/format'
import { TicketBadge } from '../../shared/TicketBadge'

export function GroupingDetail({ trace }: { trace: GroupingTrace }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-neutral-500">
        Every retrieved interaction grouped by ticket, aggregated into a final score (0.5×max +
        0.3×top-k-avg + 0.2×recency, per current config).
      </p>
      {trace.candidates.map((c) => (
        <div key={c.ticket.id} className="rounded border border-neutral-800 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <TicketBadge ticket={c.ticket} />
            <div className="flex gap-3 text-xs text-neutral-400">
              <span>max {formatScore(c.max_score)}</span>
              <span>top-k avg {formatScore(c.topk_avg)}</span>
              <span>recency {formatScore(c.recency_score)}</span>
              <span className="font-semibold text-neutral-200">
                final {formatScore(c.final_score)}
              </span>
            </div>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="text-neutral-600">
              <tr>
                <th className="py-0.5 font-normal">Contributing Interaction</th>
                <th className="py-0.5 font-normal">Match Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {c.matched_interactions.map((m) => (
                <tr key={m.interaction_id}>
                  <td className="py-1 pr-3 text-neutral-400">{m.preview}</td>
                  <td className="py-1 text-neutral-300">{formatScore(m.match_score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
