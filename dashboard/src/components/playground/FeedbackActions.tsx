import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { recordFeedback } from '../../api/feedback'
import { queryKeys } from '../../api/queryKeys'
import { listTickets } from '../../api/tickets'
import type { RunTraceResponse } from '../../api/types'
import { ApiError } from '../../api/client'

const NONE_OF_THESE = '__none__'

export function FeedbackActions({ result }: { result: RunTraceResponse }) {
  const [mode, setMode] = useState<'idle' | 'rejecting'>('idle')
  const [correctedTicketId, setCorrectedTicketId] = useState(NONE_OF_THESE)
  const [notes, setNotes] = useState('')
  const queryClient = useQueryClient()

  const customer = result.customer
  const decision = result.decision

  const ticketsQuery = useQuery({
    queryKey: queryKeys.tickets({ customer_id: customer?.id }),
    queryFn: ({ signal }) => listTickets({ customer_id: customer!.id, limit: 100 }, signal),
    enabled: mode === 'rejecting' && !!customer,
  })

  const mutation = useMutation({
    mutationFn: recordFeedback,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
    },
  })

  if (!customer || !decision) return null

  if (mutation.isSuccess) {
    return (
      <div className="mt-3 rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-400">
        Recorded: <span className="text-neutral-200">{mutation.data.manager_decision}</span>
        {mutation.data.corrected_ticket && (
          <>
            {' '}
            -&gt; corrected to{' '}
            <span className="text-neutral-200">{mutation.data.corrected_ticket.subject}</span>
          </>
        )}
      </div>
    )
  }

  const baseFields = {
    customer_id: customer.id,
    sender_email: customer.inbox_email,
    subject: result.preprocessing?.original_subject ?? '',
    body: result.preprocessing?.original_body ?? '',
    should_attach: decision.should_attach,
    recommended_ticket_id: decision.ticket?.id ?? null,
    confidence: decision.confidence,
    explanation: decision.explanation,
  }

  const submitAccept = () => {
    mutation.mutate({ ...baseFields, manager_decision: 'accepted' })
  }

  const submitReject = () => {
    mutation.mutate({
      ...baseFields,
      manager_decision: 'rejected',
      corrected_ticket_id: correctedTicketId === NONE_OF_THESE ? null : correctedTicketId,
      notes: notes.trim() || null,
    })
  }

  return (
    <div className="mt-3 border-t border-neutral-800 pt-3">
      <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
        Manager Feedback
      </div>

      {mode === 'idle' && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={submitAccept}
            disabled={mutation.isPending}
            className="rounded bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-900 disabled:opacity-40"
          >
            {mutation.isPending ? 'Recording…' : 'Accept'}
          </button>
          <button
            type="button"
            onClick={() => setMode('rejecting')}
            disabled={mutation.isPending}
            className="rounded border border-neutral-700 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-800 disabled:opacity-40"
          >
            Reject
          </button>
        </div>
      )}

      {mode === 'rejecting' && (
        <div className="space-y-2">
          <div>
            <label className="mb-1 block text-[11px] text-neutral-500">
              Actually belongs to…
            </label>
            <select
              value={correctedTicketId}
              onChange={(e) => setCorrectedTicketId(e.target.value)}
              className="w-full max-w-xs rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
            >
              <option value={NONE_OF_THESE}>None of these / no match</option>
              {ticketsQuery.data?.items.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.subject}
                </option>
              ))}
            </select>
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional notes…"
            rows={2}
            className="w-full max-w-xs rounded border border-neutral-800 bg-neutral-900 p-2 text-xs text-neutral-200"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={submitReject}
              disabled={mutation.isPending}
              className="rounded bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-900 disabled:opacity-40"
            >
              {mutation.isPending ? 'Recording…' : 'Confirm Reject'}
            </button>
            <button
              type="button"
              onClick={() => setMode('idle')}
              disabled={mutation.isPending}
              className="rounded px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {mutation.isError && (
        <p className="mt-2 text-xs text-red-400">
          {mutation.error instanceof ApiError ? mutation.error.message : 'Failed to record feedback'}
        </p>
      )}
    </div>
  )
}
