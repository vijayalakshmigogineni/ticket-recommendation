import { Link } from 'react-router-dom'
import type { TicketRef } from '../../api/types'

const statusColors: Record<string, string> = {
  OPEN: 'border-blue-800 text-blue-300',
  IN_PROGRESS: 'border-amber-800 text-amber-300',
  PENDING: 'border-purple-800 text-purple-300',
  WAITING_FOR_CLIENT: 'border-orange-800 text-orange-300',
  RESOLVED: 'border-emerald-800 text-emerald-300',
  CLOSED: 'border-neutral-700 text-neutral-400',
}

export function TicketBadge({ ticket }: { ticket: TicketRef | null }) {
  if (!ticket) return <span className="text-xs text-neutral-600">—</span>

  return (
    <Link
      to={`/dataset/tickets/${ticket.id}`}
      className={`inline-flex max-w-full items-center gap-1 rounded border px-1.5 py-0.5 text-xs hover:bg-neutral-800 ${
        statusColors[ticket.status] ?? 'border-neutral-700 text-neutral-300'
      }`}
      title={`${ticket.subject} (${ticket.status})`}
    >
      <span className="truncate">{ticket.subject}</span>
    </Link>
  )
}
