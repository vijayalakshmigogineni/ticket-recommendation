import { Link } from 'react-router-dom'
import type { TicketSummary } from '../../api/types'
import { formatDateTime } from '../../lib/format'

const statusColors: Record<string, string> = {
  OPEN: 'text-blue-300',
  IN_PROGRESS: 'text-amber-300',
  PENDING: 'text-purple-300',
  WAITING_FOR_CLIENT: 'text-orange-300',
  RESOLVED: 'text-emerald-300',
  CLOSED: 'text-neutral-500',
}

export function TicketTable({ tickets }: { tickets: TicketSummary[] }) {
  if (tickets.length === 0) {
    return <p className="text-xs text-neutral-500">No tickets match these filters.</p>
  }

  return (
    <div className="overflow-x-auto rounded border border-neutral-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-neutral-900 text-neutral-500">
          <tr>
            <th className="px-2 py-1 font-medium">Subject</th>
            <th className="px-2 py-1 font-medium">Customer</th>
            <th className="px-2 py-1 font-medium">Category</th>
            <th className="px-2 py-1 font-medium">Status</th>
            <th className="px-2 py-1 font-medium">Interactions</th>
            <th className="px-2 py-1 font-medium">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800">
          {tickets.map((t) => (
            <tr key={t.id} className="hover:bg-neutral-900/60">
              <td className="px-2 py-1">
                <Link to={`/dataset/tickets/${t.id}`} className="text-neutral-200 hover:underline">
                  {t.subject}
                </Link>
              </td>
              <td className="px-2 py-1 text-neutral-400">{t.customer_name}</td>
              <td className="px-2 py-1 text-neutral-400">{t.category}</td>
              <td className={`px-2 py-1 ${statusColors[t.status] ?? 'text-neutral-400'}`}>
                {t.status}
              </td>
              <td className="px-2 py-1 text-neutral-400">{t.interaction_count}</td>
              <td className="px-2 py-1 text-neutral-500">{formatDateTime(t.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
