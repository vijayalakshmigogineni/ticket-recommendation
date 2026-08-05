import { useState } from 'react'
import type { RunRequest } from '../../api/types'

interface EmailInputFormProps {
  onSubmit: (request: RunRequest) => void
  isSubmitting: boolean
  submitLabel?: string
}

export function EmailInputForm({
  onSubmit,
  isSubmitting,
  submitLabel = 'Run Recommendation',
}: EmailInputFormProps) {
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [senderEmail, setSenderEmail] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [messageId, setMessageId] = useState('')
  const [conversationId, setConversationId] = useState('')
  const [inReplyTo, setInReplyTo] = useState('')
  const [referenceIds, setReferenceIds] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      subject,
      body,
      sender_email: senderEmail,
      message_id: messageId || null,
      conversation_id: conversationId || null,
      in_reply_to: inReplyTo || null,
      reference_message_ids: referenceIds
        ? referenceIds.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-400">Sender Email</label>
        <input
          type="email"
          required
          value={senderEmail}
          onChange={(e) => setSenderEmail(e.target.value)}
          placeholder="billing@example-clinic.com"
          className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-xs text-neutral-200"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-400">Subject</label>
        <input
          type="text"
          required
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-xs text-neutral-200"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-400">Body</label>
        <textarea
          required
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={6}
          className="w-full rounded border border-neutral-800 bg-neutral-900 p-2 text-xs text-neutral-200"
        />
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="text-xs text-neutral-500 hover:underline"
      >
        {showAdvanced ? '− Hide' : '+ Show'} threading fields (message-id / conversation-id /
        in-reply-to / references)
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-2 gap-3 rounded border border-neutral-800 p-3">
          <div>
            <label className="mb-1 block text-xs text-neutral-500">Message-ID</label>
            <input
              value={messageId}
              onChange={(e) => setMessageId(e.target.value)}
              className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">Conversation-ID</label>
            <input
              value={conversationId}
              onChange={(e) => setConversationId(e.target.value)}
              className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">In-Reply-To</label>
            <input
              value={inReplyTo}
              onChange={(e) => setInReplyTo(e.target.value)}
              className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">References (comma-separated)</label>
            <input
              value={referenceIds}
              onChange={(e) => setReferenceIds(e.target.value)}
              className="w-full rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
            />
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-neutral-100 px-4 py-1.5 text-xs font-medium text-neutral-900 disabled:opacity-40"
      >
        {isSubmitting ? 'Running…' : submitLabel}
      </button>
    </form>
  )
}
