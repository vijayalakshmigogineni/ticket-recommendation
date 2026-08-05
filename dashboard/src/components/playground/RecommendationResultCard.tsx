import { Link } from 'react-router-dom'
import type { RunTraceResponse } from '../../api/types'
import { DurationBadge } from '../shared/DurationBadge'
import { TicketBadge } from '../shared/TicketBadge'
import { FeedbackActions } from './FeedbackActions'

export function RecommendationResultCard({ result }: { result: RunTraceResponse }) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-neutral-500">Recommendation</span>
        <DurationBadge ms={result.total_time_ms} />
      </div>

      {result.path === 'unknown_customer' && (
        <p className="text-sm text-neutral-300">
          Sender email didn't match any known customer -- can't route this without a known
          customer.
        </p>
      )}

      {result.path === 'auto_attach' && result.thread_detection?.ticket && (
        <div>
          <p className="mb-2 text-sm text-neutral-300">
            Auto-attached via thread detection ({result.thread_detection.matched_on}) -- no AI
            involved.
          </p>
          <TicketBadge ticket={result.thread_detection.ticket} />
        </div>
      )}

      {result.path === 'ai_decision' && result.decision && (
        <div className="space-y-2">
          <p className="text-sm text-neutral-300">
            {result.decision.should_attach ? 'Attach to:' : 'No matching ticket found.'}
          </p>
          {result.decision.ticket && <TicketBadge ticket={result.decision.ticket} />}
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span>Confidence:</span>
            <span className="font-mono text-neutral-200">
              {(result.decision.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-neutral-400">{result.decision.explanation}</p>
        </div>
      )}

      {result.path === 'ai_decision' && result.decision && <FeedbackActions result={result} />}

      <Link to="/pipeline" className="mt-3 inline-block text-xs text-neutral-500 hover:underline">
        View full pipeline trace →
      </Link>
    </div>
  )
}
